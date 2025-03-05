import os
import discord
from discord import app_commands, Embed
from discord.ext import commands
import lavalink
from lavalink.server import LoadType
from lavalink.events import TrackStartEvent, QueueEndEvent, NodeConnectedEvent, TrackEndEvent
import json
import asyncio
import re
import unicodedata
from typing import Union, List, Any, Optional
from assets.logger.logger import music_logger as logger, music_data_logger, debug_logger
from assets.music.lavalinkvoiceclient import LavalinkVoiceClient
from assets.music.musicplayerview import MusicPlayerView
from assets.replies.reply_embed import error_embed, success_embed, warning_embed, info_embed

url_rx = re.compile(r'https?://(?:www\.)?.+')

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
                        host=os.getenv('LAVALINK_ADDRESS'), port=os.getenv('LAVALINK_PORT'), password=os.getenv('LAVALINK_PASSWORD'),
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

            # Cleanup messages from music text channels that are not the music message, and create missing music messages.
            # Set existing music messages to default and restore MusicPlayerViews for these.
            await self.cleanup_music_channels()
            
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
            with open(self.music_data_path, 'r', encoding="utf-8") as file:
                data = json.load(file)
                logger.info(f'Music data loaded from `music_data.json`.')
                music_data_logger.info(f'Music data loaded from `music_data.json`.')
                return data
        except FileNotFoundError:
            logger.warning(f'`music_data.json` not found, setting `self.music_data` to an empty dictionary.')
            music_data_logger.warning(f'`music_data.json` not found, setting `self.music_data` to an empty dictionary.')
            return {}
        except Exception as e:
            logger.error(f'Failed to load music data: {e}')
            music_data_logger.error(f'Failed to load music data: {e}')
            raise # Re-raise the exception to prevent the cog from loading
    
    def save_music_data(self):
        """Save music data to the `music_data.json` file."""
        # Save new self.music_data
        try:
            with open(self.music_data_path, 'w', encoding="utf-8") as file:
                json.dump(self.music_data, file, indent=4, ensure_ascii=False)
                music_data_logger.info(f'Music data saved to `music_data.json`.')
        except Exception as e:
            music_data_logger.error(f'Failed to save music data: {e}')
    
    def cleanup_music_data(self):
        """Remove music data for guilds where the bot is no longer in."""
        # Get a list of guild IDs where the bot is currently in
        guild_ids = [str(guild.id) for guild in self.bot.guilds]

        # Remove music data for guilds where the bot is no longer in
        for guild_id in list(self.music_data.keys()):
            if guild_id not in guild_ids:
                self.music_data.pop(guild_id, None)
                music_data_logger.info(f'Music data for guild {guild_id} removed.')
        logger.info(f'Music data cleaned for guilds where the bot is no longer in.')
        music_data_logger.info(f'Music data cleaned for guilds where the bot is no longer in.')
        
        # Save the updated music data
        self.save_music_data()
    
    def add_music_data(self, guild_id: int, keys: Union[str, List[str]], values: Union[Any, List[Any]], root_keys: Union[str, List[str]] = None):
        """
        Adds key-value pairs to the music_data dictionary, and saves it in `music_data.json`.
        
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
            current = self.music_data.setdefault(str(guild_id), {})
            # Iterate through root keys to get target dictionary, while creating keys as needed
            for key in root_keys:
                current = current.setdefault(key, {})
            return current
        
        # Get traget dictionary with root_keys, while creating keys as needed
        if root_keys is None:
            target_dict = self.music_data.setdefault(str(guild_id), {})
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
        music_data_logger.info(f'Music data for guild {guild_id} added/updated.')
        
        # Save music data
        self.save_music_data()
    
    def get_guild_music_data(self, guild_id: int):
        """
        Get music data for the specified guild.
        Returns music data for the specified guild in the format of a dictionary.
        If the guild does not exist, return empty dictionary {}.
        """
        return self.music_data.get(str(guild_id), {})

    ######################################
    ######## MUSIC TEXT CHANNEL ##########
    ######################################
    
    async def create_music_message(self, music_text_channel: discord.TextChannel):
        """Create a music message in the specified music text channel. Returns music message."""
        # Get default music message text and embed
        message_text, embed = self.get_default_music_message()

        # Get MusicPlayerView for this guild if it exists, otherwise create a new one
        musicplayerview = self.get_musicplayerview(music_text_channel.guild.id)
        if not musicplayerview:
            musicplayerview = MusicPlayerView(self.bot, self, music_text_channel.guild)

        # Send the music message (this adds view to bots persistent views automatically)
        music_message = await music_text_channel.send(message_text, embed=embed, view=musicplayerview)

        # Add guild music data to music data and save in `music_data.json`
        self.add_music_data(
            guild_id=music_text_channel.guild.id,
            keys=['guild_id', 'music_text_channel_id', 'music_message_id'],
            values=[music_text_channel.guild.id, music_text_channel.id, music_message.id],
        )

        return music_message
    
    @staticmethod
    def get_default_music_message():
        """Create and Returns the default music embed and message text."""
        # Create the default music embed
        embed = Embed(color = discord.Colour.from_rgb(137, 76, 193), title='No song playing currently')
        embed.set_image(url='https://i.pinimg.com/originals/44/eb/c3/44ebc3095a5deba2973f0e5fd3fb92b5.gif')
        embed.set_footer(text=f'For help type: /help')

        # Set the default music message
        message_text = 'Join a voice channel and queue songs by name or url in here.\n'

        return message_text, embed
    
    async def update_music_embed(self, guild: discord.Guild):
        """Update the music message embed in the music text channel."""
        # get guild music data
        guild_music_data = self.get_guild_music_data(guild.id)

        # get music text channel from ID
        music_text_channel = guild.get_channel(guild_music_data.get('music_text_channel_id')) if guild_music_data else None
        if not music_text_channel:
            return

        # get music message from ID
        try:
            music_message = await music_text_channel.fetch_message(guild_music_data.get('music_message_id')) if music_text_channel else None
            if not music_message:
                return
        except Exception as e:
            return

        # get player for this guild
        player = self.lavalink.player_manager.get(guild.id)

        # check if player exists and is playing to update track, otherwise sets default music message
        if player and player.is_playing:
            # Generate queue list string, and gets queue time
            queue_size = len(player.queue)
            queue_time = 0
            queue_list = '__**Queue list:**__\n'
            if queue_size > 15:
                queue_shown = player.queue[:15]
                queue_list += f'\nAnd **{queue_size-15}** more...'
            else:
                queue_shown = player.queue
            queue_shown_size = len(queue_shown)

            for i,item in enumerate(queue_shown[::-1]):
                if item.is_stream:
                    track_duration_str = 'LIVE'
                else:
                    queue_time += item.duration
                    track_duration_str = (
                        f'{str(item.duration // 3600000).zfill(2)}:{(item.duration % 3600000) // 60000:02d}:{(item.duration % 60000) // 1000:02d}'
                        if item.duration >= 3600000 else
                        f'{str(item.duration // 60000).zfill(2)}:{item.duration % 60000 // 1000:02d}'
                    )
                queue_list += (
                    f'\n**{queue_shown_size - i}.** '
                    f'{item.author} - {item.title}'
                    f' - `{track_duration_str}`' 
                    if item.is_seekable else
                    f'\n**{queue_shown_size - i}.** '
                    f'{item.uri}'
                    f' - `{track_duration_str}`'
                )
            
            # Get current track information
            current_track = player.current
            if current_track.is_stream:
                current_track_duration_str = 'LIVE'
            else:
                current_track_duration_str = (
                        f'{str(current_track.duration // 3600000).zfill(2)}:{(current_track.duration % 3600000) // 60000:02d}:{(current_track.duration % 60000) // 1000:02d}'
                        if current_track.duration >= 3600000 else
                        f'{str(current_track.duration // 60000).zfill(2)}:{current_track.duration % 60000 // 1000:02d}'
                    )
                queue_time += current_track.duration

            # Create music message Embed
            embed = Embed(color= discord.Colour.from_rgb(137, 76, 193),
                          description=(
                              f'**[{current_track.author} - {current_track.title}]({current_track.uri})**'
                              f' - `{current_track_duration_str}`\n'
                              f'Requester: {current_track.requester.mention}\n'
                              f'Channel: {guild.voice_client.channel.mention}'
                              if current_track.is_seekable else
                              f'**{current_track.uri}**'
                              f' - `{current_track_duration_str}`\n'
                              f'Requester: {current_track.requester.mention}\n'
                              f'Channel: {guild.voice_client.channel.mention}'
                              )
            )
            embed.set_author(name='Now Playing')
            embed.set_thumbnail(url=current_track.artwork_url if current_track.artwork_url else self.bot.user.avatar.url)
            queue_time_str = (
                    f'{str(queue_time // 3600000).zfill(2)}:{(queue_time % 3600000) // 60000:02d}:{(queue_time % 60000) // 1000:02d}'
                    if queue_time >= 3600000 else
                    f'{str(queue_time // 60000).zfill(2)}:{queue_time % 60000 // 1000:02d}'
                )
            embed.set_footer(text=(
                f'{queue_size} songs in queue for '
                f'{queue_time_str} of listening | Volume: {player.volume}%'
                )
            )

        else:
            queue_list, embed = self.get_default_music_message()
        
        # Edit music message
        await music_message.edit(content=queue_list, embed=embed, allowed_mentions=discord.AllowedMentions(users=False))

    async def cleanup_music_channels(self):
        """
        Remove messages from music text channels that are not the music message and create missing music messages.
        Set music message to default.
        Restore MusicPlayerView.
        """
        # Iterate through all guilds in `music_data.json`
        for guild_music_data in self.music_data.values():
            # Get guild from guild ID
            guild = self.bot.get_guild(guild_music_data.get('guild_id'))

            # Get music text channel from ID
            music_text_channel = guild.get_channel(guild_music_data.get('music_text_channel_id')) if guild else None

            # If music text channel does not exist skip iteration
            # Don't remove from music data because music data contains other information that should not be deleted
            # in case music channel is created again (deafult volume, playlists, etc.)
            if not music_text_channel:
                continue

            # get music message from ID
            try:
                music_message = await music_text_channel.fetch_message(guild_music_data.get('music_message_id')) if music_text_channel else None
            except Exception as e:
                music_message = None
            
            # delete all messages in music text channel that are not the music message
            music_message_id = guild_music_data.get('music_message_id')
            await music_text_channel.purge(check=lambda m: m.id != music_message_id, bulk=True)

            # If music message does not exist, create it. Otherwise, set it to default
            if not music_message:
                await self.create_music_message(music_text_channel)
            else:
                # Get default music message
                music_channel_text, embed = self.get_default_music_message()

                # Set music message to default and restore MusicPlayerView
                await music_message.edit(content=music_channel_text, embed=embed, view=MusicPlayerView(self.bot, self, guild))

        logger.info('Music text channels cleaned up, music messages set to default and MusicPlayerViews.')
    
    ######################################
    ######### MUSIC PLAYER VIEW ##########
    ######################################
    
    def get_musicplayerview(self, guild_id: int):
        """Get MusicPlayerView for the specified guild. Returns None if not found."""
        for view in self.bot.persistent_views:
            if isinstance(view, MusicPlayerView) and view.guild.id == guild_id:
                return view
        return None
    
    async def update_musicplayerview(self, guild_id: int):
        """
        Update MusicPlayerView for the specified guild music message.

        Useful to update MusicPLayerView buttons outside of Player interactions.
        In player interactions, use `interaction.message.edit(view=self)`.
        """
        # Get music data for this guild in case it exists, otherwise return
        guild_music_data = self.get_guild_music_data(guild_id)
        if not guild_music_data:
            return

        # Get music text channel from ID if it exists, otherwise return
        music_text_channel = self.bot.get_channel(guild_music_data.get('music_text_channel_id'))
        if not music_text_channel:
            return

        # get music message from ID if it exists, otherwise return
        try:
            music_message = await music_text_channel.fetch_message(guild_music_data.get('music_message_id'))
            if not music_message:
                return
        except Exception as e:
            return

        # Get MusicPlayerView and update it for this guild if it exists, otherwise create a new one
        musicplayerview = self.get_musicplayerview(guild_id)
        if not musicplayerview:
            musicplayerview = MusicPlayerView(self.bot, self, music_text_channel.guild)
        else:
            musicplayerview.update_buttons()

        # Edit music message with updated view
        await music_message.edit(view=musicplayerview)

                
    ######################################
    ########## LAVALINK EVENTS ###########
    ######################################

    @lavalink.listener(NodeConnectedEvent)
    async def on_node_connect(self, event: NodeConnectedEvent):
        """This is a custom event, emitted when a connection to a Lavalink node is successfully established."""
        logger.info(f'Lavalink client node `{event.node.name}` connected.')
    
    @lavalink.listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent):
        """
        This event is emitted when a track begins playing (e.g. via player.play()).

        Used to:
            - Stopping the auto-disconnect idle timer
            - Update music message embed
            - Update MusicPlayerView
        """
        # Get voice client for this guild
        guild_id = event.player.guild_id
        voice_client = discord.utils.get(self.bot.voice_clients, guild__id=guild_id)

        # if voice client exists and is of type LavalinkVoiceClient, cancel idle timer task
        if voice_client and isinstance(voice_client, LavalinkVoiceClient):
            voice_client.stop_idle_timer()
        
        # Update music message embed
        await self.update_music_embed(voice_client.guild)
        
        # Update MusicPlayerView in music message
        await self.update_musicplayerview(guild_id)

    @lavalink.listener(QueueEndEvent)
    async def on_queue_end(self, event: QueueEndEvent):
        """
        This is a custom event, emitted by the DefaultPlayer when there are no more tracks in the queue.
        
        Used to:
            - Start the auto-disconnect idle timer
            - If autoplay is on adds recomended track to queue
            - Update music message embed
            - Update MusicPlayerView
            - Deletes previous track from guilds player
        """
        # Get voice client for this guild
        guild_id = event.player.guild_id
        voice_client = discord.utils.get(self.bot.voice_clients, guild__id=guild_id)

        # if voice client exists and is of type LavalinkVoiceClient, start idle timer task
        if voice_client and isinstance(voice_client, LavalinkVoiceClient):
            await voice_client.start_idle_timer()    
        
        # if autoplay is on, add recommended track
        # Create query based only on previous track. Only if this track from spotify
        # No need to update embed as add_to_queue will update it, unless add_to_queue fails.
        if event.player.fetch(key='autoplay', default=False):
            track = event.player.fetch(key='previous_track', default=None)
            if track and track.source_name == 'spotify':
                query = f'seed_artists={track.plugin_info['artistUrl'].split('/')[-1]}&seed_tracks={track.identifier}&limit=1'
                add_to_queue_check = await self.add_to_queue(query, self.bot.user, voice_client.guild, search_autoplay=True)
                # check if successful
                if not add_to_queue_check:
                    return   
            else:
                # inform user that last track must be from spotify for now
                guild_music_data = self.get_guild_music_data(guild_id)
                music_text_channel = self.bot.get_channel(guild_music_data.get('music_text_channel_id')) if guild_music_data else None
                if music_text_channel:
                    await music_text_channel.send(embed=warning_embed('`AutoPlay` only works if last music track is from spotify.'), delete_after=15)  
            
        # Update music message embed
        await self.update_music_embed(voice_client.guild)

        # Update MusicPlayerView in music message
        await self.update_musicplayerview(guild_id)

        # Delete previous track from guilds player, if it exists and aytoplay is not on
        try:
            event.player.delete(key='previous_track') # raises KeyError – If the key doesn’t exist.
        except Exception:
            pass
    
    @lavalink.listener(TrackEndEvent)
    async def on_track_end(self, event: TrackEndEvent):
        """
        This event is emitted when the player finished playing a track.

        Used to:
            - Save in guilds player the previous track
        """
        # Get player for this guild
        player = self.lavalink.player_manager.get(event.player.guild_id)

        # Store previous track
        if player:
            player.store(key='previous_track', value=event.track)
        
    
    ######################################
    ########### DISCORD EVENTS ###########
    ######################################

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Called when a Message is created and sent. Used to manage messages in music text channels."""
        # No private messages
        if not message.guild:
            return
        
        # Get music data for this guild in case it exists, otherwise None
        guild_music_data = self.get_guild_music_data(message.guild.id)
        music_text_channel_id = guild_music_data.get('music_text_channel_id') if guild_music_data else None

        # Check is message is from a music text channel, and not from VibeBot
        if music_text_channel_id == message.channel.id and message.author != self.bot.user:
            # If message is not from a bot send the message to play function
            if not message.author.bot:
                # Check if bot should join and create player
                check = await self.check_and_join(message.author, message.guild, should_connect=True, should_bePlaying=False)
                if check:
                    await message.channel.send(embed=error_embed(check), delete_after=15)

                else:
                    # Add query to queue and send message if not successful
                    add_to_queue_check = await self.add_to_queue(message.content, message.author, message.guild)
                    if add_to_queue_check:
                        await message.channel.send(embed=error_embed(add_to_queue_check), delete_after=15)
            
            # Delete all the messages in the music text channel that are not from VibeBot
            try:
                await message.delete()
            except discord.Forbidden:
                await message.channel.send(embed=error_embed("I need `manage_messages`, `read_message_history` and `view_channel` permissions in this text channel."),
                                        delete_after=15)
            except discord.NotFound:
                pass
            except Exception as e:
                pass      

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Handle bot leaving a server. Remove guild from: persistent MusicPlayerViews and music data."""
        # Removes guild from persistent MusicPlayerViews
        musicplayerview = self.get_musicplayerview(guild.id)
        if musicplayerview:
            musicplayerview.stop()

        # Removes guild from music data, if it exists
        if self.music_data.pop(str(guild.id), None):
            music_data_logger.info(f'Music data for guild {guild.id} removed.')

            # Save the updated music data
            self.save_music_data()
    
    ######################################
    ######### BOT JOIN & CHECK ###########
    ######################################

    async def check_and_join(self, author: discord.Member, guild: discord.Guild, should_connect: bool, should_bePlaying: None):
        """
        This function serves as a prerequisite check for all music-related commands. 
        It ensures that a player exists for the guild and attempts to connect the bot to the author's voice channel when possible. 
        If successful returns False. Otherwise, it returns a string with the warning/error.

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
            return 'This command can only be used in a server.'
        
        # Check if there is any lavalink nodes available
        if not self.lavalink.node_manager.available_nodes:
            return 'No lavalink nodes available.'
        
        # Create player if not exists
        player = self.lavalink.player_manager.create(guild.id)

        # Get Bot voice client if exists, otherwise None
        voice_client = guild.voice_client

        # Check if author is in voice channel
        if not author.voice or not author.voice.channel:
            # Check if bot is in voice channel.
            if voice_client is not None:
                # If yes, inform to join the same channel
                return 'You need to join my voice channel first.'
            
            # If not, inform to join a voice channel
            return 'Join a voice channel first.'

        # Get author voice channel
        voice_channel = author.voice.channel

        # If bot is not in voice channel, and author is in voice channel
        if voice_client is None:
            # Stop for commands that require bot to already be in voice channel
            if not should_connect:
                return 'I\'m not playing music.'
            
            # Get bot's permission in the author's voice channel
            permissions = voice_channel.permissions_for(guild.me)

            # Check if bot has permission to connect and speak in the author's voice channel
            if not permissions.connect or not permissions.speak or not permissions.view_channel:
                return 'I need `connect`, `speak` and `view_channel` permissions.'

            # Check if author's voice channel has user limit, is full and if bot has permission to move members (as it allows to enter full voice channel)
            if (voice_channel.user_limit > 0) and (len(voice_channel.members) >= voice_channel.user_limit) and not guild.me.guild_permissions.move_members:
                return 'Your voice channel is full.'

            # Connect to author's voice channel
            await voice_channel.connect(cls=LavalinkVoiceClient)
        
        # If bot is in voice channel, but not in author's voice channel
        elif voice_client.channel.id != voice_channel.id:
            return 'You need to join my voice channel first.'
        
        # Stop for commands that require bot to be playing when it's not
        if not player.is_playing and should_bePlaying:
            return 'I\'m not playing music.'

        # If bot connected to author's voice channel or already is in author's voice channel
        return False
    
    ######################################
    ############## ACTIONS ###############
    ######################################

    async def add_to_queue(self, query: str, author: discord.Member, guild: discord.Guild, search_autoplay: bool = False):
        """
        Add query to lavalink queue.

        It will search the user query in lavalink and add it to the queue.
        The query can eith be url or name. If it is url, it can be a playlist.
        Default search engine is Spotify.

        If successful returns False. Otherwise, it returns a string with the warning/error.

        NOTE: This function assumes that `check_and_join()` has already been called before this function is called. 
        """
        # Get player for this guild
        player = self.lavalink.player_manager.get(guild.id)

        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip('<>')

        # Check if query is url. If not, the deafault search engine is used.
        if not url_rx.match(query):
            # Check if autoplay recommendation should be used
            if search_autoplay:
                query = f'sprec:{query}'
            else:
                query = f'spsearch:{query}'
        
        # Get the results for the query from Lavalink.
        results = await player.node.get_tracks(query)

        # Check each valid load_types:
        #   TRACK    - direct URL to a track
        #   PLAYLIST - direct URL to playlist
        #   SEARCH   - query prefixed with either "ytsearch:" or "scsearch:". This could possibly be expanded with plugins.
        #   EMPTY    - no results for the query (result.tracks will be empty)
        #   ERROR    - the track encountered an exception during loading
        if results.load_type == LoadType.EMPTY:
            return 'No results found.'
        
        elif results.load_type == LoadType.ERROR:
            return 'I encountered an error while searching for that query.'
        
        elif results.load_type == LoadType.PLAYLIST:
            # Get List of tracks in the playlist
            tracks = results.tracks

            # Add each track from playlists to the queue
            for track in tracks:
                # Save author mention for music message embed
                track.extra['requester'] = author
                player.add(track=track)

        else: # (TRACK or SEARCH)
            # Get first track from results
            track = results.tracks[0]

            # Save author mention for music message embed
            track.extra['requester'] = author

            # Add track to queue
            player.add(track=track)

        # If player is not playing, start playing. Otherwise, refresh embed.
        if not player.is_playing:
            await player.play()
        else:
            # Update music embed
            await self.update_music_embed(guild)

        return False

    ######################################
    ############# COMMANDS ###############
    ######################################

    ######################################
    ############ / COMMANDS ##############
    ######################################

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """
        Handles errors for app_commands in this Cog.

        NOTE: CommandInvokeError exceptions are raise during the command, and therefore after `await interaction.response.defer(ephemeral=True)``
        has been called. Hence, for these use `await interaction.followup.send()` instead of `await interaction.response.send_message()`.
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
            await interaction.followup.send(embed=error_embed(f'An unexpected error has occured: {error.original}'), ephemeral=True)
        
        # Handle rest of app_commands.AppCommandError exceptions
        else:
            await interaction.response.send_message(embed=error_embed(f'An unexpected error has occured: {error}'), ephemeral=True)

    @app_commands.command(name='setup', description='Create music text channel')
    @app_commands.guild_only()  # Only allow command in guilds, not in private messages
    @app_commands.checks.cooldown(1, 10.0)  # Command can be used once every 10 seconds
    @app_commands.checks.has_permissions(manage_channels=True, manage_guild=True)  # Member must have the permissions
    @app_commands.checks.bot_has_permissions(
        manage_channels=True,
        manage_roles=True,
        manage_messages=True,
        mention_everyone=True,
        view_channel=True,
        read_message_history=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        add_reactions=True,
        use_external_emojis=True,
    )  # Bot must have all these permissions
    async def setup(self, interaction: discord.Interaction):
        """Setup music text channel, if it doesn't exists."""
        # Get guild music data and music text channel id
        guild_music_data = self.get_guild_music_data(interaction.guild.id)
        music_text_channel_id = guild_music_data.get('music_text_channel_id') if guild_music_data else None

        # Get music text channel in case it exists in current guild, otherwise None
        music_text_channel = interaction.guild.get_channel(music_text_channel_id)

        # If music text channel exists, inform user
        if music_text_channel is not None:
            await interaction.response.send_message(embed=warning_embed(f'Music text channel already exists: {music_text_channel.mention}'), ephemeral=True)
            return

        # Create music text channel with required permissions for bot role
        overwrites = {
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                read_message_history=True, 
                send_messages=True,
                manage_messages=True,
                embed_links=True,
                attach_files=True,
                add_reactions=True,
                use_external_emojis=True,
                mention_everyone=True,
            )
        }
        topic_music_text_channel = ""
        music_text_channel = await interaction.guild.create_text_channel(name="vibebot-music", overwrites=overwrites, topic=topic_music_text_channel)

        # Create music message in music text channel
        await self.create_music_message(music_text_channel)

        # Infom user music text channel was created
        await interaction.response.send_message(embed=success_embed(f'Music text channel created: {music_text_channel.mention}')) 
    
    @app_commands.command(name='volume', description='Change bot\'s audio volume')
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 2.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.describe(
        volume="Set the player volume (0-200)"
    )
    async def volume(self, interaction: discord.Interaction, volume: app_commands.Range[int, 0, 200]):
        """Change bot's audio volume."""
        # Prevents the interaction from timing out
        await interaction.response.defer(ephemeral=True)

        # Check if command should continue using check_and_join()
        check = await self.check_and_join(interaction.user, interaction.guild, should_connect=False, should_bePlaying=False)
        if check:
            await interaction.followup.send(embed=error_embed(check), ephemeral=True)
            return

        # Get player for this guild
        player = self.lavalink.player_manager.get(interaction.guild.id)

        # Set player volume
        await player.set_volume(volume)

        # Update music message embed
        if player.is_playing:
            await self.update_music_embed(interaction.guild)

        # Send success message
        await interaction.followup.send(embed=success_embed(f'Volume set to `{volume}%`'), ephemeral=True)
    
    @app_commands.command(name='default-volume', description='Set the defauft volume when the bot joins a voice channel')
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.describe(
        volume="Set the default player volume (0-200)"
    )
    async def set_default_volume(self, interaction: discord.Interaction, volume: app_commands.Range[int, 10, 200]):
        """Change bot's default audio volume when the bot joins a voice channel."""
        # Get guild music data and set default volume
        self.add_music_data(
            guild_id=interaction.guild.id,
            keys='default_volume',
            values=volume
        )

        # Send success message
        await interaction.response.send_message(embed=success_embed(f'Default volume set to `{volume}%`'))
    
    @app_commands.command(name='default-autoplay', description='Enable or Disable autoplay by default when the bot joins a voice channel')
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.choices(state=[
    app_commands.Choice(name="Enable", value=1),
    app_commands.Choice(name="Disable", value=0)
    ])
    async def set_default_autoplay(self, interaction: discord.Interaction, state: app_commands.Choice[int]):
        """Enable or Disable autoplay by default when the bot joins a voice channel."""
        # Get guild music data and set default volume
        self.add_music_data(
            guild_id=interaction.guild.id,
            keys='default_autoplay',
            values=bool(state.value)
        )

        # Send success message
        if state.value:
            await interaction.response.send_message(embed=success_embed(f'Default AutoPlay `enabled`'))
        else:
            await interaction.response.send_message(embed=success_embed(f'Default AutoPlay `disabled`'))
    
    @app_commands.command(name='default-loop', description='Enable or Disable loop queue by default when the bot joins a voice channel')
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.choices(state=[
    app_commands.Choice(name="Enable", value=1),
    app_commands.Choice(name="Disable", value=0)
    ])
    async def set_default_loop(self, interaction: discord.Interaction, state: app_commands.Choice[int]):
        """Enable or Disable loop queue by default when the bot joins a voice channel."""
        # Get guild music data and set default volume
        self.add_music_data(
            guild_id=interaction.guild.id,
            keys='default_loop',
            values=bool(state.value)
        )

        # Send success message
        if state.value:
            await interaction.response.send_message(embed=success_embed(f'Default Loop Queue `enabled`'))
        else:
            await interaction.response.send_message(embed=success_embed(f'Default Loop Queue `disabled`'))
    
    @app_commands.command(name='pl-add', description='Add playlist button to music message')
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 5.0)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.describe(
        name="Playlist name (1-50 characters)",
        url="Playlist url (Spotify, Youtube, Soundcloud, AppleMusic, etc.)",
        button_name="Playlist button name (1-8 characters)",
        emoji="Playlist button emoji"
    )
    async def set_playlist_add(self, interaction: discord.Interaction, name: app_commands.Range[str, 1, 50], url: str, button_name: Optional[app_commands.Range[str, 1, 8]] = None, emoji: Optional[str] = None):
        """Add playlist button to music message."""
        # Check if all inputs contain only ASCII characters
        if not name.isascii():
            await interaction.response.send_message(embed=error_embed("Playlist name must contain only ASCII characters."), ephemeral=True)
            return
        if not url.isascii():
            await interaction.response.send_message(embed=error_embed("Playlist URL must contain only ASCII characters."), ephemeral=True)
            return
        if button_name and not button_name.isascii():
            await interaction.response.send_message(embed=error_embed("Button name must contain only ASCII characters."), ephemeral=True)
            return
        
        # Get Playlists dict from guild music data
        playlists_dict = self.get_guild_music_data(interaction.guild.id).get('playlists', {})

        # Verify there are less than 10 playlists
        if len(playlists_dict) >= 10:
            await interaction.response.send_message(embed=error_embed("Maximum number of playlists reached (10).\
                                                                      \nPlease remove a playlist with `/pl-remove` before adding a new one."), 
                                                                      ephemeral=True)
            return

        # Verify playlist name doesn't already exist
        if name in playlists_dict:
            await interaction.response.send_message(embed=error_embed(f"Playlist with name `{name}` already exists."), ephemeral=True)
            return

        # Validate URL format
        if not url_rx.match(url):
            await interaction.response.send_message(embed=error_embed("Invalid URL format. Please provide a valid URL."), ephemeral=True)
            return

        # Verify that either emoji or button_name exists
        if not emoji and not button_name:
            await interaction.response.send_message(embed=error_embed("At least one of `button_name` or `emoji` must be provided as input for this command."), ephemeral=True)
            return
        
        # Auxiliar function to validate emoji
        def is_valid_emoji(interaction: discord.Interaction, emoji: str):
            """Checks if the emoji is valid (Unicode or custom guild emoji)."""
            try:
                # Check if the emoji is a custom emoji
                if emoji.startswith('<:') and emoji.endswith('>'):
                    # Extract the emoji ID and name
                    emoji_id = int(emoji.split(':')[2][:-1])
                    emoji_name = emoji.split(':')[1]

                    # Check if the emoji exists in the guild
                    if discord.utils.get(interaction.guild.emojis, id=emoji_id):
                        return {'unicode': False, 'id': emoji_id, 'name': emoji_name}
                    return False
                
                # Check if the emoji is a valid Unicode emoji
                if len(emoji) == 1: # Single character emoji (e.g., 😊)
                    if unicodedata.category(emoji) == "So":  # "So" stands for "Symbol, Other" (used for emojis)
                        return {'unicode': True, 'name': emoji}
                    return False
                
                if len(emoji) > 1: # Multi-character emoji (e.g., 👨‍👩‍👧‍👦)
                    for char in emoji:
                        if unicodedata.category(char) != "So":
                            return False
                    return {'unicode': True, 'name': emoji}
                
                return False

            except Exception:
                return False
        
        # Validate emoji (Unicode or custom guild emoji)
        if emoji:
            emoji_dict = is_valid_emoji(interaction, emoji)
            if not emoji_dict:
                await interaction.response.send_message(embed=error_embed("Invalid emoji. Use a Unicode emoji or a custom emoji from this server."), ephemeral=True)
                return

        # Create keys and values list
        keys = ['url']
        values = [url]
        if button_name:
            keys.append('button_name')
            values.append(button_name)
        if emoji:
            keys.append('emoji')
            values.append(emoji_dict)

        # Add playlist to guild music data
        self.add_music_data(
            guild_id=interaction.guild.id,
            keys=keys,
            values=values,
            root_keys=['playlists', name]
        )

        # Update MusicPLayerView
        await self.update_musicplayerview(interaction.guild.id)

        # Send success message
        await interaction.response.send_message(embed=success_embed(f'Playlist **[{name}]({url})** added.'))
    
    @app_commands.command(name='pl-show', description='Show added playlists')
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    async def show_playlists(self, interaction: discord.Integration):
        """Show added playlists."""
        # Get playlists dictionary
        playlists = self.get_guild_music_data(interaction.guild.id).get('playlists')

        # Check if there are playlists
        if not playlists or len(playlists) == 0:
            await interaction.response.send_message(embed=info_embed('No playlists have been added yet.\nUse `/pl-add` to add a playlist.'))
            return

        # Embed with playlists info
        embed = Embed(color = discord.Colour.from_rgb(137, 76, 193), title='Playlists:')
        for i, pl_name in enumerate(playlists):
            # Get playlist emoji if exists
            if playlists[pl_name].get('emoji'):
                if playlists[pl_name].get('emoji').get('unicode'):
                    playlist_emoji = playlists[pl_name].get('emoji').get('name')
                else:
                    playlist_emoji = discord.PartialEmoji(
                        name=playlists[pl_name].get('emoji').get('name'),
                        id = playlists[pl_name].get('emoji').get('id')
                    )
            else:
                playlist_emoji = ''
            # Add playlists to embed field
            embed.add_field(
                name=f'',
                value=f'**{i+1}.** **[{pl_name}]({playlists[pl_name].get('url')})**: {playlist_emoji} {playlists[pl_name].get('button_name','')}',
                inline=False
            )
        embed.set_footer(text=f'/pl-add to add new playlists.\n/pl-remove to remove playlists.')
        await interaction.response.send_message(embed=embed)

    async def playlist_autocomplete(self, interaction: discord.Interaction, current: str):
        """Auxiliar function to autocomplete function for playlist names in inputs of / commands."""
        return [
            app_commands.Choice(name=pl_name, value=pl_name)
            for pl_name in self.get_guild_music_data(interaction.guild.id).get('playlists', {}) if current.lower() in pl_name.lower()
        ]
    @app_commands.command(name='pl-remove', description='Remove playlists')
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 5.0)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.autocomplete(name=playlist_autocomplete)
    async def remove_playlists(self, interaction: discord.Integration, name: str):
        """Remove playlists."""
        # Check if playlist exists
        if name in self.get_guild_music_data(interaction.guild.id).get('playlists', {}):
            # Delete playlist
            self.music_data[str(interaction.guild.id)]['playlists'].pop(name, None)

            # Save the updated music data
            self.save_music_data()

            # Send success message embed
            await interaction.response.send_message(embed=success_embed(f'Playlist `{name}` deleted.'))

            # Update MusicPLayerView
            await self.update_musicplayerview(interaction.guild.id)
            return
        await interaction.response.send_message(embed=warning_embed(f'Playlist named `{name}` not found.\nUse `/pl-show` to see list of existing playlists.'),
                                                ephemeral=True)

async def setup(bot):
    # Add MusicCog to bot instance
    await bot.add_cog(MusicCog(bot))