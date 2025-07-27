"""
Discord Bot integration for Music Updater
Handles Discord notifications and slash commands for artist tracking
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, time, timedelta
import config
from spotify_api import SpotifyAPI
from data_manager import DataManager
import json
import math

# Pagination Views
class ReleasePaginationView(discord.ui.View):
    """Pagination view for release notifications"""
    
    def __init__(self, albums, singles, *, timeout=300):
        super().__init__(timeout=timeout)
        self.albums = albums
        self.singles = singles
        self.current_page = 0
        
        # Use adaptive page size based on number of releases
        # More releases = smaller pages to prevent character limit issues
        total_releases = len(albums) + len(singles)
        if total_releases > 30:
            self.page_size = 5  # Small pages for many releases
        elif total_releases > 15:
            self.page_size = 7  # Medium pages
        else:
            self.page_size = 10  # Normal pages for few releases
        
        # Calculate pages
        all_releases = albums + singles
        self.total_pages = math.ceil(len(all_releases) / self.page_size) if all_releases else 1
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    def create_embed(self):
        """Create embed for current page"""
        all_releases = self.albums + self.singles
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        page_releases = all_releases[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"🆕 {len(all_releases)} New Release{'s' if len(all_releases) != 1 else ''}!",
            description=f"Page {self.current_page + 1} of {self.total_pages}",
            color=0x1DB954,
            timestamp=datetime.now()
        )
        
        # Group page releases by type
        page_albums = [r for r in page_releases if r['type'] == 'album']
        page_singles = [r for r in page_releases if r['type'] == 'single']
        
        # Helper function to create release line with smart truncation
        def create_release_line(release_info, max_length=80):
            artist = release_info['artist']
            release = release_info['release']
            spotify_link = release.get('external_urls', {}).get('spotify', '')
            
            # Smart truncation based on available space
            artist_name = artist[:25] + "..." if len(artist) > 25 else artist
            
            # Calculate remaining space for release name
            base_length = len(f"• **{artist_name}** - [] ({release['release_date']})")
            remaining_space = max_length - base_length
            release_name = release['name'][:max(10, remaining_space-5)] + "..." if len(release['name']) > remaining_space else release['name']
            
            if spotify_link:
                return f"• **{artist_name}** - [{release_name}]({spotify_link}) ({release['release_date']})"
            else:
                return f"• **{artist_name}** - {release_name} ({release['release_date']})"
        
        # Add albums for this page with character limit checking
        if page_albums:
            album_lines = []
            current_length = 0
            max_field_length = 900  # Safe limit under 1024
            
            for album in page_albums:
                line = create_release_line(album)
                # Check if adding this line would exceed the limit
                if current_length + len(line) + 1 > max_field_length:
                    remaining = len(page_albums) - len(album_lines)
                    if remaining > 0:
                        album_lines.append(f"*...and {remaining} more albums on this page*")
                    break
                album_lines.append(line)
                current_length += len(line) + 1
            
            embed.add_field(
                name=f"💿 Albums on this page ({len(page_albums)})",
                value='\n'.join(album_lines),
                inline=False
            )
        
        # Add singles for this page with character limit checking
        if page_singles:
            single_lines = []
            current_length = 0
            max_field_length = 900  # Safe limit under 1024
            
            for single in page_singles:
                line = create_release_line(single)
                # Check if adding this line would exceed the limit
                if current_length + len(line) + 1 > max_field_length:
                    remaining = len(page_singles) - len(single_lines)
                    if remaining > 0:
                        single_lines.append(f"*...and {remaining} more singles on this page*")
                    break
                single_lines.append(line)
                current_length += len(line) + 1
            
            embed.add_field(
                name=f"🎵 Singles on this page ({len(page_singles)})",
                value='\n'.join(single_lines),
                inline=False
            )
        
        # Add summary (keep this short)
        embed.add_field(
            name="📊 Total Summary",
            value=f"Albums: {len(self.albums)} • Singles: {len(self.singles)}",
            inline=True
        )
        
        embed.set_footer(text="Music Updater Bot")
        return embed
    
    @discord.ui.button(label='◀️ Previous', style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label='▶️ Next', style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

class ArtistPaginationView(discord.ui.View):
    """Pagination view for artist list"""
    
    def __init__(self, artists, *, timeout=300):
        super().__init__(timeout=timeout)
        self.artists = artists
        self.current_page = 0
        
        # Calculate pages (10 artists per page)
        self.total_pages = math.ceil(len(artists) / 10) if artists else 1
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    def create_embed(self):
        """Create embed for current page"""
        start_idx = self.current_page * 10
        end_idx = start_idx + 10
        page_artists = self.artists[start_idx:end_idx]
        
        embed = discord.Embed(
            title="🎵 Tracked Artists",
            description=f"Page {self.current_page + 1} of {self.total_pages} • Total: **{len(self.artists)}** artists",
            color=0x1DB954
        )
        
        for i, artist in enumerate(page_artists, 1):
            global_index = start_idx + i
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
                name=f"{global_index}. {artist['name']}", 
                value=value or "No recent releases", 
                inline=True
            )
        
        embed.set_footer(text=f"Use /music add to add more artists • Page {self.current_page + 1}/{self.total_pages}")
        return embed
    
    @discord.ui.button(label='◀️ Previous', style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label='▶️ Next', style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

class MusicBot(commands.Bot):
    def __init__(self):
        # Set up bot intents - only use basic intents to avoid privileged intent requirements
        intents = discord.Intents.default()
        intents.message_content = False  # We don't need message content for slash commands
        
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
        
        # Load bot settings (notification channels, etc.)
        bot_settings = self.data_manager.load_bot_settings()
        self.notification_channels = bot_settings.get('notification_channels', [])
        
        # Also load Discord channel ID from config if available (for backwards compatibility)
        if config.DISCORD_CHANNEL_ID and not self.notification_channels:
            try:
                channel_id = int(config.DISCORD_CHANNEL_ID)
                self.notification_channels = [channel_id]
                # Save this to persistent settings
                self.save_bot_settings()
            except ValueError:
                print("⚠️  Invalid Discord channel ID in config")
        
        print(f"📋 Loaded {len(self.notification_channels)} notification channels")
    
    def save_data(self):
        """Save artist data"""
        return self.data_manager.save_artists(self.artists)
    
    def save_bot_settings(self):
        """Save bot settings (notification channels, etc.)"""
        settings = {
            'notification_channels': self.notification_channels,
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return self.data_manager.save_bot_settings(settings)
    
    async def close(self):
        """Properly close the bot and cleanup resources"""
        # Stop scheduled tasks
        if hasattr(self, 'check_releases_task') and self.check_releases_task.is_running():
            self.check_releases_task.cancel()
        
        if hasattr(self, 'weekly_summary_task') and self.weekly_summary_task.is_running():
            self.weekly_summary_task.cancel()
        
        # Close the bot connection
        await super().close()
    
    def setup_tasks(self):
        """Set up scheduled tasks for checking releases"""
        # Check twice daily: 9 AM and 6 PM (production)
        @tasks.loop(time=[time(9, 0), time(18, 0)])
        async def check_releases_scheduled():
            await self.check_and_notify_releases()
        
        # Test mode: Check every 2 minutes for testing notifications
        @tasks.loop(minutes=2)
        async def check_releases_test():
            print("🧪 TEST MODE: Running release check...")
            await self.check_and_notify_releases()
        
        # Weekly summary: Every Friday at midnight
        @tasks.loop(time=time(0, 0))  # Midnight
        async def weekly_summary_task():
            # Only run on Fridays (weekday 4)
            if datetime.now().weekday() == 4:  # Friday
                print("📅 Running weekly summary for Friday...")
                await self.send_weekly_summary()
        
        # Use production mode (twice daily checks)
        self.check_releases_task = check_releases_scheduled
        self.weekly_summary_task = weekly_summary_task
    
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
            print('🔄 PRODUCTION MODE: Release checks twice daily (9 AM & 6 PM)')
        
        if not self.weekly_summary_task.is_running():
            self.weekly_summary_task.start()
            print('📅 Weekly summary task started (Fridays at midnight)')
        
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
                name="🗓️ Weekly Summary", 
                value="Every Friday at midnight - weekly release roundup", 
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
                
                # PRODUCTION MODE: Check for actual new releases
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
            
            # Send consolidated notification to all configured channels
            if self.notification_channels:
                await self.send_consolidated_release_notifications(new_releases)
            
            print(f"✅ Found {len(new_releases)} new releases")
        else:
            print("ℹ️  No new releases found")
    
    async def send_consolidated_release_notifications(self, new_releases):
        """Send a paginated consolidated notification for all new releases"""
        if not new_releases:
            return
        
        # Group releases by type for better organization
        albums = [r for r in new_releases if r['type'] == 'album']
        singles = [r for r in new_releases if r['type'] == 'single']
        
        # Send to all notification channels
        for channel_id in self.notification_channels:
            channel = self.get_channel(channel_id)
            # Only send to TextChannel or Thread (not Category, Forum, or Private channels)
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    # Create pagination view
                    view = ReleasePaginationView(albums, singles)
                    embed = view.create_embed()
                    
                    # Only show pagination buttons if there are multiple pages
                    if view.total_pages > 1:
                        await channel.send(embed=embed, view=view)
                    else:
                        await channel.send(embed=embed)
                        
                except Exception as e:
                    print(f"⚠️  Could not send notification to channel {channel_id}: {e}")
                    
                    # If it still fails, send a simplified message
                    try:
                        simple_embed = discord.Embed(
                            title=f"🆕 {len(new_releases)} New Releases!",
                            description=f"Found {len(albums)} albums and {len(singles)} singles from your tracked artists.\n\nUse `/music list` to see details.",
                            color=0x1DB954,
                            timestamp=datetime.now()
                        )
                        simple_embed.set_footer(text="Music Updater Bot")
                        await channel.send(embed=simple_embed)
                        print(f"✅ Sent simplified notification to channel {channel_id}")
                    except Exception as e2:
                        print(f"❌ Failed to send even simplified notification to channel {channel_id}: {e2}")

    async def send_weekly_summary(self):
        """Send a weekly summary of all releases from the past week"""
        if not self.spotify.is_available():
            print("❌ Spotify API not available - skipping weekly summary")
            return
        
        if not self.notification_channels:
            print("ℹ️  No notification channels configured - skipping weekly summary")
            return
        
        print("📅 Generating weekly summary...")
        
        # Calculate date range for the past week (Monday to Sunday)
        today = datetime.now()
        # Get last Monday (start of this week)
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday)
        # Get the previous Monday (start of last week)
        week_start = last_monday - timedelta(days=7)
        week_end = last_monday - timedelta(days=1)  # Last Sunday
        
        week_start_str = week_start.strftime("%Y-%m-%d")
        week_end_str = week_end.strftime("%Y-%m-%d")
        
        print(f"📅 Collecting releases from {week_start_str} to {week_end_str}")
        
        weekly_releases = []
        
        for artist in self.artists:
            if not artist.get('spotify_data'):
                continue  # Skip offline artists
            
            try:
                # Get all albums and singles for this artist
                releases_by_type = self.spotify.get_latest_by_type(artist['spotify_data']['id'])
                
                # Check albums released this week
                if releases_by_type['latest_album']:
                    album_date = releases_by_type['latest_album']['release_date']
                    if week_start_str <= album_date <= week_end_str:
                        weekly_releases.append({
                            'artist': artist['name'],
                            'type': 'album',
                            'release': releases_by_type['latest_album'],
                            'artist_data': artist
                        })
                
                # Check singles released this week
                if releases_by_type['latest_single']:
                    single_date = releases_by_type['latest_single']['release_date']
                    if week_start_str <= single_date <= week_end_str:
                        weekly_releases.append({
                            'artist': artist['name'],
                            'type': 'single',
                            'release': releases_by_type['latest_single'],
                            'artist_data': artist
                        })
                        
            except Exception as e:
                print(f"❌ Error checking weekly releases for {artist['name']}: {e}")
        
        # Send weekly summary to all notification channels
        if weekly_releases:
            await self.send_weekly_summary_notifications(weekly_releases, week_start, week_end)
            print(f"✅ Weekly summary sent: {len(weekly_releases)} releases")
        else:
            # Send a "no releases" summary
            await self.send_no_releases_summary(week_start, week_end)
            print("ℹ️  Weekly summary sent: no new releases")

    async def send_weekly_summary_notifications(self, weekly_releases, week_start, week_end):
        """Send formatted weekly summary notifications"""
        # Group releases by type
        albums = [r for r in weekly_releases if r['type'] == 'album']
        singles = [r for r in weekly_releases if r['type'] == 'single']
        
        # Create custom pagination view for weekly summary
        class WeeklySummaryView(ReleasePaginationView):
            def create_embed(self):
                # Use the parent method but customize the title and description
                embed = super().create_embed()
                
                week_start_formatted = week_start.strftime("%B %d")
                week_end_formatted = week_end.strftime("%B %d, %Y")
                
                embed.title = f"🗓️ Weekly Release Summary"
                embed.description = f"**{week_start_formatted} - {week_end_formatted}**\nPage {self.current_page + 1} of {self.total_pages}"
                embed.color = 0x9932CC  # Purple for weekly summaries
                
                # Update footer
                embed.set_footer(text="Music Updater Bot • Weekly Summary")
                return embed
        
        # Send to all notification channels
        for channel_id in self.notification_channels:
            channel = self.get_channel(channel_id)
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    # Create weekly pagination view
                    view = WeeklySummaryView(albums, singles)
                    embed = view.create_embed()
                    
                    # Only show pagination buttons if there are multiple pages
                    if view.total_pages > 1:
                        await channel.send(embed=embed, view=view)
                    else:
                        await channel.send(embed=embed)
                        
                except Exception as e:
                    print(f"⚠️  Could not send weekly summary to channel {channel_id}: {e}")

    async def send_no_releases_summary(self, week_start, week_end):
        """Send a summary when no releases were found for the week"""
        week_start_formatted = week_start.strftime("%B %d")
        week_end_formatted = week_end.strftime("%B %d, %Y")
        
        embed = discord.Embed(
            title="🗓️ Weekly Release Summary",
            description=f"**{week_start_formatted} - {week_end_formatted}**\n\nNo new releases from your tracked artists this week.",
            color=0x9932CC,  # Purple for weekly summaries
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📊 Current Stats",
            value=f"Tracking {len(self.artists)} artists across all genres",
            inline=False
        )
        
        embed.add_field(
            name="🎯 What's Next?",
            value="New releases will be posted as they come out!\nUse `/music add` to track more artists.",
            inline=False
        )
        
        embed.set_footer(text="Music Updater Bot • Weekly Summary")
        
        # Send to all notification channels
        for channel_id in self.notification_channels:
            channel = self.get_channel(channel_id)
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"⚠️  Could not send weekly summary to channel {channel_id}: {e}")

    async def send_release_notifications(self, release_info):
        """Send a formatted notification for a new release to all notification channels"""
        # This method is kept for backwards compatibility but not used in the new flow
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
            self.save_bot_settings()  # Persist the change
            print(f"✅ Added notification channel: {channel_id}")
            return True
        return False
    
    def remove_notification_channel(self, channel_id: int):
        """Remove a channel from automatic notifications"""
        if channel_id in self.notification_channels:
            self.notification_channels.remove(channel_id)
            self.save_bot_settings()  # Persist the change
            print(f"✅ Removed notification channel: {channel_id}")
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
    """List all tracked artists with pagination"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'artists') or not bot.artists:
        await interaction.response.send_message("📭 No artists being tracked yet. Use `/music add` to start!", ephemeral=True)
        return
    
    # Create pagination view
    view = ArtistPaginationView(bot.artists)
    embed = view.create_embed()
    
    # Only show pagination buttons if there are multiple pages
    if view.total_pages > 1:
        await interaction.response.send_message(embed=embed, view=view)
    else:
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
        # Store original notification channels
        original_channels = bot.notification_channels.copy()
        
        # Temporarily add the current channel for manual check results
        if interaction.channel and hasattr(interaction.channel, 'id'):
            current_channel_id = interaction.channel.id
            if current_channel_id not in bot.notification_channels:
                bot.notification_channels.append(current_channel_id)
        
        # Run the release check
        await bot.check_and_notify_releases()
        
        # Restore original notification channels
        bot.notification_channels = original_channels
        
        await interaction.followup.send("✅ Release check completed! Results shown below.")
        
    except Exception as e:
        # Restore original notification channels in case of error
        bot.notification_channels = original_channels
        await interaction.followup.send(f"❌ Error checking releases: {str(e)}")

async def weekly_summary_command(interaction: discord.Interaction):
    """Generate a manual weekly summary"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'send_weekly_summary'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    
    # Defer response since this might take a moment
    await interaction.response.defer()
    
    try:
        # Store original notification channels
        original_channels = bot.notification_channels.copy()
        
        # Temporarily add the current channel for manual summary results
        if interaction.channel and hasattr(interaction.channel, 'id'):
            current_channel_id = interaction.channel.id
            if current_channel_id not in bot.notification_channels:
                bot.notification_channels.append(current_channel_id)
        
        # Run the weekly summary
        await bot.send_weekly_summary()
        
        # Restore original notification channels
        bot.notification_channels = original_channels
        
        await interaction.followup.send("✅ Weekly summary completed! Results shown above.")
        
    except Exception as e:
        # Restore original notification channels in case of error
        bot.notification_channels = original_channels
        await interaction.followup.send(f"❌ Error generating weekly summary: {str(e)}")

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
        ("�️ `/music weekly`", "Generate weekly release summary"),
        ("�📊 `/music stats`", "Show bot statistics"),
        ("🔔 `/music setup [channel]`", "Enable notifications (Admin only)"),
        ("🔕 `/music unsetup [channel]`", "Disable notifications (Admin only)"),
        ("❓ `/music help`", "Show this help message")
    ]
    
    for command, description in commands_list:
        embed.add_field(name=command, value=description, inline=False)
    
    embed.add_field(
        name="📢 About Notifications",
        value="• Use `/music setup` to enable automatic notifications in a channel\n• Notifications run twice daily at 9 AM & 6 PM\n• Weekly summaries every Friday at midnight\n• Commands work in any channel, notifications go to configured channels",
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
    
    @app_commands.command(name='weekly', description='Generate weekly release summary')
    async def weekly(self, interaction: discord.Interaction):
        await weekly_summary_command(interaction)
    
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
    except KeyboardInterrupt:
        print("\n🛑 Bot shutdown requested...")
    except Exception as e:
        print(f"❌ Error starting Discord bot: {e}")
    finally:
        # Ensure proper cleanup
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    # Run the bot with proper event loop handling
    try:
        asyncio.run(run_discord_bot())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            print("✅ Bot stopped cleanly")
        else:
            raise
