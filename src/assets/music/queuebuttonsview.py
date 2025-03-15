import discord
from discord import SelectOption
from discord.ext import commands
from discord.ui import Button, View, Select

class QueueButtonsView(View):
    """A view with queue buttons, to be used with /queue."""
    def __init__(self,
                 cog: commands.Cog,
                 guild: discord.Guild,
                 current_page: int,
                 total_pages: int):
        super().__init__()
        self.cog = cog
        self.guild = guild
        self.current_page = current_page

        # Initialize buttons
        self.update_buttons(total_pages)

    ######################################
    ############## UPDATES ###############
    ######################################

    def update_buttons(self, total_pages: int):
        """
        Update button states based on current page and total pages.
        
        Buttons:
        - Previous page
        - Refresh
        - Next page
        - Page selector (Dropdown)

        NOTE: This view os not persistent, hence after bot restarts, interations requested before will fail.
        """
        # Clear previous buttons
        self.clear_items()

        # Page selector (Dropdown)
        options = [
            discord.SelectOption(label=f"Page {i}/{total_pages}", value=str(i), default=(i == self.current_page))
            for i in range(1, total_pages + 1)
        ]
        page_selector = Select(
            options=options,
            row=0
        )
        page_selector.callback = self.page_select_callback
        self.add_item(page_selector)

        # Previous page button
        previous_page = Button(
            style=discord.ButtonStyle.grey,
            label='◁',
            row=1,
            disabled=self.current_page == 1
        )
        previous_page.callback = self.previous_page_callback
        self.add_item(previous_page)

        # Refresh button
        refresh = Button(
            style=discord.ButtonStyle.blurple,
            label='⟳',
            row=1,
        )
        refresh.callback = self.refresh_callback
        self.add_item(refresh)

        # Next page button
        next_page = Button(
            style=discord.ButtonStyle.grey,
            label='▷',
            row=1,
            disabled=self.current_page >= total_pages
        )
        next_page.callback = self.next_page_callback
        self.add_item(next_page)

    ######################################
    ######### AUXILIAR FUNCTIONS #########
    ######################################

    async def _callback(self, interaction: discord.Interaction):
        """Handles the callbacks after current page is updated."""
        # Get player for this guild
        player = self.cog.lavalink.player_manager.get(interaction.guild.id) if self.cog.lavalink else None

        # Get current track
        current_track = player.current if player else None

        # Get queue list
        queue = player.queue if player else []

        # Get queue size
        queue_size = len(queue)

        # Get queue time in ms
        queue_time = 0
        queue_time = sum(t.duration for t in queue if not t.is_stream)
        queue_time += current_track.duration if current_track and not current_track.is_stream else 0

        # Gat total number of pages
        total_pages = queue_size // 10
        total_pages += 1 if queue_size % 10 or queue_size == 0 else 0

        # Check if valid current_page
        if self.current_page > total_pages:
            self.current_page = total_pages

        # Get Queue to show
        if queue_size > 10:
            show_queue = queue[self.current_page*10-10:self.current_page*10]
        else:
            show_queue = queue
        
        # Create embed
        embed = self.cog.queue_embed(interaction.guild, 
                                 current_track, 
                                 show_queue, 
                                 queue_size, 
                                 queue_time,
                                 self.current_page,
                                 total_pages)

        # Update View
        self.update_buttons(total_pages)

        # Send embed
        await interaction.response.edit_message(embed=embed, view=self)

    ######################################
    ############# CALLBACKS ##############
    ######################################

    async def page_select_callback(self, interaction: discord.Interaction):
        """"Handle select page dropdown callback. Show chosen queue page."""
        # Set current page
        self.current_page = int(interaction.data["values"][0])

        # Run callback
        await self._callback(interaction)

    async def previous_page_callback(self, interaction: discord.Interaction):
        """"Handle previous page button callback. Show previous queue page."""
        # Decrement current page
        self.current_page -= 1

        # Run callback
        await self._callback(interaction)

    async def next_page_callback(self, interaction: discord.Interaction):
        """"Handle next page button callback. Show next queue page."""
        # Increment current page
        self.current_page += 1

        # Run callback
        await self._callback(interaction)
    
    async def refresh_callback(self, interaction: discord.Interaction):
        """"Handle refresh button callback. Refresh embed to update queue."""
        # Run callback
        await self._callback(interaction)
        