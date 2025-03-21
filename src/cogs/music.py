import os
import discord
from discord import app_commands, Embed, PartialEmoji
from discord.ext import commands
import lavalink
from lavalink.server import LoadType
from lavalink.events import TrackStartEvent, QueueEndEvent, NodeConnectedEvent, TrackEndEvent
import json
import asyncio
import re
from typing import Union, List, Any, Optional
from assets.logger.logger import music_logger as logger, music_data_logger, debug_logger
from assets.music.lavalinkvoiceclient import LavalinkVoiceClient
from assets.music.musicplayerview import MusicPlayerView
from assets.music.queuebuttonsview import QueueButtonsView
from assets.music.lastfm import LastFMClient
from assets.utils.reply_embed import error_embed, success_embed, warning_embed, info_embed

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

        # Initialize LastFM client
        self.bot.lastfm = LastFMClient(os.getenv('LASTFM_API_KEY'))
        self.lastfm = self.bot.lastfm

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
    ############# WEBHOOKS  ##############
    ######################################

    async def get_webhook(self, guild_id: int):
        """Gets an existing webhook for the music text channel, otherwise returns None."""
        # Check if we have a stored webhook for this channel
        webhook = self.get_guild_music_data(guild_id).get('music_text_channel_webhook')
        if webhook:
            try:
                return await self.bot.fetch_webhook(webhook.get('id'))
            except discord.NotFound:
                return None
            except Exception:
                return None

    async def create_webhook(self, guild_id: int, music_text_channel: Optional[discord.TextChannel] = None):
        """
        Create webhook  for the music text channel, stores it is music data and returns it.

        If music text channel doesnt exist, it returns None
        """
        # Check music text channel when not given
        if not music_text_channel:
            guild_music_data = self.get_guild_music_data(guild_id)
            guild = self.bot.get_guild(guild_id)
            music_text_channel = guild.get_channel(guild_music_data.get('music_text_channel_id')) if guild else None
            if not music_text_channel:
                return None

        # Create webhook
        webhook = await music_text_channel.create_webhook(name=f'{self.bot.user.name} Player', 
                                                          avatar=await self.bot.user.display_avatar.read())

        # Store webhook in `music_data.json`
        self.add_music_data(
            guild_id=guild_id,
            keys=['url', 'id', 'token'],
            values=[webhook.url, webhook.id, webhook.token],
            root_keys='music_text_channel_webhook'
        )

        return webhook
    
    async def get_or_create_webhook(self, guild_id: int, music_text_channel: Optional[discord.TextChannel] = None):
        """
        Gets music text channel webhok if it exists, otherwise creates it.
        
        If music text channel doesnt exist, it returns None
        """
        # Check if webhook exists
        webhook = await self.get_webhook(guild_id)
        if webhook:
            return webhook

        # Create webhook
        return await self.create_webhook(guild_id, music_text_channel=music_text_channel)

    ######################################
    ######## MUSIC TEXT CHANNEL ##########
    ######################################
    
    async def create_music_message(self, webhook: discord.Webhook):
        """Create a music message in the specified music text channel. Returns music message."""
        # Get default music message text and embed
        message_text, embed = self.get_default_music_message()

        # Get MusicPlayerView for this guild if it exists, otherwise create a new one
        musicplayerview = self.get_musicplayerview(webhook.guild_id)
        if not musicplayerview:
            musicplayerview = MusicPlayerView(self.bot, self, webhook.guild)

        # Get bot nick name in guild
        bot_guild_user = webhook.guild.get_member(self.bot.user.id)
        bot_nick = bot_guild_user.display_name if bot_guild_user else self.bot.user.name

        # Send the music message (this adds view to bots persistent views automatically)
        music_message = await webhook.send(message_text, embed=embed, view=musicplayerview, wait=True, username=bot_nick, avatar_url=self.bot.user.display_avatar.url)

        # Add guild music data to music data and save in `music_data.json`
        self.add_music_data(
            guild_id=webhook.guild_id,
            keys=['guild_id', 'music_text_channel_id', 'music_message_id'],
            values=[webhook.guild_id, webhook.channel_id, music_message.id],
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

        # Get webhook if it exists or try to create it, otherwise if it fails return
        webhook = await self.get_or_create_webhook(guild.id)
        if not webhook:
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
                queue_list += f'\nAnd **{queue_size-15}** more...'

            for i,item in enumerate(player.queue[::-1]):
                # get track position in queue
                position = queue_size-i

                # Accumulate queue time for non-streams
                if not item.is_stream:
                    queue_time += item.duration
                
                # For track beyond next 15 continue to next track
                if position > 15:
                    continue

                # Set track duration string
                if item.is_stream:
                    track_duration_str = 'LIVE'
                else:
                    track_duration_str = (
                            f'{str(item.duration // 3600000).zfill(2)}:{(item.duration % 3600000) // 60000:02d}:{(item.duration % 60000) // 1000:02d}'
                            if item.duration >= 3600000 else
                            f'{str(item.duration // 60000).zfill(2)}:{item.duration % 60000 // 1000:02d}'
                        )
                
                # Add track to queue list string
                queue_list += (
                        f'\n**{position}.** '
                        f'{item.author} - {item.title}'
                        f' - `{track_duration_str}`' 
                        if item.is_seekable else
                        f'\n**{position}.** '
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
            embed.set_thumbnail(url=current_track.artwork_url if current_track.artwork_url else self.bot.user.display_avatar.url)
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
        
        # Edit music message, if it exists
        try:
            await webhook.edit_message(guild_music_data.get('music_message_id'), content=queue_list, embed=embed, allowed_mentions=discord.AllowedMentions(users=False))
        except Exception:
            return

    async def cleanup_music_channels(self):
        """
        For all guilds:
        Remove messages from music text channels that are not the music message and create missing music messages.
        Set music message to default.
        Restore MusicPlayerView.
        """
        # Iterate through all guilds in `music_data.json`
        for guild_music_data in self.music_data.values():
            # Clean music text channel for this guild
            await self.cleanup_music_channel(guild_music_data)

        logger.info('Music text channels cleaned up, music messages set to default and MusicPlayerViews.')
    
    async def cleanup_music_channel(self, guild_music_data: dict, force_recreate: bool = False):
        """
        For given guild:
        Remove messages from music text channels that are not the music message and create missing music messages.
        Set music message to default.
        Restore MusicPlayerView.
        """
        # Get webhook
        webhook = await self.get_or_create_webhook(guild_music_data.get('guild_id'))

        # If webhook is None, it means music text channel does not exist
        # If music text channel does not exist skip iteration
        # Don't remove from music data because music data contains other information that should not be deleted
        # in case music channel is created again (deafult volume, playlists, etc.)
        # This note is important when called in cleanup_music_channels()
        if not webhook:
            return

        # get music message from ID
        music_message_id = guild_music_data.get('music_message_id')

        # delete all messages in music text channel that are not the music message, unless , force_recreate is True
        if not force_recreate:
            await webhook.channel.purge(check=lambda m: m.id != music_message_id, bulk=True)
        else:
            await webhook.channel.purge(bulk=True)

        # Get music message
        try:
            music_message = await webhook.fetch_message(music_message_id)
        except Exception:
            music_message = None

        # If music message does not exist, create it. Otherwise, set it to default
        if not music_message:
            await self.create_music_message(webhook)
            await self.update_music_embed(webhook.guild)
            return

        # Get MusicPlayerView for this guild if it exists, otherwise create a new one
        musicplayerview = self.get_musicplayerview(webhook.guild_id)
        if not musicplayerview:
            musicplayerview = MusicPlayerView(self.bot, self, webhook.guild)

        # Set  MusicPlayerView in music message
        await webhook.edit_message(music_message_id, view=musicplayerview)

        # Update Music embed
        await self.update_music_embed(webhook.guild)
    
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
        In player interactions, use `interaction.response.edit_message(view=self)`.
        """
        # Get music data for this guild in case it exists, otherwise return
        guild_music_data = self.get_guild_music_data(guild_id)
        if not guild_music_data:
            return

        # Get webhook if it exists or try to create it, otherwise if it fails return
        webhook = await self.get_or_create_webhook(guild_id)
        if not webhook:
            return
        
        # Get MusicPlayerView and update it for this guild if it exists, otherwise create a new one
        musicplayerview = self.get_musicplayerview(guild_id)
        if not musicplayerview:
            musicplayerview = MusicPlayerView(self.bot, self, webhook.guild)
        else:
            musicplayerview.update_buttons()

        # Edit music message with updated view, if it exists
        try:
            await webhook.edit_message(guild_music_data.get('music_message_id') ,view=musicplayerview)
        except Exception:
            return

                
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

        # Check if autoplay is on
        if event.player.fetch(key='autoplay', default=False):
            # Get previous track
            track = event.player.fetch(key='previous_track', default=None)

            # Get recommended track
            recommended_track = self.lastfm.get_recommendation(track['title'], track['author'])
            
            # If recommended track exists, add it to queue
            if recommended_track:
                add_to_queue_check = await self.add_to_queue(recommended_track, self.bot.user, voice_client.guild)

                # check if successful
                if not add_to_queue_check:
                    return
            
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
        
        # Get webhook
        webhook = await self.get_webhook(message.guild.id)
        
        # Ignore message from VibeBot and music text channel webhook
        if message.author == self.bot.user or message.author.id == webhook.id:
            return
        
        # Get music data for this guild in case it exists, otherwise None
        guild_music_data = self.get_guild_music_data(message.guild.id)
        music_text_channel_id = guild_music_data.get('music_text_channel_id')

        # Check is message is from a music text channel, and not from VibeBot
        if music_text_channel_id == message.channel.id:

            # Delete message asynchronously without blovking rest of function (running in parallel task)
            async def delete_message():
                try:
                    await message.delete()
                except discord.Forbidden:
                    await message.channel.send(
                        embed=error_embed("I need `manage_messages`, `read_message_history`, and `view_channel` permissions in this text channel."),
                        delete_after=15
                    )
                except discord.NotFound:
                    pass
                except Exception as e:
                    pass
            asyncio.create_task(delete_message())

            # Check if message is not from other bot    
            if message.author.bot:
                return
            
            # Check if bot should join and create player
            check = await self.check_and_join(message.author, message.guild, should_connect=True, should_bePlaying=False)
            if check:
                await message.channel.send(embed=error_embed(check), delete_after=15)
                return

            # Add query to queue and send message if not successful
            add_to_queue_check = await self.add_to_queue(message.content, message.author, message.guild)
            if add_to_queue_check:
                await message.channel.send(embed=error_embed(add_to_queue_check), delete_after=15)
                return

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

    async def add_to_queue(self, query: str, author: discord.Member, guild: discord.Guild):
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
    ######## AUXILIAR FUNCTIONS ##########
    ######################################

    async def playlist_autocomplete(self, interaction: discord.Interaction, current: str):
        """Auxiliar function to autocomplete function for playlist names in inputs of / commands."""
        return [
            app_commands.Choice(name=pl_name, value=pl_name)
            for pl_name in self.get_guild_music_data(interaction.guild.id).get('playlists', {}) if current.lower() in pl_name.lower()
        ]
    
    @staticmethod
    def is_valid_emoji(interaction: discord.Interaction, emoji: str):
        """Checks if the emoji is valid (Unicode or custom guild emoji)."""
        try:
            # Attempt to create a PartialEmoji from the string
            emoji = PartialEmoji.from_str(emoji)
            
            # If it's a custom emoji, check if it exists in the guild
            if emoji.is_custom_emoji():
                if discord.utils.get(interaction.guild.emojis, id=emoji.id):
                    return {'unicode': False, 'id': emoji.id, 'name': emoji.name}
                return False
            
            # If it's a Unicode emoji, return emoji dictionary
            return {'unicode': True, 'name': emoji.name}
        
        except Exception:
            # If from_str fails, it's not a valid emoji
            return False
    
    @staticmethod
    def queue_embed(guild: discord.Guild, 
                    current_track: lavalink.AudioTrack, 
                    queue: list[lavalink.AudioTrack],
                    queue_size: int, 
                    queue_time: int,
                    current_page: int,
                    total_pages: int):
        """Creates an embed for the queue."""
        # Initialize description of embed
        description = ""

        # Format current track
        current_track_str = None
        if current_track:
            current_track_duration_str = (
                f'{str(current_track.duration // 3600000).zfill(2)}:{(current_track.duration % 3600000) // 60000:02d}:{(current_track.duration % 60000) // 1000:02d}'
                if current_track.duration >= 3600000 else
                f'{str(current_track.duration // 60000).zfill(2)}:{current_track.duration % 60000 // 1000:02d}'
            )
            current_track_str=(
                f'[{current_track.author} - {current_track.title}]({current_track.uri})'
                f' - `{current_track_duration_str}`'
                if current_track.is_seekable else
                f'{current_track.uri}'
                f' - `{current_track_duration_str}`'
            )
        description += '**♪ Now playing**\n'
        description += f'> {current_track_str}\n\n' if current_track_str else '> `No music`\n\n'

        # Format queue
        description += f'**🎶 Tracks in queue({queue_size})**\n'
        if len(queue) == 0:
            description += '> `No track in queue`'
        for i,track in enumerate(queue):
            if track.is_stream:
                track_duration_str = 'LIVE'
            else:
                track_duration_str = (
                    f'{str(track.duration // 3600000).zfill(2)}:{(track.duration % 3600000) // 60000:02d}:{(track.duration % 60000) // 1000:02d}'
                    if track.duration >= 3600000 else
                    f'{str(track.duration // 60000).zfill(2)}:{track.duration % 60000 // 1000:02d}'
                )
            description += (
                f'**[{(current_page-1)*10+i+1}]** `-` '
                f'[{track.author} - {track.title}]({track.uri})'
                f' - `{track_duration_str}`\n' 
                if track.is_seekable else
                f'**[{(current_page-1)*10+i+1}]** `-` '
                f'{track.uri}'
                f' - `{track_duration_str}`\n'
            )

        # Create embed
        embed = Embed(
            color=discord.Colour.from_rgb(137, 76, 193),
            title=f"{guild.name} Queue",
            description=description
        )

        # Format queue time
        queue_time_str = (
            f'{str(queue_time // 3600000).zfill(2)}:{(queue_time % 3600000) // 60000:02d}:{(queue_time % 60000) // 1000:02d}'
            if queue_time >= 3600000 else
            f'{str(queue_time // 60000).zfill(2)}:{queue_time % 60000 // 1000:02d}'
        )
        embed.add_field(
            name='**⏱ Queue time**',
            value=f'> `{queue_time_str}`',
            inline=False
        )

        # Set footer with pages
        embed.set_footer(
            text=f'Page: {current_page}/{total_pages}'
        )

        return embed

    ######################################
    ############# COMMANDS ###############
    ######################################

    ######################################
    ############ / COMMANDS ##############
    ######################################
    
    ######################################
    ###### DEFINE SETTINGS / COMMANDS ####
    ######################################

    @app_commands.command(name='setup', description='Create music text channel', extras={'Category': 'Music', 'Sub-Category': 'Settings'})
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
        manage_webhooks=True
    )  # Bot must have all these permissions
    async def setup(self, interaction: discord.Interaction):
        """Setup music text channel, if it doesn't exists."""
        # Get guild music data and music text channel id
        guild_music_data = self.get_guild_music_data(interaction.guild.id)
        music_text_channel_id = guild_music_data.get('music_text_channel_id')

        # Get music text channel in case it exists in current guild, otherwise None
        music_text_channel = interaction.guild.get_channel(music_text_channel_id)

        # If music text channel exists, inform user
        if music_text_channel:
            await interaction.response.send_message(embed=warning_embed(f'Music text channel already exists: {music_text_channel.mention}'), ephemeral=True)
            return

        # Create music text channel with required permissions for bot role
        overwrites = {
            interaction.guild.me: discord.PermissionOverwrite(
                manage_channels=True,
                read_messages=True,
                read_message_history=True, 
                send_messages=True,
                manage_messages=True,
                embed_links=True,
                attach_files=True,
                add_reactions=True,
                use_external_emojis=True,
                mention_everyone=True,
                manage_webhooks=True
            )
        }
        topic_music_text_channel = "Take full control of VibeBot’s music experience: **play**, **pause**, **resume**, or **stop** \
                                    tracks; **skip to next** or jump back with **previous track** ; **loop** the entire queue or track; \
                                    **shuffle** playlists for variety; **adjust volume** on the fly; **add playlists**; **toggle  \
                                    autoplay mode** ; or **connect/disconnect** the bot. Let the vibes flow! :notes:"
        music_text_channel = await interaction.guild.create_text_channel(name="vibebot-music", overwrites=overwrites, topic=topic_music_text_channel)

        # Create music text channel webhook
        webhook = await self.get_or_create_webhook(interaction.guild.id, music_text_channel=music_text_channel)

        # Create music message in music text channel
        await self.create_music_message(webhook)

        # Infom user music text channel was created
        await interaction.response.send_message(embed=success_embed(f'Music text channel created: {music_text_channel.mention}'))
    
    @app_commands.command(name='setup-fix', description='Recreate music text message in music text channel', extras={'Category': 'Music', 'Sub-Category': 'Settings'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.bot_has_permissions(
        read_message_history=True,
        manage_messages=True,
        send_messages=True,
        embed_links=True,
        manage_webhooks=True
    ) 
    async def fix_setup(self, interaction: discord.Interaction):
        """Fix music music text channel. Recreate music text message. Deletes all other messages in music text channel."""
        # Get musicd data for this guild
        guild_music_data = self.get_guild_music_data(interaction.guild.id)

        # Get music text channel in case it exists in current guild, otherwise None
        music_text_channel = interaction.guild.get_channel(guild_music_data.get('music_text_channel_id'))

        # If music text channel doesn't exist, inform user to /setup
        if not music_text_channel:
            await interaction.response.send_message(embed=warning_embed(f'Music text channel does not exist./nUse `/setup` to create one.'), ephemeral=True)
            return
        
        # Prevents the interaction from timing out
        await interaction.response.defer(ephemeral=True)

        # Clean music text channel
        await self.cleanup_music_channel(guild_music_data, force_recreate=True)

        # Success message
        await interaction.followup.send(embed=success_embed(f'Music text channel fixed.'))
    
    @app_commands.command(name='default-volume', description='Set the defauft volume when the bot joins a voice channel', extras={'Category': 'Music', 'Sub-Category': 'Settings'})
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
    
    @app_commands.command(name='default-autoplay', description='Enable or Disable autoplay by default when the bot joins a voice channel', extras={'Category': 'Music', 'Sub-Category': 'Settings'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.choices(state=[
    app_commands.Choice(name="Enable", value=1),
    app_commands.Choice(name="Disable", value=0)
    ])
    @app_commands.describe(
        state="Enable/Disable default autoplay",
    )
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
    
    @app_commands.command(name='default-loop', description='Enable or Disable loop queue by default when the bot joins a voice channel', extras={'Category': 'Music', 'Sub-Category': 'Settings'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.choices(state=[
    app_commands.Choice(name="Enable", value=1),
    app_commands.Choice(name="Disable", value=0)
    ])
    @app_commands.describe(
        state="Enable/Disable default loop queue",
    )
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
    
    @app_commands.command(name='auto-disconnect', description='Enable or Disable auto-disconnect when idle. Change auto-disconnect idle timer.', extras={'Category': 'Music', 'Sub-Category': 'Settings'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.choices(state=[
    app_commands.Choice(name="Enable", value=1),
    app_commands.Choice(name="Disable", value=0)
    ])
    @app_commands.describe(
        state="Enable/Disable auto-disconnect",
        timer="Set auto-disconnect idle timer in seconds",
    )
    async def set_idle_timer(self, interaction: discord.Integration, state: Optional[app_commands.Choice[int]] = None, timer: Optional[app_commands.Range[int, 10, 3600]] = None):
        """Enable or Disable auto-disconnect when idle. Change auto-disconnect idle timer."""
        # Check if any arguments used
        if not state and not timer:
            await interaction.response.send_message(embed=error_embed("You must provide at least one argument."), ephemeral=True)
            return
        
        # Set state, if state provided
        if state:
            self.add_music_data(
                guild_id=interaction.guild.id,
                keys='auto_disconnect',
                values=bool(state.value)
            )

        # Set timer, if timer provided
        if timer:
            self.add_music_data(
                guild_id=interaction.guild.id,
                keys='idle_timer',
                values=timer
            )
        
        # Send info message
        if self.get_guild_music_data(interaction.guild.id).get('auto_disconnect', True):
            await interaction.response.send_message(embed=info_embed(f'Auto-disconnect `enabled`.\nIdle timer: `{self.get_guild_music_data(interaction.guild.id).get('idle_timer', 300)}s`'))
        else:
            await interaction.response.send_message(embed=info_embed(f'Auto-disconnect `disabled`.'))
    
    @app_commands.command(name='settings', description='Shows guild\'s music player settings', extras={'Category': 'Music', 'Sub-Category': 'Settings'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    async def settings(self, interaction: discord.Integration):
        """Shows guild's music player settings."""
        # Get guild music data
        guild_music_data = self.get_guild_music_data(interaction.guild.id)

        # Get music text channel
        music_text_channel = interaction.guild.get_channel(guild_music_data.get('music_text_channel_id'))
        
        # Get music message
        try:
            music_message = await music_text_channel.fetch_message(guild_music_data.get('music_message_id')) if music_text_channel else None
        except Exception as e:
            music_message = None
        
        # Create embed
        embed = Embed(
            color=discord.Colour.from_rgb(137, 76, 193),
            title=f'🎶 {interaction.guild.name} - Music Player Settings'
        )

        # Add fields with channel/message and settings info
        embed.add_field(
            name="📌 **Channels & Messages**",
            value=(
                f'🔖 **Music Text Channel:** {music_text_channel.mention if music_text_channel else "*None*"}\n'
                f'💬 **Music Message:** {music_message.jump_url if music_message else "*None*"}\n'
            ),
            inline=False
        )

        embed.add_field(
            name="⚙️ **Playback Settings**",
            value=(
                f'🔊 **Default Volume:** `{guild_music_data.get("default_volume", 50)}%`\n'
                f'🎵 **Default Autoplay:** `{guild_music_data.get("default_autoplay", "False")}`\n'
                f'🔁 **Default Loop Queue:** `{guild_music_data.get("default_loop", "False")}`\n'
            ),
            inline=False
        )

        embed.add_field(
            name="🛠 **Bot Behavior**",
            value=(
                f'🔌 **Auto Disconnect:** `{guild_music_data.get("auto_disconnect", "True")}`\n'
                f'⏳ **Idle Timer:** `{guild_music_data.get("idle_timer", 300)}s`\n'
            ),
            inline=False
        )

        # Send embed
        await interaction.response.send_message(embed=embed)
    
    ######################################
    ########## PLAYER / COMMANDS #########
    ######################################
    
    @app_commands.command(name='volume', description='Change bot\'s audio volume', extras={'Category': 'Music', 'Sub-Category': 'Player'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 3.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.describe(
        volume="Set the player volume (0-200)"
    )
    async def volume(self, interaction: discord.Interaction, volume: app_commands.Range[int, 0, 200]):
        """Change bot's audio volume."""
        # Check if command should continue using check_and_join()
        check = await self.check_and_join(interaction.user, interaction.guild, should_connect=False, should_bePlaying=False)
        if check:
            await interaction.response.send_message(embed=error_embed(check), ephemeral=True)
            return

        # Get player for this guild
        player = self.lavalink.player_manager.get(interaction.guild.id)

        # Set player volume
        await player.set_volume(volume)

        # Update music message embed
        if player.is_playing:
            await self.update_music_embed(interaction.guild)

        # Send success message
        await interaction.response.send_message(embed=success_embed(f'Volume set to `{volume}%`'), delete_after=7)
    
    @app_commands.command(name='seek', description='Skips to a specified time in the current song', extras={'Category': 'Music', 'Sub-Category': 'Player'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 3.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.describe(
        time="Time to skip to (in seconds)",
    )
    async def seek_time(self, interaction: discord.Integration, time: app_commands.Range[int, 0, 999999999]):
        """Skips to a specific time in the current song."""
        # Check if command should continue using check_and_join()
        check = await self.check_and_join(interaction.user, interaction.guild, should_connect=False, should_bePlaying=True)
        if check:
            await interaction.response.send_message(embed=error_embed(check), ephemeral=True)
            return

        # Get player for this guild
        player = self.lavalink.player_manager.get(interaction.guild.id)

        # Get current track
        current_track = player.current

        # Get current track duration
        current_track_duration = current_track.duration / 1000

        # Check if given time is valid
        if time > current_track_duration:
            await interaction.response.send_message(embed=error_embed(f'Invalid time. Current track is `{int(current_track_duration)}` seconds long.'), ephemeral=True)
            return

        # Seek to given time
        await player.seek(time * 1000)

        # Send success message
        await interaction.response.send_message(embed=success_embed(f'Skipped to `{time}` seconds'), delete_after=7)
    
    @app_commands.command(name='fast-forward', description='Fast forwards the current track by a specificied ammount. Default is 15 seconds.', extras={'Category': 'Music', 'Sub-Category': 'Player'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 3.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.describe(
        time="Time to fast forward by (in seconds)",
    )
    async def fast_forward(self, interaction: discord.Integration, time: Optional[app_commands.Range[int, 0, 999999999]] = 15):
        """Fast forwards the current track by a specificied ammount. Default is 15 seconds."""
        # Check if command should continue using check_and_join()
        check = await self.check_and_join(interaction.user, interaction.guild, should_connect=False, should_bePlaying=True)
        if check:
            await interaction.response.send_message(embed=error_embed(check), ephemeral=True)
            return

        # Get player for this guild
        player = self.lavalink.player_manager.get(interaction.guild.id)

        # Seek to given time
        await player.seek(player.position + time * 1000)

        # Send success message
        await interaction.response.send_message(embed=success_embed(f'Fast forwarded by `{time}` seconds.\nNew position: `{int(player.position / 1000)}s`'), delete_after=7)
    
    @app_commands.command(name='rewind', description='Rewinds the current track by a specificied ammount. Default is 15 seconds.', extras={'Category': 'Music', 'Sub-Category': 'Player'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 3.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.describe(
        time="Time to rewind by (in seconds)",
    )
    async def rewind(self, interaction: discord.Integration, time: Optional[app_commands.Range[int, 0, 999999999]] = 15):
        """Rewinds the current track by a specificied ammount. Default is 15 seconds."""
        # Check if command should continue using check_and_join()
        check = await self.check_and_join(interaction.user, interaction.guild, should_connect=False, should_bePlaying=True)
        if check:
            await interaction.response.send_message(embed=error_embed(check), ephemeral=True)
            return

        # Get player for this guild
        player = self.lavalink.player_manager.get(interaction.guild.id)

        # Seek to given time
        await player.seek(player.position - time * 1000)

        # Send success message
        await interaction.response.send_message(embed=success_embed(f'Rewound by `{time}` seconds.\nNew position: `{int(player.position / 1000)}s`'), delete_after=7)
    
    ######################################
    ########### QUEUE / COMMANDS #########
    ######################################

    @app_commands.command(name='queue', description='Shows the queue', extras={'Category': 'Music', 'Sub-Category': 'Queue'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 5.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    async def queue(self, interaction: discord.Integration):
        """Shows the queue."""
        # Check if command should continue using check_and_join()
        check = await self.check_and_join(interaction.user, interaction.guild, should_connect=False, should_bePlaying=False)
        if check:
            await interaction.response.send_message(embed=error_embed(check), ephemeral=True)
            return
        
        # Get player for this guild
        player = self.lavalink.player_manager.get(interaction.guild.id)

        # Get current track
        current_track = player.current

        # Get queue list
        queue = player.queue

        # Get queue size
        queue_size = len(queue)

        # Get queue time in ms
        queue_time = 0
        queue_time = sum(t.duration for t in queue if not t.is_stream)
        queue_time += current_track.duration if current_track and not current_track.is_stream else 0

        # Get first 10 or less tracks to show
        if queue_size > 10:
            show_queue = queue[:10]
        else:
            show_queue = queue

        # Gat total number of pages
        total_pages = queue_size // 10
        total_pages += 1 if queue_size % 10 or queue_size == 0 else 0
        
        # Create embed
        embed = self.queue_embed(interaction.guild, 
                                 current_track, 
                                 show_queue, 
                                 queue_size, 
                                 queue_time,
                                 1,
                                 total_pages)

        # Send embed
        await interaction.response.send_message(embed=embed, view=QueueButtonsView(self, interaction.guild, 1, total_pages), ephemeral=True)

    @app_commands.command(name='clear-queue', description='Clear the queue', extras={'Category': 'Music', 'Sub-Category': 'Queue'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 5.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    async def clear_queue(self, interaction: discord.Integration):
        """Clear the queue."""
        # Check if command should continue using check_and_join()
        check = await self.check_and_join(interaction.user, interaction.guild, should_connect=False, should_bePlaying=True)
        if check:
            await interaction.response.send_message(embed=error_embed(check), ephemeral=True)
            return

        # Get player for this guild
        player = self.lavalink.player_manager.get(interaction.guild.id)

        # Clear queue
        player.queue.clear()

        # Update music message embed
        await self.update_music_embed(interaction.guild)

        # Send success message
        await interaction.response.send_message(embed=success_embed(f'Queue cleared.'), delete_after=7)
    
    @app_commands.command(name='jump', description='Jump to specified track in the queue', extras={'Category': 'Music', 'Sub-Category': 'Queue'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 5.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.describe(
        position="Position of track in queue",
    )
    async def jump(self, interaction: discord.Integration, position: app_commands.Range[int, 1, 999999999]):
        """Jump to specified track in the queue."""
        # Check if command should continue using check_and_join()
        check = await self.check_and_join(interaction.user, interaction.guild, should_connect=False, should_bePlaying=True)
        if check:
            await interaction.response.send_message(embed=error_embed(check), ephemeral=True)
            return

        # Get player for this guild
        player = self.lavalink.player_manager.get(interaction.guild.id)

        # Get queue list
        queue = player.queue

        # Check if given position is valid
        if position > len(queue):
            await interaction.response.send_message(embed=error_embed(f'Position must be between `1` and `{len(queue)}`.'), ephemeral=True)
            return

        # Check if loop queue is enabled
        if player.loop == player.LOOP_QUEUE:
            player.queue = queue[position - 1:] + queue[:position - 1]
        else:
            player.queue = queue[position - 1:]
        
        # Play selected track
        if player.loop == player.LOOP_SINGLE:
            await player.play(player.queue.pop(0))
        else:
            await player.skip()

        # Send success message
        await interaction.response.send_message(embed=success_embed(f'Jumped to position `{position}` in queue.'), delete_after=7)
    
    @app_commands.command(name='remove', description='Remove specified track from queue', extras={'Category': 'Music', 'Sub-Category': 'Queue'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 5.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.describe(
        position="Position of track in queue",
    )
    async def remove_from_queue(self, interaction: discord.Integration, position: app_commands.Range[int, 1, 999999999]):
        """Remove specified track from queue"""
        # Check if command should continue using check_and_join()
        check = await self.check_and_join(interaction.user, interaction.guild, should_connect=False, should_bePlaying=True)
        if check:
            await interaction.response.send_message(embed=error_embed(check), ephemeral=True)
            return

        # Get player for this guild
        player = self.lavalink.player_manager.get(interaction.guild.id)

        # Get queue list
        queue = player.queue

        # Check if given position is valid
        if position > len(queue):
            await interaction.response.send_message(embed=error_embed(f'Position must be between `1` and `{len(queue)}`.'), ephemeral=True)
            return

        # Remove track from queue
        removed_track = player.queue.pop(position-1)

        # Update music message embed
        await self.update_music_embed(interaction.guild)

        # Send success message
        message = (
            f'Track `{position}. {removed_track.author} - {removed_track.title}` removed from queue.'
            if removed_track.is_seekable else
            f'Track `{position}. {removed_track.uri}` removed from queue.'
        )
        await interaction.response.send_message(embed=success_embed(message), delete_after=7)
    
    @app_commands.command(name='move', description='Move specified track in queue', extras={'Category': 'Music', 'Sub-Category': 'Queue'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 5.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.rename(
    frrom="from"  
    )
    @app_commands.describe(
        frrom="Current position of track in queue",
        to="New position of track in queue"
    )
    async def move(self, interaction: discord.Integration, frrom: app_commands.Range[int, 1, 999999999], to: app_commands.Range[int, 1, 999999999]):
        """Move specified track in queue."""
        # Check if command should continue using check_and_join()
        check = await self.check_and_join(interaction.user, interaction.guild, should_connect=False, should_bePlaying=True)
        if check:
            await interaction.response.send_message(embed=error_embed(check), ephemeral=True)
            return

        # Get player for this guild
        player = self.lavalink.player_manager.get(interaction.guild.id)

        # Check if given from position is valid
        if frrom > len(player.queue):
            await interaction.response.send_message(embed=error_embed(f'`from` position must be between `1` and `{len(player.queue)}`.'), ephemeral=True)
            return

        # Check if to position is valid
        if to > len(player.queue):
            to = len(player.queue)

        # Move track in queue
        track = player.queue.pop(frrom-1)
        player.queue.insert(to-1, track)

        # Update music message embed
        await self.update_music_embed(interaction.guild)

        # Send success message
        message = (
            f'Moved track `{track.author} - {track.title}` from **{frrom}.** to **{to}.** in queue.'
            if track.is_seekable else
            f'Moved track `{track.uri}` from **{frrom}.** to **{to}.** in queue.'
        )
        await interaction.response.send_message(embed=success_embed(message), delete_after=7)
    
    ######################################
    ######### PLAYLISTS / COMMANDS #######
    ######################################

    # Create Playlists Group
    pl = app_commands.Group(name='pl', description='Manage playlists', extras={'Category': 'Music', 'Sub-Category': 'Playlist'})
    
    @pl.command(name='add', description='Add playlist button to music message', extras={'Category': 'Music', 'Sub-Category': 'Playlist'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 5.0)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.choices(shuffle=[
    app_commands.Choice(name="Yes", value=1),
    app_commands.Choice(name="No", value=0)
    ])
    @app_commands.describe(
        name="Playlist name (1-50 characters)",
        url="Playlist url (Spotify, Youtube, Soundcloud, AppleMusic, etc.)",
        button_name="Playlist button name (1-8 characters)",
        emoji="Playlist button emoji",
        shuffle="If playlist should be shuffled when played. Default: `No`",
    )
    async def add_playlist(self, 
                               interaction: discord.Interaction, 
                               name: app_commands.Range[str, 1, 50], 
                               url: str, 
                               button_name: Optional[app_commands.Range[str, 1, 8]] = None, 
                               emoji: Optional[str] = None,
                               shuffle: Optional[app_commands.Choice[int]] = None
                               ):
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
                                                                      \nPlease remove a playlist with `/pl remove` before adding a new one."), 
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
        
        # Validate emoji (Unicode or custom guild emoji)
        if emoji:
            emoji_dict = self.is_valid_emoji(interaction, emoji)
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
        if shuffle:
            keys.append('shuffle')
            values.append(bool(shuffle.value))

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
    
    @pl.command(name='list', description='List all saved playlists', extras={'Category': 'Music', 'Sub-Category': 'Playlist'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    async def show_playlists(self, interaction: discord.Interaction):
        """List all saved playlists."""
        # Get playlists dictionary
        playlists = self.get_guild_music_data(interaction.guild.id).get('playlists')

        # Check if there are playlists
        if not playlists or len(playlists) == 0:
            await interaction.response.send_message(embed=info_embed('🎵 No playlists have been added yet.\nUse `/pl add` to add a playlist.'))
            return

        # Create embed
        embed = discord.Embed(
            color=discord.Colour.from_rgb(137, 76, 193),
            title="📂 Your Saved Playlists",
            description=""
        )

        # Loop through playlists
        for i, pl_name in enumerate(playlists):
            playlist = playlists[pl_name]
            
            # Get emoji
            emoji = ""
            if playlist.get('emoji'):
                if playlist['emoji'].get('unicode'):
                    emoji = playlist['emoji']['name']
                else:
                    emoji = f"<:{playlist['emoji']['name']}:{playlist['emoji']['id']}>"

            # Get button label
            button_label = playlist.get('button_name', '')
            button_label = f'`{button_label}`' if button_label else ''

            # Combine emoji and button label (ensure no extra spaces)
            button_display = f"{emoji} {button_label}".strip()

            # Format playlist details
            embed.add_field(
                name='',
                value=(
                    f"**[{i+1}]** - 🎶  **[{pl_name}]({playlist['url']})**  🎶\n"
                    f"*Button:* {button_display}\n"
                    f"*Shuffle:* `{playlist.get('shuffle', False)}`"
                ),
                inline=False
            )

        # Footer
        embed.set_footer(text="➕ Use /pl add to add a playlist\n➖ Use /pl remove to a playlist")

        # Send embed
        await interaction.response.send_message(embed=embed)

    @pl.command(name='remove', description='Remove saved playlist', extras={'Category': 'Music', 'Sub-Category': 'Playlist'})
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 5.0)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.bot_has_permissions(embed_links=True)
    @app_commands.autocomplete(name=playlist_autocomplete)
    @app_commands.describe(
        name="Name of playlist you wish to remove",
    )
    async def remove_playlists(self, interaction: discord.Integration, name: str):
        """Remove saved playlist."""
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
        await interaction.response.send_message(embed=warning_embed(f'Playlist named `{name}` not found.\nUse `/pl list` to see list of existing playlists.'),
                                                ephemeral=True)

async def setup(bot):
    # Add MusicCog to bot instance
    await bot.add_cog(MusicCog(bot))