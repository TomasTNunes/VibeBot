import discord
from discord import SelectOption, app_commands
from discord.ext import commands
from discord.ui import View, Select

class HelpGroupView(View):
    """A view with Selector for Command Groups, to be used with /help <command_group>."""
    def __init__(self, bot: commands.Bot, cog: commands.Cog, command_group: app_commands.Group):
        super().__init__()
        self.bot = bot
        self.cog = cog
        self.command_group = command_group
        self.commands_list = command_group.commands

        # Initialize buttons
        self.update_buttons()
    
    ######################################
    ############## UPDATES ###############
    ######################################

    def update_buttons(self):
        """
        Initialize button states for this view.
        
        Buttons:
        - Group Commands Selector (Dropdown)

        NOTE: This view os not persistent, hence after bot restarts, interations requested before will fail.
        """
        # Clear previous buttons
        self.clear_items()

        # Group Commands Selector (Dropdown)
        options = [
            SelectOption(label='/'+command.qualified_name, value=command.qualified_name, description=command.description) 
            for command in self.commands_list
        ]
        command_selector = Select(
            options=options,
            placeholder='Help with command:',
            row=0
        )
        command_selector.callback = self.command_selector_callback
        self.add_item(command_selector)
    
    ######################################
    ############# CALLBACKS ##############
    ######################################
    async def command_selector_callback(self, interaction: discord.Interaction):
        """"Handle select command dropdown callback. Show help embed for selected command."""
        # Set current page
        selected_command = interaction.data["values"][0]

        # Send help embed for selected command
        await self.cog.help.callback(self.cog, interaction, selected_command)

        # Update view to remove selecte option
        self.update_buttons()
        await interaction.followup.edit_message(interaction.message.id,view=self)