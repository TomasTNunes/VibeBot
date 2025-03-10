import discord
import lavalink
from lavalink.errors import ClientError
import asyncio
from assets.logger.logger import debug_logger
from assets.utils.reply_embed import error_embed, success_embed, warning_embed

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
        self.guild = channel.guild
        self.guild_id = channel.guild.id
        self.cog = self.client.get_cog("MusicCog")
        self._destroyed = False

        if not hasattr(self.client, 'lavalink'):
            # Instantiate a client if one doesn't exist.
            # We store it in `self.client` so that it may persist across cog reloads,
            # however this is not mandatory.
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node(host='localhost', port=2333, password='youshallnotpass',
                                          region='eu', name='music-node')

        # Create a shortcut to the Lavalink client here.
        self.lavalink = self.client.lavalink

        # Task to track auto-disconnect due to idle task
        self.idle_task = None
    
    async def start_idle_timer(self):
        """Starts a idle timer to disconnect if idle."""
        # Stop task if it exists
        self.stop_idle_timer()

        # Start new task, if auto-disconnect is enabled
        if self.cog.get_guild_music_data(self.guild_id).get('auto_disconnect', True):
            self.idle_task = asyncio.create_task(self._check_idle_disconnect())

    async def _check_idle_disconnect(self):
        """Background task to check for idle time of continuous inactivity."""
        # Wait idle timer
        await asyncio.sleep(self.cog.get_guild_music_data(self.guild_id).get('idle_timer', 300))

        # Get player for this guild
        player = self.lavalink.player_manager.get(self.guild_id)

        # Disconnect only if player is not playing
        if player and not player.is_playing:
            await self.disconnect(force=True)

            # Send Warning to music text channel that bot has been disconnected for being idle
            guild_music_data = self.cog.get_guild_music_data(self.guild_id)
            music_text_channel = self.guild.get_channel(guild_music_data['music_text_channel_id']) if guild_music_data else None
            if music_text_channel:
                await music_text_channel.send(embed=warning_embed(f"I left the voice channel due to inactivity.\nUse `/auto-disconnect` to disable the auto-disconnect or change the idle timer."), 
                                                delete_after=15)
            
    def stop_idle_timer(self):
        """Stops idle task timer."""
        # Cancel task if it exists
        if self.idle_task:
            self.idle_task.cancel()
        self.idle_task = None

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        """
        This method whenever a voice state is updated.
        
        NOTE: This function is called when bot is connected, moves or is moved and disconeects or is disconnected. 
        """
        channel_id = data['channel_id']

        # When bot is disconnected
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
        player = self.lavalink.player_manager.create(guild_id=self.guild_id)

        ##########################################
        ####### SET PLAYER DEFAULT SETTINGS ######
        ##########################################

        # Set default volume
        await player.set_volume(self.cog.get_guild_music_data(self.guild_id).get('default_volume', 50))

        # Set default autoplay
        player.store(key="autoplay", value=self.cog.get_guild_music_data(self.guild_id).get('default_autoplay', False))

        # Set default loop
        if self.cog.get_guild_music_data(self.guild_id).get('default_loop', False):
            player.set_loop(player.LOOP_QUEUE)

        # Connect
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

        ##########################################
        ######### HANDLE CONNECT ACTIONS #########
        ##########################################

        # start idle task timer
        await self.start_idle_timer()

        # Update MusicPlayerView in music message
        await self.cog.update_musicplayerview(self.guild_id)

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.

        NOTE: When bot is disconnected by someone else this function is not called.
        """
        player = self.lavalink.player_manager.get(self.guild_id)

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

        ##########################################
        ####### HANDLE DISCONNECT ACTIONS ########
        ##########################################

        # Update MusicPlayerView in music message
        await self.cog.update_musicplayerview(self.guild_id)

        # Update music message embed
        await self.cog.update_music_embed(self.guild)
        
        # Cancel idle task (If I uncomment, the message warning bot disconnected isnt deleted)
        #self.stop_idle_timer()