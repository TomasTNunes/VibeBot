import os
import discord
from discord import ActivityType, app_commands
from discord.ext import commands
from dotenv import load_dotenv
from assets.logger.logger import main_logger as logger, debug_logger
from assets.utils.reply_embed import error_embed, success_embed, warning_embed, info_embed
from assets.utils.invitebuttonview import InviteButtonView

# Indentify each bot start in log
logger.info(f'STARTING BOT----------------')

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)),'.env'))

# Define which intents/events bot as access (for give all, but in future change to only needed ones. Havilng all affects performance)
intents = discord.Intents().all()

# Create bot instance
bot = commands.Bot(command_prefix='$', intents=intents)

# Define cogs to load
cogs = ['music']

############################################################################################################
################################################# EVENTS ###################################################
############################################################################################################

@bot.event
async def on_ready():
    """
    Called when the client is done preparing the data received from Discord.
    Used to update bot status, load cogs and / commands.
    """
    # Update bot status
    await bot.change_presence(status=discord.Status.online, 
                            activity=discord.Activity(type=ActivityType.listening, name="/help | /setup"))
    logger.info(f'Logged in as {bot.user}')

    # Load cogs
    for cog in cogs:
        try:
            await bot.load_extension(f'cogs.{cog}')
            logger.info(f'Cog `{cog}` loaded successfully')
        except Exception as e:
            logger.error(f'Failed to load cog \'{cog}\': {e}')
    # Log loades cogs
    logger.info(f'Loaded cogs: {list(bot.cogs.keys())}')

    # Load / commands
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} commands')
    except Exception as e:
        logger.error(f'Failed to sync commands: {e}')

@bot.event
async def on_command_error(ctx, error):
    """
    The default command error handler provided by the bot. 
    This only fires if you do not specify any listeners for command error.
    """
    # Ignore CommandNotFound errors
    if isinstance(error, commands.CommandNotFound):
        pass
    else:
        # Re-raise other errors to be handled elsewhere
        raise error

############################################################################################################
############################################### / COMMANDS #################################################
############################################################################################################

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """
    Handles errors for app_commands in this Cog.

    NOTE: CommandInvokeError exceptions are raise during the command, and therefore sometimes after `await interaction.response.defer(ephemeral=True)``
    has been called. Hence, for these use `await interaction.followup.send()` instead of `await interaction.response.send_message()` when needed.
    """

    # Handle CheckFailure: An exception raised when check predicates in a command have failed.
    if isinstance(error, app_commands.CheckFailure):

        # Handle NoPrivateMessage: An exception raised when a command does not work in a direct message.
        if isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message(embed=error_embed("This command cannot be used in private messages."), ephemeral=True)
        
        # Handle MissingPermissions: An exception raised when the command invoker lacks permissions to run a command.
        elif isinstance(error, app_commands.MissingPermissions):
            msg_text = 'You need the following permissions to run this command:'
            for permission in error.missing_permissions:
                msg_text += f' `{permission}`,'
            msg_text = msg_text[:-1]+'.'
            await interaction.response.send_message(embed=error_embed(msg_text), ephemeral=True)
        
        # Handle BotMissingPermissions: An exception raised when the bot’s member lacks permissions to run a command.
        elif isinstance(error, app_commands.BotMissingPermissions):
            msg_text = 'I need the following permissions to run this command:'
            for permission in error.missing_permissions:
                msg_text += f' `{permission}`,'
            msg_text = msg_text[:-1]+'.'
            await interaction.response.send_message(embed=error_embed(msg_text), ephemeral=True)
        
        # Handle CommandOnCooldown: An exception raised when the command being invoked is on cooldown.
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(embed=error_embed(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds."), ephemeral=True)
        
        # Handle MissingRole: An exception raised when the command invoker lacks a role to run a command.
        elif isinstance(error, app_commands.MissingRole):
            msg_text = 'You need the following role to run this command:'
            await interaction.response.send_message(embed=error_embed(f'You need the following role to run this command: `{error.missing_role}`'), ephemeral=True)
        
        # Handle MissingAnyRole: An exception raised when the command invoker lacks any of the roles specified to run a command.
        elif isinstance(error, app_commands.MissingAnyRole):
            msg_text = 'You need at least one of the following roles to run this command:'
            for role in error.missing_roles:
                msg_text += f' `{role}`,'
            msg_text = msg_text[:-1]+'.'
            await interaction.response.send_message(embed=error_embed(msg_text), ephemeral=True)
        
        # For other CheckFailure exceptions, like for example for cutom checks
        else:
            await interaction.response.send_message(embed=error_embed(f'An unexpected error has occured: {error}'), ephemeral=True)
    
    # Handle CommandInvokeError: An exception raised when the command being invoked raised an exception.
    elif isinstance(error, app_commands.CommandInvokeError):
        if interaction.response.is_done():
            await interaction.followup.send(embed=error_embed(f'An unexpected error has occured: {error.original}'), ephemeral=True)
            return
        await interaction.response.send_message(embed=error_embed(f'An unexpected error has occured: {error.original}'), ephemeral=True)
    
    # Handle rest of app_commands.AppCommandError exceptions
    else:
        await interaction.response.send_message(embed=error_embed(f'An unexpected error has occured: {error}'), ephemeral=True)

@bot.tree.command(name="invite", description="Get the bot invite link.")
@app_commands.checks.cooldown(1, 5.0)
@app_commands.checks.bot_has_permissions(embed_links=True)
async def invite(interaction: discord.Interaction):
    """Get the bot invite link in a button."""
    await interaction.response.send_message("Click the button below to invite VibeBot to your server!", view=InviteButtonView())

if __name__ == '__main__':
    """Run bot instance"""
    try:
        bot.run(os.getenv('TOKEN'), log_handler=None)
    finally:
        logger.info(f'BOT SHUTDOWN----------------')