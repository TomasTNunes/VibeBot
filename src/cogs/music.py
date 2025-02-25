import os
import discord
from discord import app_commands
from discord.ext import commands
import lavalink
from lavalink.errors import ClientError
import json
import asyncio
from assets.logs.logger import music_logger as logger

############################################################################################################
########################################## LavalinkVoiceClient #############################################
############################################################################################################

class LavalinkVoiceClient(discord.VoiceProtocol):
    """
    This is the preferred way to handle external voice sending
    This client will be created via a cls in the connect method of the channel
    see the following documentation:
    https://discordpy.readthedocs.io/en/latest/api.html#voiceprotocol
    """

    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        self.guild_id = channel.guild.id
        self._destroyed = False

        if not hasattr(self.client, 'music'):
            # Instantiate a client if one doesn't exist.
            # We store it in `self.client` so that it may persist across cog reloads,
            # however this is not mandatory.
            self.client.music = lavalink.Client(client.user.id)
            self.client.music.add_node(host='localhost', port=2333, password='testing',
                                          region='eu', name='music-node')

        # Create a shortcut to the Lavalink client here.
        self.lavalink = self.client.music

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        channel_id = data['channel_id']

        if not channel_id:
            await self._destroy()
            return

        self.channel = self.client.get_channel(int(channel_id))

        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_STATE_UPDATE',
            'd': data
        }

        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False) -> None:
        """
        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        # ensure there is a player_manager when creating a new voice_client
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        # no need to disconnect if we are not connected
        if not force and not player.is_connected:
            return

        # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that would set channel_id
        # to None doesn't get dispatched after the disconnect
        player.channel_id = None
        await self._destroy()

    async def _destroy(self):
        self.cleanup()

        if self._destroyed:
            # Idempotency handling, if `disconnect()` is called, the changed voice state
            # could cause this to run a second time.
            return

        self._destroyed = True

        try:
            await self.lavalink.player_manager.destroy(self.guild_id)
        except ClientError:
            pass

############################################################################################################
############################################ MusicCogClass #################################################
############################################################################################################

class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        """
        Initializes the MusicCog instance.

        This method sets up essential variables that do not require asynchronous 
        operations or the Lavalink client. It runs before `cog_load()`.
        """
        # Bot Instance
        self.bot = bot
        # To be set to the Lavalink client instance in `cog_load()` 
        self.lavalink = None
        # Path to `music_data.json`
        self.music_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'../assets/data/music_data.json')
        # Load music data from `music_data.json`
        self.music_data = self.load_music_data()
        # Cleanup music data for guilds where the bot is no longer in
        self.cleanup_music_data()

    ######################################
    ############# COG LOAD ###############
    ######################################
    
    async def cog_load(self):
        """
        Handles asynchronous initialization when the cog is loaded.

        This method is executed after `__init__` and allows for async operations. 
        If an error occurs at any point, the cog is gracefully unloaded using 
        `cog_unload()`, and the cog is removed.
        """
        try:
            # Check if the Lavalink client already exists on the bot instance
            if not hasattr(self.bot, 'lavalink'):
                try:
                    # Initialize the Lavalink client
                    self.bot.lavalink = lavalink.Client(self.bot.user.id)
                    logger.info('Lavalink client initialized.')

                    # Add node to Lavalink client
                    self.bot.lavalink.add_node(
                        host='localhost', port=2333, password='youshallnotpass',
                        region='eu', name='music-node'
                    )
                    logger.info('Lavalink client node added.')

                except Exception as e:
                    logger.error(f'Failed to setup Lavalink: {e}')
                    raise  # Prevent cog from loading if Lavalink setup fails

            # Assign the Lavalink client to self.lavalink for easy access
            self.lavalink: lavalink.Client = self.bot.lavalink

            # Add event hooks
            self.lavalink.add_event_hooks(self)
            
        except Exception as e:
            # Gracefully unload the cog if an exception occurs during setup
            await self.cog_unload()
            raise # Re-raise the exception to prevent the cog from loading
    
    ######################################
    ############ COG UNLOAD ##############
    ######################################
    
    async def cog_unload(self):
        """
        This function removes any registered event hooks, cancels all Lavalink-related tasks, 
        and closes the Lavalink client when the cog is unloaded.

        Once the cog is loaded again, event hooks will be re-registered, and a new Lavalink 
        client will be created. This ensures the Lavalink client and its events are properly 
        refreshed when the cog is reloaded.

        Additionally, all Lavalink-related tasks will be identified and canceled to prevent 
        potential issues with lingering tasks after unloading.

        NOTE: Use `self.bot.lavalink` instead of `self.lavalink` in this function, as `self.lavalink` 
        may not be defined when the cog is being unloaded--for example, if an exception occurs 
        early in `cog_load`.
        """
        if hasattr(self.bot, 'lavalink') and self.bot.lavalink:
            # Clear event hooks
            try:
                self.bot.lavalink._event_hooks.clear()
                logger.info('Lavalink event hooks removed.')
            except Exception as e:
                logger.error(f'Failed to remove Lavalink event hooks: {e}')

            # Cancel all Lavalink-related tasks
            try:
                pending_tasks = [t for t in asyncio.all_tasks() if not t.done()]
                for task in pending_tasks:
                    if "lavalink" in str(task):
                        task.cancel()
                logger.info(f'Cancelled all Lavalink-related tasks.')
            except Exception as e:
                logger.error(f'Failed to cancel Lavalink tasks: {e}')

            # Close Lavalink Client
            try:
                await self.bot.lavalink.close()
                logger.info('Lavalink client closed.')
            except Exception as e:
                logger.error(f'Failed to close Lavalink Client: {e}')
    
    ######################################
    ############ MUSIC DATA ##############
    ######################################

    def load_music_data(self):
        """Load music data from the `music_data.json` file if it exists, otherwise return and save an empty dictionary."""
        try:
            with open(self.music_data_path, 'r') as file:
                data = json.load(file)
                logger.info(f'Music data loaded from `music_data.json`.')
                return data
        except FileNotFoundError:
            logger.warning(f'`music_data.json` not found, setting `self.music_data` to an empty dictionary.')
            return {}
        except Exception as e:
            logger.error(f'Failed to load music data: {e}')
            raise # Re-raise the exception to prevent the cog from loading
    
    def save_music_data(self):
        """Save music data to the `music_data.json` file."""
        try:
            with open(self.music_data_path, 'w') as file:
                json.dump(self.music_data, file, indent=4)
        except Exception as e:
            logger.error(f'Failed to save music data: {e}')
    
    def cleanup_music_data(self):
        """Remove music data for guilds where the bot is no longer in."""
        # Get a list of guild IDs where the bot is currently in
        guild_ids = [guild.id for guild in self.bot.guilds]

        # Remove music data for guilds where the bot is no longer in
        for guild_id in list(self.music_data.keys()):
            if guild_id not in guild_ids:
                del self.music_data[guild_id]
        logger.info(f'Music data cleaned for guilds where the bot is no longer in.')
        
        # Save the updated music data
        self.save_music_data()


    def add_music_data(self, guild_id: int, music_text_channel_id: int, music_message_id: int, default_volume: int = 50):
        """Add music data for the specified guild. If the guild already exists, update the data."""
        pass
    
    def get_music_data(self, guild_id: int):
        """
        Get music data for the specified guild.
        Returns music data for the specified guild in the format of a dictionary:
        {
            'guild_id': 1234567890,
            'music_text_channel_id': 1234567890,
            'music_message_id': 1234567890,
            'default_volume': 50
        }
        If the guild does not exist, return None.
        """
        pass
    
    ######################################
    ########## LAVALINK EVENTS ###########
    ######################################
    
    ######################################
    ########### DISCORD EVENTS ###########
    ######################################
    
    ######################################
    ######### BOT JOIN & CHECK ###########
    ######################################

    async def check_and_join(self, author: discord.Member, guild: discord.Guild, should_connect: bool):
        """
        This function serves as a prerequisite check for all music-related commands. 
        It ensures that a player exists for the guild and attempts to connect the bot to the author's voice channel when possible. 
        If successful, it returns True. Otherwise, it returns False and informs the user of the issue.

        NOTE: In this function, the player is created before the bot connects to a voice channel. 
        While this might seem like an inefficient use of resources — since players will be initialized for guilds even if the bot 
        isn't connected — this approach guarantees that a player is always available when needed, minimizing potential bugs.
        Ideally, the player should only be created upon connecting to a voice channel. 
        However, this could lead to issues if a player is unexpectedly destroyed without a corresponding disconnection, which might 
        occur due to a bug, a Lavalink restart, or the automatic removal of inactive players. 
        By ensuring the player is always initialized before executing music commands, we reduce the risk of such problems.
        """
        # Dont allow private messages
        if guild is None:
            return False
        
        # Create player if not exists
        self.lavalink.player_manager.create(guild.id)

        # Get Bot voice client if exists, otherwise None
        voice_client = guild.voice_client

        # Check if author is in voice channel
        if not author.voice or not author.voice.channel:
            # Check if bot is in voice channel.
            if voice_client is not None:
                # If yes, inform to join the same channel
                print('You need to join my voice channel first.')
                return False
            # If not, inform to join a voice channel
            print('Join a voice channel first.')
            return False

        # Get author voice channel
        voice_channel = author.voice.channel

        # If bot is not in voice channel, and author is in voice channel
        if voice_client is None:
            # Stop for commands that require bot to already be in voice channel
            if not should_connect:
                print('I\'m not playing music.')
                return False
            
            # Get bot's permission in the author's voice channel
            permissions = voice_channel.permissions_for(guild.me)

            # Check if bot has permission to connect and speak in the author's voice channel
            if not permissions.connect or not permissions.speak:
                print('I need `CONNECT` and `SPEAK` permissions.')
                return False

            # Check if author's voice channel has user limit, is full and if bot has permission to move members (as it allows to enter full voice channel)
            if (voice_channel.user_limit > 0) and (len(voice_channel.members) >= voice_channel.user_limit) and not guild.me.guild_permissions.move_members:
                print('Your voice channel is full.')
                return False

            # Connect to author's voice channel
            await voice_channel.connect(cls=LavalinkVoiceClient)
        
        # If bot is in voice channel, but not in author's voice channel
        elif voice_client.channel.id != voice_channel.id:
            print('You need to join my voice channel first.')
            return False
        
        # If bot connected to author's voice channel
        return True

    ######################################
    ############# COMMANDS ###############
    ######################################

    ######################################
    ############ / COMMANDS ##############
    ######################################

    # @app_commands.command(name='setup', description='Create music text channel')
    # async def setup(self, interaction: discord.Interaction):
    #     """Setup music text channel, if it doesn't exists."""
    #     # Prevents the interaction from timing out
    #     await interaction.response.defer()

    #     # Check if music text channel already exists
    #     ######

    #     # Create music text channel
    #     music_channel = await interaction.guild.create_text_channel('vibebot-music')


    #     music_text_channel_id = get_music_data(interaction.guild)[0]
    #     if music_text_channel_id == 0:
    #         music_channel = await interaction.guild.create_text_channel('stream')
    #         music_msg_id = await create_embed(self, interaction.guild, music_channel.id, self.emojis_mine)
    #         save_music_data(self,interaction.guild.id, music_channel.id, music_msg_id)
    #         await interaction.followup.send('CRIADO')
    #     else:
    #         await interaction.followup.send('ESSA MERDA JA EXISTE')



async def setup(bot):
    await bot.add_cog(MusicCog(bot))