import discord

class InviteButtonView(discord.ui.View):
    """A view with an invite button, to be used with /invite"""
    def __init__(self):
        super().__init__()
        # Invite url
        self.inv_url = 'https://discord.com/oauth2/authorize?client_id=1343092449702187028'

        # Invite Button
        self.add_item(discord.ui.Button(
            label="Invite VibeBot to your server", 
            url=self.inv_url, 
            style=discord.ButtonStyle.link
            )
        )
