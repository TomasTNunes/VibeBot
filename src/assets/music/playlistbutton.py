import discord
from assets.replies.reply_embed import error_embed, success_embed, warning_embed

class PlaylistButton(discord.ui.Button):
    """Class inherited from discord.ui.Button to handle MusicPlayerView Playlist buttons."""
    def __init__(self, url: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pl_url = url
    
    async def callback(self, interaction: discord.Interaction):
        """
        Callback for when a playlist button is clicked.

        Adds playlists to guilds player queue.
        It does not needs to update MusicPlayerView.
        It does not needs to update music message embed.

        NOTE: This  buttons is to be used in MusicPLayerView, hence join_and_check() will be ran there as interaction_check.
        """
        # Defer the interaction
        await interaction.response.defer()

        # Add playlists url to queue
        add_to_queue_check = await self.view.cog.add_to_queue(self.pl_url, interaction.user, interaction.guild)
        if add_to_queue_check:
            await interaction.followup.send(embed=error_embed(add_to_queue_check), delete_after=15)
            return
        
