from discord.ext import commands
import json
from typing import Union, List, Any, Optional
from assets.logger.logger import music_data_logger as logger


class DataManager:
    """Class to manage data and data functions for the bot."""
    def __init__(self, bot: commands.Bot, data_path: str):
        # Bot Instance
        self.bot = bot

        # Path to `music_data.json`
        self.data_path = data_path
        
        # Initialize data 
        self.data = self.load_music_data()

        # Clean up music data
        self.cleanup_music_data()
    
    def __getattr__(self, name):
        """Redirect attribute access to self.data"""
        return getattr(self.data, name)

    def __getitem__(self, key):
        """Allow dictionary-style access to self.data"""
        return self.data[key]
    
    def load_music_data(self):
        """Load data from the `music_data.json` file if it exists, otherwise return and save an empty dictionary."""
        try:
            with open(self.data_path, 'r', encoding="utf-8") as file:
                data = json.load(file)
                logger.info(f'Music data loaded from `music_data.json`.')
                return data
        except FileNotFoundError:
            logger.warning(f'`music_data.json` not found, setting `self.data` to an empty dictionary.')
            return {}
        except Exception as e:
            logger.error(f'Failed to load music data: {e}')
            raise # Re-raise the exception to prevent the cog from loading
    
    def save_music_data(self):
        """Save music data to the `music_data.json` file."""
        # Save new self.data
        try:
            with open(self.data_path, 'w', encoding="utf-8") as file:
                json.dump(self.data, file, indent=4, ensure_ascii=False)
                logger.info(f'Music data saved to `music_data.json`.')
        except Exception as e:
            logger.error(f'Failed to save music data: {e}')

    def cleanup_music_data(self):
        """Remove music data for guilds where the bot is no longer in."""
        # Get a list of guild IDs where the bot is currently in
        guild_ids = [str(guild.id) for guild in self.bot.guilds]

        # Remove music data for guilds where the bot is no longer in
        for guild_id in list(self.data.keys()):
            if guild_id not in guild_ids:
                self.data.pop(guild_id, None)
                logger.info(f'Music data for guild {guild_id} removed.')
        logger.info(f'Music data cleaned for guilds where the bot is no longer in.')

        # Save the updated music data
        self.save_music_data()

    def add_music_data(self, guild_id: int, keys: Union[str, List[str]], values: Union[Any, List[Any]], root_keys: Union[str, List[str]] = None):
        """
        Adds key-value pairs to the data dictionary, and saves it in `music_data.json`.
        
        Args:
            guild_id - The guild ID to add the key-value pair to.
            keys - The key to add or a list of keys to add. Can either be string or a list of strings.
            values - The value to add or a list of values to add. If keys is a list, values must be a list of the same length.
            root_key - The root key to add the key-value pair to. Can be None, string or a list of strings.
                     - If None, the key-value pair is added to the root key = [str(guild_id)].
                     - If string, the key-value pair is added to the root key = [str(guild_id)][root_key].
                     - If list of strings, the key-value pair is added to the root key = [str(guild_id)][root_key[0]][root_key[1]]...
        """
        def get_nested_dict(root_keys: List[str]):
            """Helper function to get (or create) the nested dictionary for a list of root keys."""
            # Ensure guild exists in music data, otherwise create it
            current = self.data.setdefault(str(guild_id), {})
            # Iterate through root keys to get target dictionary, while creating keys as needed
            for key in root_keys:
                current = current.setdefault(key, {})
            return current
        
        # Get traget dictionary with root_keys, while creating keys as needed
        if root_keys is None:
            target_dict = self.data.setdefault(str(guild_id), {})
        elif isinstance(root_keys, str):
            target_dict = get_nested_dict([root_keys])
        elif isinstance(root_keys, list):
            target_dict = get_nested_dict(root_keys)
        
        # Add key-value pair
        if isinstance(keys, list):
            if not isinstance(values, list) or len(keys) != len(values):
                raise ValueError("If key is a list, value must also be a list of the same length.")
            target_dict.update(zip(keys, values))
        else:
            target_dict[keys] = values
        logger.info(f'Music data for guild {guild_id} added/updated.')
        
        # Save music data
        self.save_music_data() 

    def get_guild_music_data(self, guild_id: int):
        """
        Get data for the specified guild.
        Returns data for the specified guild in the format of a dictionary.
        If the guild does not exist, return empty dictionary {}.
        """
        return self.data.get(str(guild_id), {})   
    