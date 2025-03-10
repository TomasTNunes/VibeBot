import discord
import os

class InviteButtonView(discord.ui.View):
    """A view with an invite button, to be used with /invite"""
    def __init__(self):
        super().__init__()
        # Invite url
        self.inv_url = os.getenv('INVITE_LINK')

        # Invite Button
        self.add_item(discord.ui.Button(
            label="Invite VibeBot to your server", 
            url=self.inv_url, 
            style=discord.ButtonStyle.link
            )
        )
