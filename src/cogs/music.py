import os
import discord
from discord import app_commands, Embed
from discord.ext import commands
import lavalink
import json
import asyncio
from assets.logs.logger import music_logger as logger, music_data_logger, debug_logger
from assets.music.lavalinkvoiceclient import LavalinkVoiceClient

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

        # Ondisconnect clean guild from music data
        # qd o bot liga reset sala? ou so editar para mensagem default (caso exista); se sala nao existir nao fazer nada; se sala existir e mensagem nao reset_setup?; 
        # apagar todas as mensagens daquela sala que nao seja a music message

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
                        host='localhost', port=2333, password='youshallnotpass',
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
            with open(self.music_data_path, 'r') as file:
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
        try:
            with open(self.music_data_path, 'w') as file:
                json.dump(self.music_data, file, indent=4)
                music_data_logger.info(f'Music data saved to `music_data.json`.')
        except Exception as e:
            logger.error(f'Failed to save music data: {e}')
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

    def add_music_data(self, guild_id: int, music_text_channel_id: int, music_message_id: int, default_volume: int = 50):
        """Add music data for the specified guild. If the guild already exists, update the data."""
        self.music_data[str(guild_id)] = {
            'guild_id': guild_id,
            'music_text_channel_id': music_text_channel_id,
            'music_message_id': music_message_id,
            'default_volume': default_volume
        }
        music_data_logger.info(f'Music data for guild {guild_id} added/updated.')
        self.save_music_data()
    
    def get_music_data(self, guild_id: int):
        """
        Get music data for the specified guild.
        Returns music data for the specified guild in the format of a dictionary:
        {
            'guild_id': 1234567890,
            'music_text_channel_id': 1234567890,
            'music_message_id': 1234567890,
            'default_volume': 50
        }
        If the guild does not exist, return None.
        """
        return self.music_data.get(str(guild_id))

    ######################################
    ######## MUSIC TEXT CHANNEL ##########
    ######################################
    
    async def create_music_message(self, music_text_channel: discord.TextChannel):
        """Create a music message in the specified music text channel. Returns music message."""
        # Get default music message text and embed
        message_text, embed = self.get_default_music_message()

        # Send the music message
        music_message = await music_text_channel.send(message_text, embed=embed)

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
                
    ######################################
    ########## LAVALINK EVENTS ###########
    ######################################
    
    ######################################
    ########### DISCORD EVENTS ###########
    ######################################

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Handle bot leaving a server. Remove guild from music data."""
        # Removes guild from music data, if it exists
        if self.music_data.pop(str(guild.id), None):
            music_data_logger.info(f'Music data for guild {guild.id} removed.')

            # Save the updated music data
            self.save_music_data()
    
    ######################################
    ######### BOT JOIN & CHECK ###########
    ######################################

    async def check_and_join(self, author: discord.Member, guild: discord.Guild, should_connect: bool):
        """
        This function serves as a prerequisite check for all music-related commands. 
        It ensures that a player exists for the guild and attempts to connect the bot to the author's voice channel when possible. 
        If successful, it returns True. Otherwise, it returns False and informs the user of the issue.

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
            return False
        
        # Create player if not exists
        self.lavalink.player_manager.create(guild.id)

        # Get Bot voice client if exists, otherwise None
        voice_client = guild.voice_client

        # Check if author is in voice channel
        if not author.voice or not author.voice.channel:
            # Check if bot is in voice channel.
            if voice_client is not None:
                # If yes, inform to join the same channel
                print('You need to join my voice channel first.')
                return False
            # If not, inform to join a voice channel
            print('Join a voice channel first.')
            return False

        # Get author voice channel
        voice_channel = author.voice.channel

        # If bot is not in voice channel, and author is in voice channel
        if voice_client is None:
            # Stop for commands that require bot to already be in voice channel
            if not should_connect:
                print('I\'m not playing music.')
                return False
            
            # Get bot's permission in the author's voice channel
            permissions = voice_channel.permissions_for(guild.me)

            # Check if bot has permission to connect and speak in the author's voice channel
            if not permissions.connect or not permissions.speak:
                print('I need `CONNECT` and `SPEAK` permissions.')
                return False

            # Check if author's voice channel has user limit, is full and if bot has permission to move members (as it allows to enter full voice channel)
            if (voice_channel.user_limit > 0) and (len(voice_channel.members) >= voice_channel.user_limit) and not guild.me.guild_permissions.move_members:
                print('Your voice channel is full.')
                return False

            # Connect to author's voice channel
            await voice_channel.connect(cls=LavalinkVoiceClient)
        
        # If bot is in voice channel, but not in author's voice channel
        elif voice_client.channel.id != voice_channel.id:
            print('You need to join my voice channel first.')
            return False
        
        # If bot connected to author's voice channel
        return True

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
                await interaction.response.send_message("This command cannot be used in private messages.", ephemeral=True)
            
            # Handle MissingPermissions: An exception raised when the command invoker lacks permissions to run a command.
            elif isinstance(error, app_commands.MissingPermissions):
                msg_text = 'You need the following permissions to run this command:'
                for permission in error.missing_permissions:
                    msg_text += f' `{permission}`,'
                msg_text = msg_text[:-1]+'.'
                await interaction.response.send_message(msg_text, ephemeral=True)
            
            # Handle BotMissingPermissions: An exception raised when the bot’s member lacks permissions to run a command.
            elif isinstance(error, app_commands.BotMissingPermissions):
                msg_text = 'I need the following permissions to run this command:'
                for permission in error.missing_permissions:
                    msg_text += f' `{permission}`,'
                msg_text = msg_text[:-1]+'.'
                await interaction.response.send_message(msg_text, ephemeral=True)
            
            # Handle CommandOnCooldown: An exception raised when the command being invoked is on cooldown.
            elif isinstance(error, app_commands.CommandOnCooldown):
                await interaction.response.send_message(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
            
            # Handle MissingRole: An exception raised when the command invoker lacks a role to run a command.
            elif isinstance(error, app_commands.MissingRole):
                msg_text = 'You need the following role to run this command:'
                await interaction.response.send_message(f'You need the following role to run this command: `{error.missing_role}`', ephemeral=True)
            
            # Handle MissingAnyRole: An exception raised when the command invoker lacks any of the roles specified to run a command.
            elif isinstance(error, app_commands.MissingAnyRole):
                msg_text = 'You need at least one of the following roles to run this command:'
                for role in error.missing_roles:
                    msg_text += f' `{role}`,'
                msg_text = msg_text[:-1]+'.'
                await interaction.response.send_message(msg_text, ephemeral=True)
            
            # For other CheckFailure exceptions, like for example for cutom checks
            else:
                await interaction.response.send_message(f'An unexpected error has occured: {error}', ephemeral=True)
        
        # Handle CommandInvokeError: An exception raised when the command being invoked raised an exception.
        elif isinstance(error, app_commands.CommandInvokeError):
            await interaction.followup.send(f'An unexpected error has occured: {error.original}', ephemeral=True)
        
        # Handle rest of app_commands.AppCommandError exceptions
        else:
            await interaction.response.send_message(f'An unexpected error has occured: {error}', ephemeral=True)


    @app_commands.command(name='setup', description='Create music text channel')
    @app_commands.guild_only()  # Only allow command in guilds, not in private messages
    @app_commands.checks.cooldown(1, 10.0)  # Command can be used once every 10 seconds
    @app_commands.checks.has_permissions(manage_channels=True)  # Member must have MANAGE_CHANNELS
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
        # Prevents the interaction from timing out
        await interaction.response.defer(ephemeral=True)

        # Get guild music data and music text channel id
        guild_music_data = self.get_music_data(interaction.guild.id)
        music_text_channel_id = guild_music_data['music_text_channel_id'] if guild_music_data else None

        # Get music text channel in case it exists in current guild, otherwise None
        music_text_channel = interaction.guild.get_channel(music_text_channel_id)

        # If music text channel exists, inform user
        if music_text_channel is not None:
            await interaction.followup.send(f'Music text channel already exists: {music_text_channel.mention}', ephemeral=True)
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
        music_message = await self.create_music_message(music_text_channel)

        # Add guild music data to music data and save in `music_data.json`
        self.add_music_data(interaction.guild.id, music_text_channel.id, music_message.id) 

        # Infom user music text channel was created
        await interaction.followup.send(f'Music text channel created: {music_text_channel.mention}', ephemeral=True) 


async def setup(bot):
    await bot.add_cog(MusicCog(bot))