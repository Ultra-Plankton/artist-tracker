"""
Discord Bot integration for Music Updater
Handles Discord notifications and slash commands for artist tracking
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, time
import config
from spotify_api import SpotifyAPI
from data_manager import DataManager
import json

class MusicBot(commands.Bot):
    def __init__(self):
        # Set up bot intents
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(command_prefix='!', intents=intents)
        
        # Initialize components
        self.spotify = SpotifyAPI()
        self.data_manager = DataManager()
        self.notification_channels = []  # Support multiple notification channels
        self.artists = []
        
        # Load existing data
        self.load_data()
        
        # Set up scheduled tasks
        self.setup_tasks()
    
    def load_data(self):
        """Load artist data and bot settings"""
        self.artists = self.data_manager.load_artists()
        
        # Load Discord channel ID from config (optional)
        if config.DISCORD_CHANNEL_ID:
            try:
                channel_id = int(config.DISCORD_CHANNEL_ID)
                self.notification_channels = [channel_id]
            except ValueError:
                print("⚠️  Invalid Discord channel ID in config")
    
    def save_data(self):
        """Save artist data"""
        return self.data_manager.save_artists(self.artists)
    
    def setup_tasks(self):
        """Set up scheduled tasks for checking releases"""
        # Check twice daily: 9 AM and 6 PM
        @tasks.loop(time=[time(9, 0), time(18, 0)])
        async def check_releases_scheduled():
            await self.check_and_notify_releases()
        
        self.check_releases_task = check_releases_scheduled
    
    async def setup_hook(self):
        """Called when bot is starting up"""
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"❌ Failed to sync slash commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        print(f'🤖 {self.user} is online and ready!')
        print(f'📊 Tracking {len(self.artists)} artists')
        
        # Start scheduled tasks
        if not self.check_releases_task.is_running():
            self.check_releases_task.start()
            print('⏰ Scheduled release checks started (9 AM & 6 PM)')
        
        # Send startup message if channels are configured
        if self.notification_channels:
            startup_embed = discord.Embed(
                title="🎵 Music Updater Bot Online!",
                description=f"Now tracking **{len(self.artists)}** artists for new releases.",
                color=0x1DB954  # Spotify green
            )
            startup_embed.add_field(
                name="📅 Schedule", 
                value="Checking for releases twice daily (9 AM & 6 PM)", 
                inline=False
            )
            startup_embed.add_field(
                name="🎯 Commands", 
                value="Use `/music help` to see all commands", 
                inline=False
            )
            
            # Send to all configured notification channels
            for channel_id in self.notification_channels:
                channel = self.get_channel(channel_id)
                # Only send to TextChannel or Thread (not Category, Forum, or Private channels)
                if isinstance(channel, (discord.TextChannel, discord.Thread)):
                    try:
                        await channel.send(embed=startup_embed)
                    except Exception as e:
                        print(f"⚠️  Could not send startup message to channel {channel_id}: {e}")
    
    async def check_and_notify_releases(self):
        """Check for new releases and send notifications"""
        if not self.spotify.is_available():
            print("❌ Spotify API not available - skipping release check")
            return
        
        if not self.notification_channels:
            print("ℹ️  No notification channels configured - releases will only show in slash command responses")
        
        print(f"🔍 Checking releases for {len(self.artists)} artists...")
        new_releases = []
        
        for artist in self.artists:
            if not artist.get('spotify_data'):
                continue  # Skip offline artists
            
            try:
                # Get latest releases by type
                releases_by_type = self.spotify.get_latest_by_type(artist['spotify_data']['id'])
                latest_album = releases_by_type['latest_album']
                latest_single = releases_by_type['latest_single']
                
                # Check for new album
                if latest_album and (not artist.get('latest_album') or 
                    latest_album['release_date'] > artist['latest_album']['release_date']):
                    new_releases.append({
                        'artist': artist['name'],
                        'type': 'album',
                        'release': latest_album,
                        'artist_data': artist
                    })
                    artist['latest_album'] = latest_album
                
                # Check for new single
                if latest_single and (not artist.get('latest_single') or 
                    latest_single['release_date'] > artist['latest_single']['release_date']):
                    new_releases.append({
                        'artist': artist['name'],
                        'type': 'single',
                        'release': latest_single,
                        'artist_data': artist
                    })
                    artist['latest_single'] = latest_single
                
                artist['last_checked'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                
            except Exception as e:
                print(f"❌ Error checking {artist['name']}: {e}")
        
        # Save data if we found new releases
        if new_releases:
            self.save_data()
            
            # Send notifications to all configured channels
            if self.notification_channels:
                for release_info in new_releases:
                    await self.send_release_notifications(release_info)
            
            print(f"✅ Found {len(new_releases)} new releases")
        else:
            print("ℹ️  No new releases found")
    
    async def send_release_notifications(self, release_info):
        """Send a formatted notification for a new release to all notification channels"""
        artist = release_info['artist']
        release = release_info['release']
        release_type = release_info['type']
        artist_data = release_info['artist_data']
        
        # Create rich embed
        title = f"🆕 New {release_type.title()}!"
        description = f"**{artist}** just released a new {release_type}!"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x1DB954,  # Spotify green
            timestamp=datetime.now()
        )
        
        # Add release details
        embed.add_field(name="📀 Title", value=release['name'], inline=True)
        embed.add_field(name="📅 Release Date", value=release['release_date'], inline=True)
        embed.add_field(name="🎵 Tracks", value=str(release['total_tracks']), inline=True)
        
        # Add artist info
        if artist_data.get('spotify_data'):
            spotify_data = artist_data['spotify_data']
            embed.add_field(
                name="🎸 Genres", 
                value=', '.join(spotify_data['genres'][:3]) if spotify_data['genres'] else 'Unknown', 
                inline=True
            )
            embed.add_field(
                name="👥 Followers", 
                value=f"{spotify_data['followers']:,}", 
                inline=True
            )
        
        # Add Spotify link if available
        if release.get('external_urls', {}).get('spotify'):
            embed.add_field(
                name="🔗 Listen on Spotify", 
                value=f"[Open in Spotify]({release['external_urls']['spotify']})", 
                inline=False
            )
        
        # Set thumbnail if available
        if release.get('images') and release['images']:
            embed.set_thumbnail(url=release['images'][0]['url'])
        
        embed.set_footer(text="Music Updater Bot")
        
        # Send to all notification channels
        for channel_id in self.notification_channels:
            channel = self.get_channel(channel_id)
            # Only send to TextChannel or Thread (not Category, Forum, or Private channels)
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"⚠️  Could not send notification to channel {channel_id}: {e}")
                    
    def add_notification_channel(self, channel_id: int):
        """Add a channel to receive automatic notifications"""
        if channel_id not in self.notification_channels:
            self.notification_channels.append(channel_id)
            return True
        return False
    
    def remove_notification_channel(self, channel_id: int):
        """Remove a channel from automatic notifications"""
        if channel_id in self.notification_channels:
            self.notification_channels.remove(channel_id)
            return True
        return False

# Slash Commands - Using a more compatible approach
async def add_artist_command(interaction: discord.Interaction, artist: str):
    """Add an artist to track for new releases"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'artists'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
        
    # Check if artist already exists
    for existing_artist in bot.artists:
        if existing_artist['name'].lower() == artist.lower():
            await interaction.response.send_message(f"⚠️ **{artist}** is already being tracked!", ephemeral=True)
            return
    
    if not bot.spotify.is_available():
        await interaction.response.send_message("❌ Spotify API not available. Cannot add artists.", ephemeral=True)
        return
    
    # Defer the response since Spotify search might take a moment
    await interaction.response.defer()
    
    try:
        spotify_data = bot.spotify.search_artist(artist, interactive=False)
        
        if not spotify_data:
            await interaction.followup.send(f"❌ Could not find **{artist}** on Spotify.")
            return
        
        # Create artist data
        artist_data = {
            'name': spotify_data['name'],
            'genre': spotify_data['genres'][0] if spotify_data['genres'] else None,
            'added_date': datetime.now().strftime("%Y-%m-%d"),
            'spotify_data': spotify_data,
            'last_checked': None,
            'latest_release': None,
            'latest_album': None,
            'latest_single': None
        }
        
        # Get latest releases
        releases_by_type = bot.spotify.get_latest_by_type(spotify_data['id'])
        artist_data['latest_album'] = releases_by_type['latest_album']
        artist_data['latest_single'] = releases_by_type['latest_single']
        
        # Add to list and save
        bot.artists.append(artist_data)
        bot.save_data()
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Artist Added!",
            description=f"Now tracking **{spotify_data['name']}**",
            color=0x1DB954
        )
        
        if spotify_data['genres']:
            embed.add_field(name="🎸 Genres", value=', '.join(spotify_data['genres'][:3]), inline=True)
        embed.add_field(name="👥 Followers", value=f"{spotify_data['followers']:,}", inline=True)
        embed.add_field(name="📊 Popularity", value=f"{spotify_data['popularity']}/100", inline=True)
        
        if artist_data['latest_album']:
            embed.add_field(
                name="💿 Latest Album", 
                value=f"{artist_data['latest_album']['name']} ({artist_data['latest_album']['release_date']})", 
                inline=False
            )
        
        if artist_data['latest_single']:
            embed.add_field(
                name="🎵 Latest Single", 
                value=f"{artist_data['latest_single']['name']} ({artist_data['latest_single']['release_date']})", 
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error adding artist: {str(e)}")

async def list_artists_command(interaction: discord.Interaction):
    """List all tracked artists"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'artists') or not bot.artists:
        await interaction.response.send_message("📭 No artists being tracked yet. Use `/music add` to start!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🎵 Tracked Artists",
        description=f"Currently tracking **{len(bot.artists)}** artists",
        color=0x1DB954
    )
    
    for i, artist in enumerate(bot.artists[:10], 1):  # Limit to 10 for Discord
        value = ""
        if artist.get('spotify_data'):
            followers = artist['spotify_data']['followers']
            value += f"👥 {followers:,} followers\n"
            if artist['spotify_data']['genres']:
                value += f"🎸 {', '.join(artist['spotify_data']['genres'][:2])}\n"
        
        if artist.get('latest_single'):
            value += f"🎵 Latest: {artist['latest_single']['name']} ({artist['latest_single']['release_date']})"
        elif artist.get('latest_album'):
            value += f"💿 Latest: {artist['latest_album']['name']} ({artist['latest_album']['release_date']})"
        
        embed.add_field(
            name=f"{i}. {artist['name']}", 
            value=value or "No recent releases", 
            inline=True
        )
    
    if len(bot.artists) > 10:
        embed.set_footer(text=f"Showing first 10 of {len(bot.artists)} artists")
    
    await interaction.response.send_message(embed=embed)

async def remove_artist_command(interaction: discord.Interaction, artist: str):
    """Remove an artist from tracking"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'artists'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    
    if not bot.artists:
        await interaction.response.send_message("📭 No artists being tracked yet. Use `/music add` to start!", ephemeral=True)
        return
    
    # Find the artist to remove (case-insensitive)
    artist_to_remove = None
    for existing_artist in bot.artists:
        if existing_artist['name'].lower() == artist.lower():
            artist_to_remove = existing_artist
            break
    
    if not artist_to_remove:
        # Show available artists if not found
        available_artists = [a['name'] for a in bot.artists]
        embed = discord.Embed(
            title="❌ Artist Not Found",
            description=f"**{artist}** is not in your tracking list.",
            color=0xff0000
        )
        embed.add_field(
            name="📋 Currently Tracked Artists:",
            value="\n".join([f"• {name}" for name in available_artists[:10]]),
            inline=False
        )
        if len(available_artists) > 10:
            embed.set_footer(text=f"Showing first 10 of {len(available_artists)} artists")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Remove the artist
    bot.artists.remove(artist_to_remove)
    bot.save_data()
    
    # Send confirmation
    embed = discord.Embed(
        title="✅ Artist Removed!",
        description=f"**{artist_to_remove['name']}** has been removed from tracking.",
        color=0x1DB954
    )
    embed.add_field(
        name="📊 Remaining Artists",
        value=f"Now tracking {len(bot.artists)} artists",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

from typing import Optional

async def setup_notifications_command(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    """Set up notifications for the current or specified channel"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'add_notification_channel'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    
    # Use current channel if none specified
    target_channel = channel or interaction.channel

    if target_channel is None or not hasattr(target_channel, "id"):
        await interaction.response.send_message("❌ Could not determine the target channel for notifications.", ephemeral=True)
        return
    
    # Check permissions
    member = getattr(interaction, "user", None)
    has_permission = False
    if hasattr(interaction, "guild") and interaction.guild is not None:
        # Try to get the member object
        if isinstance(interaction.user, discord.Member):
            has_permission = interaction.user.guild_permissions.manage_channels
        else:
            # Try to fetch the member from the guild
            member = interaction.guild.get_member(interaction.user.id)
            if member and hasattr(member, "guild_permissions"):
                has_permission = member.guild_permissions.manage_channels

    if not has_permission:
        await interaction.response.send_message("❌ You need 'Manage Channels' permission to set up notifications.", ephemeral=True)
        return
    
    if bot.add_notification_channel(target_channel.id):
        embed = discord.Embed(
            title="✅ Notifications Enabled!",
            description=f"This channel will now receive automatic release notifications.",
            color=0x1DB954
        )
        embed.add_field(name="📅 Schedule", value="Twice daily at 9 AM & 6 PM", inline=True)
        channel_display = getattr(target_channel, "mention", None) or getattr(target_channel, "name", None) or f"ID: {target_channel.id}"
        embed.add_field(name="📋 Channel", value=channel_display, inline=True)
        await interaction.response.send_message(embed=embed)
    else:
        channel_display = getattr(target_channel, "mention", None) or getattr(target_channel, "name", None) or f"ID: {target_channel.id}"
        await interaction.response.send_message(f"⚠️ {channel_display} is already receiving notifications.", ephemeral=True)

from typing import Optional

async def remove_notifications_command(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    """Remove notifications from the current or specified channel"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'remove_notification_channel'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    
    # Use current channel if none specified
    target_channel = channel or interaction.channel

    if target_channel is None or not hasattr(target_channel, "id"):
        await interaction.response.send_message("❌ Could not determine the target channel for notifications.", ephemeral=True)
        return
    
    # Check permissions
    has_permission = False
    member = getattr(interaction, "user", None)
    if hasattr(interaction, "guild") and interaction.guild is not None:
        # Try to get the member object
        if isinstance(interaction.user, discord.Member):
            has_permission = interaction.user.guild_permissions.manage_channels
        else:
            # Try to fetch the member from the guild
            member = interaction.guild.get_member(interaction.user.id)
            if member and hasattr(member, "guild_permissions"):
                has_permission = member.guild_permissions.manage_channels

    if not has_permission:
        await interaction.response.send_message("❌ You need 'Manage Channels' permission to manage notifications.", ephemeral=True)
        return

    if bot.remove_notification_channel(target_channel.id):
        await interaction.response.send_message(f"✅ Notifications disabled for {getattr(target_channel, 'mention', getattr(target_channel, 'name', f'ID: {target_channel.id}'))}.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ {getattr(target_channel, 'mention', getattr(target_channel, 'name', f'ID: {target_channel.id}'))} wasn't receiving notifications.", ephemeral=True)

async def check_releases_command(interaction: discord.Interaction):
    """Manually check for new releases"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'check_and_notify_releases'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    
    # Defer response since this might take a moment
    await interaction.response.defer()
    
    try:
        await bot.check_and_notify_releases()
        await interaction.followup.send("✅ Release check completed! Any new releases have been posted to notification channels.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error checking releases: {str(e)}")

async def stats_command(interaction: discord.Interaction):
    """Show bot statistics"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'artists'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📊 Music Updater Bot Stats",
        color=0x1DB954
    )
    
    embed.add_field(name="🎵 Tracked Artists", value=str(len(bot.artists)), inline=True)
    embed.add_field(name="🔔 Notification Channels", value=str(len(bot.notification_channels)), inline=True)
    embed.add_field(name="🏠 Servers", value=str(len(bot.guilds)), inline=True)
    
    # Add some artist stats
    if bot.artists:
        with_spotify = sum(1 for a in bot.artists if a.get('spotify_data'))
        embed.add_field(name="🎧 Spotify Connected", value=f"{with_spotify}/{len(bot.artists)}", inline=True)
        
        recent_albums = sum(1 for a in bot.artists if a.get('latest_album'))
        recent_singles = sum(1 for a in bot.artists if a.get('latest_single'))
        embed.add_field(name="💿 Albums Tracked", value=str(recent_albums), inline=True)
        embed.add_field(name="🎵 Singles Tracked", value=str(recent_singles), inline=True)
    
    embed.set_footer(text="Next automatic check: 9 AM or 6 PM (whichever comes first)")
    await interaction.response.send_message(embed=embed)

async def help_command(interaction: discord.Interaction):
    """Show all available commands"""
    embed = discord.Embed(
        title="🎵 Music Updater Bot Commands",
        description="Manage your artist tracking and get release notifications!\n\n**All commands work in any channel where you can use slash commands.**",
        color=0x1DB954
    )
    
    commands_list = [
        ("📝 `/music add <artist>`", "Add an artist to track"),
        ("📋 `/music list`", "Show all tracked artists"),
        ("🗑️ `/music remove <artist>`", "Remove an artist from tracking"),
        ("🔍 `/music check`", "Check for new releases now"),
        ("📊 `/music stats`", "Show bot statistics"),
        ("🔔 `/music setup [channel]`", "Enable notifications (Admin only)"),
        ("🔕 `/music unsetup [channel]`", "Disable notifications (Admin only)"),
        ("❓ `/music help`", "Show this help message")
    ]
    
    for command, description in commands_list:
        embed.add_field(name=command, value=description, inline=False)
    
    embed.add_field(
        name="📢 About Notifications",
        value="• Use `/music setup` to enable automatic notifications in a channel\n• Notifications run twice daily at 9 AM & 6 PM\n• Commands work in any channel, notifications go to configured channels",
        inline=False
    )
    embed.set_footer(text="🔔 Bot works globally - no need to be in a specific channel!")
    await interaction.response.send_message(embed=embed)

# Music command group
class MusicGroup(app_commands.Group):
    """Music tracking commands"""
    
    def __init__(self):
        super().__init__(name='music', description='Track artists and get release notifications')
    
    @app_commands.command(name='add', description='Add an artist to track')
    @app_commands.describe(artist="The name of the artist to add")
    async def add(self, interaction: discord.Interaction, artist: str):
        await add_artist_command(interaction, artist)
    
    @app_commands.command(name='list', description='List all tracked artists')
    async def list(self, interaction: discord.Interaction):
        await list_artists_command(interaction)
    
    @app_commands.command(name='remove', description='Remove an artist from tracking')
    @app_commands.describe(artist="The name of the artist to remove")
    async def remove(self, interaction: discord.Interaction, artist: str):
        await remove_artist_command(interaction, artist)
    
    @app_commands.command(name='help', description='Show all commands')
    async def help(self, interaction: discord.Interaction):
        await help_command(interaction)
    
    @app_commands.command(name='setup', description='Enable notifications in current/specified channel')
    @app_commands.describe(channel="Channel to receive notifications (defaults to current channel)")
    async def setup(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        await setup_notifications_command(interaction, channel)
    
    @app_commands.command(name='unsetup', description='Disable notifications in current/specified channel')
    @app_commands.describe(channel="Channel to stop receiving notifications (defaults to current channel)")
    async def unsetup(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        await remove_notifications_command(interaction, channel)
    
    @app_commands.command(name='check', description='Check for new releases now')
    async def check(self, interaction: discord.Interaction):
        await check_releases_command(interaction)
    
    @app_commands.command(name='stats', description='Show bot statistics')
    async def stats(self, interaction: discord.Interaction):
        await stats_command(interaction)

# Initialize and run bot
async def run_discord_bot():
    """Initialize and run the Discord bot"""
    if not config.DISCORD_TOKEN:
        print("❌ Discord token not configured. Please add DISCORD_TOKEN to your .env file.")
        return
    
    bot = MusicBot()
    
    # Add the music command group
    bot.tree.add_command(MusicGroup())
    
    try:
        await bot.start(config.DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Error starting Discord bot: {e}")

if __name__ == "__main__":
    # Run the bot
    asyncio.run(run_discord_bot())
