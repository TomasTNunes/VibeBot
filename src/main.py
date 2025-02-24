import os
import discord
from discord import ActivityType
from discord.ext import commands
from dotenv import load_dotenv
from logger import logger

# Indentify each bot start in log
logger.info(f'Starting bot...')

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

# Event for when bot is ready
@bot.event
async def on_ready():
    # Update bot status
    await bot.change_presence(status=discord.Status.online, 
                            activity=discord.Activity(type=ActivityType.listening, name="/help"))
    logger.info(f'Logged in as {bot.user}')
    # Load cogs
    for cog in cogs:
        try:
            await bot.load_extension(f'cogs.{cog}')
            logger.info(f'Cog "{cog}" loaded successfully')
        except Exception as e:
            logger.error(f'Failed to load cog "{cog}": {e}')
    # Load / commands
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} commands')
    except Exception as e:
        logger.error(f'Failed to sync commands: {e}')

# Run bot instance
if __name__ == '__main__':
    bot.run(os.getenv('TOKEN'))