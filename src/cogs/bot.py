import discord
from discord import app_commands, Embed
from discord.ext import commands
import time
from typing import Optional
from assets.logger.logger import main_logger as logger, debug_logger
from assets.utils.reply_embed import error_embed, success_embed, warning_embed, info_embed
from assets.utils.invitebuttonview import InviteButtonView

class Bot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ######################################
    ######## AUXILIAR FUNCTIONS ##########
    ######################################

    async def commands_groups_autocomplete(self, interaction: discord.Interaction, current: str):
        """Auxiliar function to autocomplete function for commands and groups names in inputs of / commands."""
        return [
            app_commands.Choice(name=com.qualified_name, value=com.qualified_name)
            for com in self.bot.tree.walk_commands() if current.lower() in com.qualified_name.lower()
        ]

    def get_command_embed(self, command: app_commands.Command, appcommand: app_commands.AppCommand):
        """Create an embed for a command. To be used in /help."""
        # Create embed
        embed = Embed(
            color=discord.Colour.from_rgb(137, 76, 193),
            title=f"🎯 Command: **</{command.qualified_name}:{appcommand.id}>**",
            description="",
        )

        # Add Command Description
        command_description = command.description or "No description available"
        embed.add_field(name="📜 **Description**", value=f"> {command_description}", inline=False)

        # Iterate through all parameters
        usage_list = []
        params_fields = []
        for param in command.parameters:
            # Build usage list for command string
            param_usage = f"`<{param.display_name}>`" if param.required else f"`[{param.display_name}]`"
            usage_list.append(param_usage)

            # Format parameter details
            param_name = f"🔹 **{param.display_name}**" if param.required else f"🔸 **[Optional] {param.display_name}**"
            param_description = param.description or "*No description available*"
            params_fields.append(f"• {param_name}\n᲼᲼↳ *{param_description}*")

        # Add Command Usage
        embed.add_field(
            name="📝 **Usage**", 
            value=f"> /{command.qualified_name} {' '.join(usage_list)}",
            inline=False
        )

        # Add Parameters (if any)
        if params_fields:
            embed.add_field(
                name="⚙️ **Parameters**",
                value="\n".join(params_fields),
                inline=False
            )

        # Add footer
        embed.set_footer(text="Use /help for more info")

        # Return embed
        return embed
    
    ######################################
    ############ / COMMANDS ##############
    ######################################

    @app_commands.command(name="help", description="See all available commands and how to use them", extras={'Category': 'Bot', 'Sub-Category': None})
    @app_commands.checks.cooldown(1, 5.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.autocomplete(command_name=commands_groups_autocomplete)
    @app_commands.describe(
        command_name="Command name",
    )
    @app_commands.rename(
    command_name="command"  
    )
    async def help(self, interaction: discord.Interaction, command_name: Optional[str] = None):
        """See all available commands and how to use them."""
        # Check if command was given
        if command_name:
            # split command name
            split_command_name = command_name.split()

            # Get command
            command = self.bot.tree.get_command(split_command_name[0])

            # Check if command exists
            if not command:
                return await interaction.response.send_message(embed=error_embed(f'The command `{command_name}` does not exist.'))
            
            # Get app command
            appcommand = self.bot.synced_commands[command.qualified_name]
            
            # Check if command is a group
            if isinstance(command, app_commands.Group) and len(split_command_name) == 1:
                # Create Help Group Embed
                embed = Embed(
                    color=discord.Colour.from_rgb(137, 76, 193),
                    title=f"🎯 Command Group: `/{command_name}`",
                    description="",
                )

                # Add Group Description
                group_description = command.description or "No description available"
                embed.add_field(name="📜 **Description**", value=f"> {group_description}", inline=False)

                # Iterate through all commands
                cmd_fields = []
                for cmd in command.commands:
                    cmd_mention = f"</{cmd.qualified_name}:{appcommand.id}>"
                    cmd_description = cmd.description or "*No description available*"
                    cmd_fields.append(f"📌 {cmd_mention} — {cmd_description}")

                # Add commands to field
                embed.add_field(
                    name="**Commands:**",
                    value="\n".join(cmd_fields),
                    inline=False
                )

                # Add footer
                embed.set_footer(text="Use /help for more info")

                # Send embed
                return await interaction.response.send_message(embed=embed)
            
            # If command is subcommand, check if it exists
            if len(split_command_name) > 1:
                # Get subcommand
                command = command.get_command(split_command_name[1])
                
                # Check if subcommand exists
                if not command:
                    return await interaction.response.send_message(embed=error_embed(f'The command `{command_name}` does not exist.'))

            # Create Command Embed
            embed = self.get_command_embed(command, appcommand)

            # Send embed
            return await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invite", description="Get the bot invite link", extras={'Category': 'Bot', 'Sub-Category': None})
    @app_commands.checks.cooldown(1, 5.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    async def invite(self, interaction: discord.Interaction):
        """Get the bot invite link in a button."""
        embed = discord.Embed(
            title="✨ Invite VibeBot to Your Server!",
            description="Click the button below to invite **VibeBot** and enjoy music on your server!",
            color=discord.Colour.from_rgb(137, 76, 193)
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Thank you for choosing VibeBot! 🎵")

        await interaction.response.send_message(embed=embed, view=InviteButtonView())
    
    @app_commands.command(name="ping", description="Shows the bot's ping", extras={'Category': 'Bot', 'Sub-Category': None})
    @app_commands.checks.cooldown(1, 5.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    async def ping(self, interaction: discord.Interaction):
        """
        Shows the bot's ping, specifically:
            - Bot latency
            - Discord API latency and Shard ID
            - Database response time (when implemented)
            - Redis response time (when implemented)
            - Bot Uptime
            """
        # Get bot latency in ms, WebSocket latency (communication between the bot and Discord's gateway)
        bot_latency = round(self.bot.latency * 1000)

        # Get bot Shard ID
        shard_id = interaction.guild.shard_id if interaction.guild else 0

        # Measure Discord API latency in ms (REST API latency)
        start_time = time.monotonic()
        await self.bot.http.get_user(self.bot.user.id) # (simulating an API call)
        api_latency = round((time.monotonic() - start_time) * 1000)

        # Create embed
        embed = Embed(
            color=discord.Colour.from_rgb(137, 76, 193),
            title="🏓 Pong!",
            description="Here are the VibeBot's latency stats."
        )

        # Format uptime
        uptime = time.monotonic() - self.bot.start_time
        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Bot Latency (WebSocket)
        bot_latency = round(self.bot.latency * 1000)

        # Get bot Shard ID
        shard_id = interaction.guild.shard_id if interaction.guild else 0

        # Measure Discord API latency (REST API)
        start_time = time.monotonic()
        await self.bot.http.get_user(self.bot.user.id)  # Simulating an API call
        api_latency = round((time.monotonic() - start_time) * 1000)

        # Add fields with latency and uptime info
        embed.add_field(
            name="⏳ **Uptime**",
            value=f"`{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s`",
            inline=False
        )

        embed.add_field(
            name="📡 **Bot Latency**",
            value=f"`{bot_latency}ms`",
            inline=True
        )

        embed.add_field(
            name="🔗 **API Latency**",
            value=f"`{api_latency}ms` (Shard `{shard_id}`)",
            inline=True
        )

        # Send embed
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    # Add Bot to bot instance
    await bot.add_cog(Bot(bot))