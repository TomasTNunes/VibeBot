import discord
from discord.ext import commands
from typing import Callable
import lavalink

class QueueButtonsView(discord.ui.View):
    """A view with queue buttons, to be used with /queue."""
    def __init__(self, 
                 guild: discord.Guild, 
                 create_embed: Callable[[discord.Guild, lavalink.AudioTrack, list[lavalink.AudioTrack], int, int, int, int], discord.Embed]):
        super().__init__()
        self.guild = guild
        self.create_embed = create_embed
        