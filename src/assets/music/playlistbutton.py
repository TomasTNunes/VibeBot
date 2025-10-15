import discord
import random
from assets.utils.reply_embed import error_embed, success_embed, warning_embed

class PlaylistButton(discord.ui.Button):
    """Class inherited from discord.ui.Button to handle MusicPlayerView Playlist buttons."""
    def __init__(self, url: str, shuffle: bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pl_url = url
        self.shuffle = shuffle
    
    async def callback(self, interaction: discord.Interaction):
        """
        Callback for when a playlist button is clicked.

        Adds playlists to guilds player queue.
        It does not needs to update MusicPlayerView.
        It needs to update music message embed, if shuffle is True.

        NOTE: This  buttons is to be used in MusicPLayerView, hence join_and_check() will be ran there as interaction_check.
        """
        # Get guild player
        player = self.view.cog.lavalink.player_manager.get(interaction.guild.id)

        # Is shuffle is True, set lavalink shuffle for random first song
        player.set_shuffle(self.shuffle)

        # Add playlists url to queue
        add_to_queue_check = await self.view.cog.add_to_queue(self.pl_url, interaction.user, interaction.guild)

        # Set lavalink shuffle to False
        player.set_shuffle(False)

        # If add_to_queue_check is not None, something went wrong
        if add_to_queue_check:
            await interaction.response.send_message(embed=error_embed(add_to_queue_check), delete_after=15)
            return
        
        # Defer the interaction
        await interaction.response.defer()

        # Shuffle rest of queue if shuffle is True
        if self.shuffle:
            random.shuffle(player.queue)

            # Update music message embed
            await self.view.cog.update_music_embed(interaction.guild)
        
