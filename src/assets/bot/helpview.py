import discord
import os
from discord import SelectOption, app_commands
from discord.ext import commands
from discord.ui import View, Select, Button

class HelpView(View):
    """A view with Selector for Commands, to be used with /help."""
    def __init__(self, bot: commands.Bot, cog: commands.Cog):
        super().__init__()
        self.bot = bot
        self.cog = cog
        # Sort commands alphabetically
        self.commands_list = sorted([com for com in self.bot.tree.walk_commands()], key=lambda c: c.qualified_name)
        # Invite url
        self.inv_url = os.getenv('INVITE_LINK')

        # Initialize buttons
        self.update_buttons()

    ######################################
    ############## UPDATES ###############
    ######################################

    def update_buttons(self):
        """
        Initialize button states for this view.
        
        Buttons:
        - Commands Selector (Dropdown)
        - Invite button

        NOTE: This view os not persistent, hence after bot restarts, interations requested before will fail.
        """
        # Clear previous buttons
        self.clear_items()

        # Commands Selector (Dropdown)
        options = [
            SelectOption(label='/'+command.qualified_name, value=command.qualified_name, description=command.description) 
            for command in self.commands_list
        ]
        command_selector = Select(
            options=options[:25],
            placeholder='Help with command:',
            row=0
        )
        command_selector.callback = self.command_selector_callback
        self.add_item(command_selector)

        # Invite Button
        self.add_item(Button(
            label="Invite VibeBot to your server", 
            url=self.inv_url, 
            style=discord.ButtonStyle.link
            )
        )
    
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
        await interaction.followup.edit_message(interaction.message.id, view=self)
