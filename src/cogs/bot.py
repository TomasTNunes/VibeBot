import discord
from discord import app_commands, Embed
from discord.ext import commands
import time
from assets.logger.logger import main_logger as logger, debug_logger
from assets.utils.reply_embed import error_embed, success_embed, warning_embed, info_embed
from assets.utils.invitebuttonview import InviteButtonView

class Bot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="invite", description="Get the bot invite link.")
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
    
    @app_commands.command(name="ping", description="Shows the bot's ping.")
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