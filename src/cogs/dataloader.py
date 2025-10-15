import os
import discord
from discord.ext import commands
from assets.utils.data_manager import DataManager
from assets.logger.logger import music_data_logger as logger

class DataLoader(commands.Cog):
    def __init__(self, bot: commands.Bot):
        # Bot Instance
        self.bot = bot

        # Initialize data manager
        self.bot.data_manager = None

        # Import Data Manager
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'../assets/data/music_data.json')
        data_manager = DataManager(bot, data_path)

        # Set bot.data_manager to data_manager
        self.bot.data_manager = data_manager
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Handle bot leaving a server. Remove guild from: data."""
        # Removes guild from music data, if it exists
        if self.bot.data_manager.pop(str(guild.id), None):
            logger.info(f'Music data for guild {guild.id} removed.')

            # Save the updated music data
            self.bot.data_manager.save_music_data()
        

async def setup(bot):
    # Add DataLoader to bot instance
    await bot.add_cog(DataLoader(bot))