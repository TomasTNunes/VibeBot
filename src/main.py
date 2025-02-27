import os
import discord
from discord import ActivityType
from discord.ext import commands
from dotenv import load_dotenv
from assets.logs.logger import main_logger as logger, debug_logger

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


if __name__ == '__main__':
    """Run bot instance"""
    try:
        bot.run(os.getenv('TOKEN'), log_handler=None)
    finally:
        logger.info(f'BOT SHUTDOWN----------------')