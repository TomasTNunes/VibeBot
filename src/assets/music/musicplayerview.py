import discord
from discord import PartialEmoji
from discord.ext import commands
from discord.ui import Button, View
from lavalink.events import QueueEndEvent
import random
from assets.replies.reply_embed import error_embed, success_embed, warning_embed
from assets.music.playlistbutton import PlaylistButton

class MusicPlayerView(View):
    """Class to control View with buttons for music message. Each music message has its own View instance."""
    def __init__(self, bot: commands.Bot, cog: commands.Cog, guild: discord.Guild):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.cog = cog
        self.guild = guild

        # Initialize buttons
        self.update_buttons()
    
    ######################################
    ############## UPDATES ###############
    ######################################

    def update_buttons(self):
        """
        Update button states based on connection and playback status.

        Buttons:
        - Volume down
        - Previous track
        - Resume/Pause
        - Next track
        - Volume up
        - Loop
        - Shuffle
        - AutoPlay
        - Connect/Disconnect
        - Custom Playslists

        NOTE: When using persistent views, Discord identifies buttons using custom_id across all active views, hence 
        across all MusicPlayerView instances for all guilds. If multiple instances of MusicPlayerView exist
        and they all use "connect" as the custom_id, Discord will not be able to differentiate them properly. 
        When a button is clicked, Discord sends the interaction to the first view that registered a matching custom_id.
        If multiple views with the same custom_id exist, only one will receive the interaction, and it might not be the correct one.
        Hence the custom_id should be unique for each view instance: `vibebot_connect_<guild_id>`.
        """
        # Clear previous buttons
        self.clear_items()

        # Get required connection and playback status.
        is_connected = self.guild.voice_client is not None
        player = self.cog.lavalink.player_manager.get(self.guild.id) if self.cog.lavalink else None
        if player:
            is_paused = player.paused
            is_autoplay = player.fetch("autoplay", default=False)
            is_playing = player.is_playing
        else:
            is_paused = False
            is_autoplay = False
            is_playing = False

        # Volume down button
        volume_down = Button(
            style=discord.ButtonStyle.grey,
            emoji=PartialEmoji(name="vibebot_volume_down", id=1344945898257383464),
            label='Down',
            custom_id=f"vibebot_volume_down_{self.guild.id}",
            row=0,
            disabled=not is_connected
        )
        volume_down.callback = self.volume_down_callback
        self.add_item(volume_down)

        # Previous track button
        previous_track = Button(
            style=discord.ButtonStyle.grey,
            emoji=PartialEmoji(name="vibebot_previous_track", id=1344945852061585481),
            label='Previous',
            custom_id=f"vibebot_previous_track_{self.guild.id}",
            row=0,
            disabled=not is_connected
        )
        previous_track.callback = self.previous_track_callback
        self.add_item(previous_track)

        # Resume/Pause button
        use_resume = not is_connected or is_paused or not is_playing
        resume_pause = Button(
            style=discord.ButtonStyle.green if use_resume else discord.ButtonStyle.grey,
            emoji=PartialEmoji(name="vibebot_resume", id=1344945864287715339) if use_resume else PartialEmoji(name="vibebot_pause", id=1344945843891077120),
            label='Resume' if use_resume else 'Pause',
            custom_id=f"vibebot_resume_pause_{self.guild.id}",
            row=0,
            disabled=not is_connected
        )
        resume_pause.callback = self.resume_pause_callback
        self.add_item(resume_pause)

        # Next track button
        next_track = Button(
            style=discord.ButtonStyle.grey,
            emoji=PartialEmoji(name="vibebot_next_track", id=1344945834915266600),
            label='Skip',
            custom_id=f"vibebot_next_track_{self.guild.id}",
            row=0,
            disabled=not is_connected
        )
        next_track.callback = self.next_track_callback
        self.add_item(next_track)

        # Volume up button
        volume_up = Button(
            style=discord.ButtonStyle.grey,
            emoji=PartialEmoji(name="vibebot_volume_up", id=1344945908122648586),
            label='Up',
            custom_id=f"vibebot_volume_up_{self.guild.id}",
            row=0,
            disabled=not is_connected
        )
        volume_up.callback = self.volume_up_callback
        self.add_item(volume_up)

        # Loop button
        if is_connected and player:
            if player.loop == player.LOOP_NONE:
                loop_style = discord.ButtonStyle.grey
            elif player.loop == player.LOOP_QUEUE:
                loop_style = discord.ButtonStyle.blurple
            else:
                loop_style = discord.ButtonStyle.green
        else:
            loop_style = discord.ButtonStyle.grey
        loop = Button(
            style=loop_style,
            emoji=PartialEmoji(name="vibebot_loop", id=1344997235133513801),
            label='Loop',
            custom_id=f"vibebot_loop_{self.guild.id}",
            row=1,
            disabled=not is_connected
        )
        loop.callback = self.loop_callback
        self.add_item(loop)

        # Shuffle button
        shuffle = Button(
            style=discord.ButtonStyle.grey,
            emoji=PartialEmoji(name="vibebot_shuffle", id=1344945876753317891),
            label='Shuffle',
            custom_id=f"vibebot_shuffle_{self.guild.id}",
            row=1,
            disabled=not is_connected
        )
        shuffle.callback = self.shuffle_callback
        self.add_item(shuffle)

        # Autoplay button
        autoplay = Button(
            style=discord.ButtonStyle.blurple if is_autoplay else discord.ButtonStyle.grey,
            emoji=PartialEmoji(name="vibebot_autoplay", id=1344945822156066907),
            label='AutoPlay',
            custom_id=f"vibebot_autoplay_{self.guild.id}",
            row=1,
            disabled=not is_connected
        )
        autoplay.callback = self.autoplay_callback
        self.add_item(autoplay)

        # Stop button
        stop = Button(
            style=discord.ButtonStyle.grey,
            emoji=PartialEmoji(name="vibebot_stop", id=1344945887679483997),
            label='Stop',
            custom_id=f"vibebot_stop_{self.guild.id}",
            row=1,
            disabled=not is_connected
        )
        stop.callback = self.stop_callback
        self.add_item(stop)

        # Playlists Buttons
        playlists = self.cog.get_guild_music_data(self.guild.id).get("playlists", None)
        if playlists:
            for i, pl_name in enumerate(playlists):
                # Get playlist emoji if exists
                if playlists[pl_name].get('emoji'):
                    if playlists[pl_name].get('emoji').get('unicode'):
                        playlist_emoji = playlists[pl_name].get('emoji').get('name')
                    else:
                        playlist_emoji = PartialEmoji(
                            name=playlists[pl_name].get('emoji').get('name'),
                            id = playlists[pl_name].get('emoji').get('id')
                        )
                else:
                    playlist_emoji = None

                # Create playlist button
                playlist_button = PlaylistButton(
                    url=playlists[pl_name].get('url'),
                    style=discord.ButtonStyle.grey,
                    emoji=playlist_emoji,
                    label=playlists[pl_name].get('button_name', None),
                    custom_id=f"vibebot_playlist_{pl_name}_{self.guild.id}",
                    row=2 if i<=4 else 3,
                    disabled=False
                )
                self.add_item(playlist_button)
        
        # Connect/Disconnect button
        if not playlists or len(playlists) == 0:
            connect_row = 2
        elif len(playlists) <= 5:
            connect_row = 3
        else:
            connect_row = 4
        connect = Button(
            style=discord.ButtonStyle.red if is_connected else discord.ButtonStyle.green,
            emoji=PartialEmoji(name="vibebot_disconnect", id=1344955759284191233) if is_connected else PartialEmoji(name="vibebot_connect", id=1344955706322976808),
            label="Disconnect Bot" if is_connected else "Connect Bot",
            custom_id=f"vibebot_connect_{self.guild.id}",
            row=connect_row,
            disabled=False
        )
        connect.callback = self.connect_callback
        self.add_item(connect)
    
    ######################################
    ############### EVENTS ###############
    ######################################
    
    async def interaction_check(self, interaction: discord.Interaction):
        """
        A callback that is called when an interaction happens within the view that checks whether the view should process item callbacks for the interaction.
        If the view children's callbacks should be called returns True, otherwise returns False.
        """
        # Get the custom_id of the button that was clicked and obtain button name
        custom_id = interaction.data.get("custom_id").split("_")[1]

        # If the button is connect, than the bot should join the voice channel if possible
        should_connect = True if custom_id == "connect" or custom_id == "playlist" else False

        # If the button is previous, resume, skip, loop, shuffle or stop, than the bot should be playing
        should_bePlaying = True if custom_id in ["previous", "resume", "next", "shuffle", "stop"] else False

        # Check if bot is connected
        is_connected = self.guild.voice_client is not None

        # Check if the interation should run using cog.check_and_join
        check = await self.cog.check_and_join(interaction.user, interaction.guild, should_connect, should_bePlaying)
        if check:
            await interaction.response.send_message(embed=error_embed(check), ephemeral=True)
        else:
            # After passsing check_and_join, if bot was not connected before, then it was connected in this check
            # Save this information for connect_callback_function
            interaction.extras["wasConectedDuringCheck"] = not is_connected
            return True

    
    ######################################
    ############# CALLBACKS ##############
    ######################################

    async def volume_down_callback(self, interaction: discord.Interaction):
        """"
        Handle volume down button callback. 
        
        Lower volume by 10. Minimum is 0.
        It does not needs to update MusicPlayerView.
        It needs to update music message embed, if player is playing (cause volume doesnt show if player only connected not playing).
        """
        # Get guild player
        player = self.cog.lavalink.player_manager.get(self.guild.id)

        # Get Current Volume
        volume = player.volume

        # Check if volume is already minimum (0)
        if volume == 0:
            await interaction.response.send_message(embed=error_embed("Volume is already at minimum (0%)."), ephemeral=True)
            return
        
        # Defer the interaction
        await interaction.response.defer()

        # Lower volume by 10
        volume-=10

        # Clip volume between 0 and 200
        volume = max(0, min(200, volume))

        # Set volume
        await player.set_volume(volume)

        # Update music message embed
        if player.is_playing:
            await self.cog.update_music_embed(self.guild)

    async def previous_track_callback(self, interaction: discord.Interaction):
        """
        Handle previous track button callback.
        
        Play previous track.
        It does not needs to update MusicPlayerView.
        It does not needs to update music message embed.
        """
        # Get guild player
        player = self.cog.lavalink.player_manager.get(self.guild.id)

        # Get previous track, if it exists, otherwise None
        previous_track = player.fetch(key='previous_track', default=None)

        # check if previous track exists
        if not previous_track:
            await interaction.response.send_message(embed=error_embed("No previous track."), ephemeral=True)
            return
        
        # Defer the interaction
        await interaction.response.defer()

        # Play previous track
        await player.play(previous_track)

    async def resume_pause_callback(self, interaction: discord.Interaction):
        """
        Handle resume/pause button callback.

        Pause if button is Pause. Resume if button is Resume.
        It needs to update MusicPlayerView.
        It does not needs to update music message embed.

        NOTE: When bot is connected without music playing the Resume button is shown. When in this state, clicking Resume
        will send warning that not music is playing.
        """
        # Defer the interaction
        await interaction.response.defer()

        # Get guild player
        player = self.cog.lavalink.player_manager.get(self.guild.id)
        
        # Check if player is paused
        if player.paused:
            await player.set_pause(False)
        else:
            await player.set_pause(True)

        # Update MusicPlayerView in music message
        self.update_buttons()
        await interaction.message.edit(view=self)

        # Defer the interaction 
        # (This could be above `if player.paused:` to avoid interaction failing (timeout), however it looks like interaction ends way before the pause or resume takes action)
        #await interaction.response.defer()

    
    async def next_track_callback(self, interaction: discord.Interaction):
        """
        Handle next track button callback.
        
        Skips to next track.
        It does not needs to update MusicPlayerView.
        It does not needs to update music message embed.
        """
        # Get guild player
        player = self.cog.lavalink.player_manager.get(self.guild.id)

        # Defer the interaction
        await interaction.response.defer()

        # Skip to next track
        await player.skip()
    
    async def volume_up_callback(self, interaction: discord.Interaction):
        """"
        Handle volume up button callback. 
        
        Elevate volume by 10. Maximum is 200.
        It does not needs to update MusicPlayerView.
        It needs to update music message embed, if player is playing (cause volume doesnt show if player only connected not playing).
        """
        # Get guild player
        player = self.cog.lavalink.player_manager.get(self.guild.id)

        # Get Current Volume
        volume = player.volume

        # Check if volume is already minimum (0)
        if volume == 200:
            await interaction.response.send_message(embed=error_embed("Volume is already at maximum (200%)."), ephemeral=True)
            return

        # Defer the interaction
        await interaction.response.defer()

        # Elevate volume by 10
        volume+=10

        # Clip volume between 0 and 200
        volume = max(0, min(200, volume))

        # Set volume
        await player.set_volume(volume)

        # Update music message embed
        if player.is_playing:
            await self.cog.update_music_embed(self.guild)
    
    async def loop_callback(self, interaction: discord.Interaction):
        """
        Handle loop button callback.
        
        Toggle loop.
        It needs to update MusicPlayerView.
        It does not needs to update music message embed.
        """
        # Get guild player
        player = self.cog.lavalink.player_manager.get(self.guild.id)

        if player.loop == player.LOOP_NONE:
            player.set_loop(player.LOOP_QUEUE)
            await interaction.response.send_message(embed=success_embed("Looping Queue."), ephemeral=True, delete_after=5)
        elif player.loop == player.LOOP_QUEUE:
            player.set_loop(player.LOOP_SINGLE)
            await interaction.response.send_message(embed=success_embed("Looping Track."), ephemeral=True, delete_after=5)
        elif player.loop == player.LOOP_SINGLE:
            player.set_loop(player.LOOP_NONE)
            await interaction.response.send_message(embed=success_embed("Looping Disbaled."), ephemeral=True, delete_after=5)
        
        # Update MusicPlayerView in music message
        self.update_buttons()
        await interaction.message.edit(view=self)
    
    async def shuffle_callback(self, interaction: discord.Interaction):
        """
        Handle shuffle button callback.
        
        Shuffle queue.
        It does not needs to update MusicPlayerView.
        It needs to update music message embed.
        """
        # Defer the interaction
        await interaction.response.defer()

        # Get guild player
        player = self.cog.lavalink.player_manager.get(self.guild.id)

        # Shuffle queue
        random.shuffle(player.queue)

        # Update music message embed
        await self.cog.update_music_embed(self.guild)
    
    async def autoplay_callback(self, interaction: discord.Interaction):
        """
        Handle autoplay button callback.
        
        Toggle autoplay.
        It needs to update MusicPlayerView.
        It does not needs to update music message embed.
        """
        # Defer the interaction
        await interaction.response.defer()

        # Get guild player
        player = self.cog.lavalink.player_manager.get(self.guild.id)

        # Toggle autoplay
        if not player.fetch(key="autoplay", default=False):
            player.store(key="autoplay", value=True)
        else:
            player.store(key="autoplay", value=False)

        # Update MusicPlayerView in music message
        self.update_buttons()
        await interaction.message.edit(view=self)
    
    async def stop_callback(self, interaction: discord.Interaction):
        """
        Handle stop button callback.
        
        Stop music. Resets player default settings. Triggers lavalink QueueEndEvent.
        It does not needs to update MusicPlayerView.
        It does not needs to update music message embed.
        """
        # Get guild player
        player = self.cog.lavalink.player_manager.get(self.guild.id)

        # Defer the interaction
        await interaction.response.defer()

        # Clear player queue
        player.queue.clear()

        # Set player loop to None
        player.loop = player.LOOP_NONE

        # Stop music player
        await player.stop()

        # Turn off autoplay if it's on
        player.store(key="autoplay", value=False)

        # Manually trigger the queue end logic
        await self.cog.on_queue_end(QueueEndEvent(player))
    
    async def connect_callback(self, interaction: discord.Interaction):
        """
        Handle connect/disconnect button callback.

        Connect if button is Connect. Disconnect if button is Disconnect.
        It does not needs to update MusicPlayerView.
        It does needs to update music message embed, as it is alredy handled on disconnect.

        NOTE: When entering thin callback, the bow will always be already connected (because of check_and_join()), hence
        to know when not to disconnect (when the connect button is clicked), it is necessary to know if the bot was
        connected during check_and_join(). For that interaction.extras["wasConectedDuringCheck"] is used.
        """
        # Defer the interaction
        await interaction.response.defer()

        # If bot is connected and was not connected during check, then disconnect
        # Otherwise do nothing and bot was already connected during check 
        if self.guild.voice_client is not None and not interaction.extras["wasConectedDuringCheck"]:
            await self.guild.voice_client.disconnect(force=True)