import discord
from discord import app_commands
from discord.ext import commands
from assets.utils.reply_embed import error_embed, success_embed, warning_embed, info_embed

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        # Bot Instance
        self.bot = bot

        # Set music_data to Data Manager (loaded in dataloader cog)
        self.music_data = self.bot.data_manager
        self.save_music_data = self.music_data.save_music_data
        self.add_music_data = self.music_data.add_music_data
        self.get_guild_music_data = self.music_data.get_guild_music_data
    
    ######################################
    ########### DISCORD EVENTS ###########
    ######################################

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle member joining a server. Gives the stored role to new members when they join, if any."""
        # Get join role if any
        role_id = self.bot.data_manager.get_guild_music_data(member.guild.id).get('join_role', None)
        role = member.guild.get_role(role_id) if role_id else None

        # Assign role
        if role:
            try:
                await member.add_roles(role, reason="Auto role on join")
            except discord.Forbidden:
                pass
            except Exception:
                pass
    
    ######################################
    ######## AUXILIAR FUNCTIONS ##########
    ######################################

    async def role_autocomplete(self, interaction: discord.Interaction, current: str):
        """Auxiliar function to autocomplete roles in /join-role."""
        roles = [
            app_commands.Choice(name=role.name, value=str(role.id))
            for role in interaction.guild.roles
            if current.lower() in role.name.lower() and not role.managed and role != interaction.guild.default_role
        ]
        return roles[:25]

    ######################################
    ############ / COMMANDS ##############
    ######################################

    @app_commands.command(name="clear", description="Clears messages in a channel.", extras={'Category': 'Moderation'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 2.0)
    @app_commands.describe(number="Number of messages to clear.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(embed_links=True, manage_messages=True, read_message_history=True, view_channel=True)
    async def clear(self, interaction: discord.Interaction, number: app_commands.Range[int, 1, 100]):
        """Clears messages in a channel."""
        # Defer the interaction
        await interaction.response.defer(ephemeral=True)

        # Delte messages
        deleted = await interaction.channel.purge(limit=number)

        # Check if any message was deleted
        if not deleted:
            return await interaction.followup.send(embed=warning_embed(f'I couldn\'t find any messages to delete.'), ephemeral=True)
        
        # Send success message
        await interaction.followup.send(embed=success_embed(f'Successfully deleted `{len(deleted)}` messages.'), ephemeral=True)

    @app_commands.command(name="join-role", description="Automatically assign a role to new members.", extras={'Category': 'Moderation'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    @app_commands.describe(role="The role to assign when a new member joins.")
    @app_commands.checks.has_permissions(manage_guild=True, manage_roles=True)
    @app_commands.checks.bot_has_permissions(embed_links=True, manage_roles=True)
    @app_commands.autocomplete(role=role_autocomplete)
    async def join_role(self, interaction: discord.Interaction, role: str):
        """Assigns a role to new members when they join."""
        # Get guild and user
        guild = interaction.guild
        user = interaction.user

        # Get role
        role = guild.get_role(int(role))

        # Ensure the role exists in the guild
        if role not in guild.roles:
            return await interaction.response.send_message(embed=error_embed(f'The selected role `{role.name}` does not exist in this server'), ephemeral=True)

        # Ensure role is not managed by integrations
        if role.managed:
            return await interaction.response.send_message(embed=error_embed(f'The selected role `{role.name}` cannot be managed by integrations'), ephemeral=True)

        # Check if the user has a higher role than the selected role
        if user.top_role <= role:
            return await interaction.response.send_message(embed=error_embed(f'You can only select roles that are below your highest role'), ephemeral=True)

        # Check if the bot's highest role is above the selected role
        if guild.me.top_role <= role:
            return await interaction.response.send_message(embed=error_embed(f'I cannot assign this role because it\'s above my highest role'), ephemeral=True)

        # Save the role to music data
        self.add_music_data(
            guild_id=interaction.guild.id,
            keys='join_role',
            values=role.id
        )

        # Send success message	
        await interaction.response.send_message(embed=success_embed(f'Successfully set {role.mention} as join role.'))
    
    @app_commands.command(name="remove-join-role", description="Disables auto assign a role to new members.", extras={'Category': 'Moderation'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    @app_commands.checks.has_permissions(manage_guild=True, manage_roles=True)
    @app_commands.checks.bot_has_permissions(embed_links=True, manage_roles=True)
    async def remove_join_role(self, interaction: discord.Interaction):
        """Disables auto assign a role to new members."""
        # Remove join role from music data
        self.add_music_data(
            guild_id=interaction.guild.id,
            keys='join_role',
            values=None
        )

        # Send success message	
        await interaction.response.send_message(embed=success_embed(f'Successfully removed join role.'))


async def setup(bot):
    # Add Moderation to bot instance
    await bot.add_cog(Moderation(bot))