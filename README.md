# Music Updater Bot 🎵

A Discord bot that tracks your favorite artists and sends notifications when they release new music via Spotify API integration with YouTube Music links.

## Features

- 🎵 **Track Multiple Artists** - Add/remove artists from your watchlist
- 🔔 **Automatic Notifications** - Get notified of new releases twice daily (9 AM & 6 PM)
- 🎯 **Smart Search** - Intelligent artist matching with exact name prioritization
- 📊 **Rich Information** - See follower counts, genres, popularity, and release details
- 🎧 **Spotify Integration** - Direct links to listen on Spotify
- 📺 **YouTube Music Integration** - Links to music videos on YouTube
- ⚙️ **Flexible Notifications** - Configure which channels receive notifications
- 🎪 **Discord Slash Commands** - Modern Discord command interface

## Discord Commands

- `/music add <artist>` - Add an artist to track
- `/music list` - Show all tracked artists
- `/music remove <artist>` - Remove an artist from tracking
- `/music check` - Manually check for new releases
- `/music stats` - Show bot statistics
- `/music setup [channel]` - Enable notifications (Admin only)
- `/music unsetup [channel]` - Disable notifications (Admin only)
- `/music help` - Show all commands

## Getting Started

### Prerequisites
- Python 3.8 or higher
- Spotify Developer Account (for Spotify API)
- Google Developer Account (for YouTube Data API)
- Discord Bot Token

### Setup

1. **Clone and Install Dependencies**:
   ```bash
   pip install spotipy python-dotenv requests
   ```

2. **Spotify API Setup (Optional but Recommended)**:
   - Go to https://developer.spotify.com/dashboard
   - Create a new app
   - Copy the Client ID and Client Secret
   - Copy `.env.template` to `.env` and fill in your credentials:
     ```
     SPOTIFY_CLIENT_ID=your_client_id_here
     SPOTIFY_CLIENT_SECRET=your_client_secret_here
     ```

3. **Run the Application**:
   ```bash
   python main.py
   ```

### Usage

#### **Command Line Interface**
```bash
python main.py
```

The application provides an enhanced menu interface:
1. **Add artist** - Search and add artists with Spotify data
2. **List artists** - View all tracked artists with release info
3. **Remove artist** - Remove an artist from tracking  
4. **Check for new releases** - Find new releases from all artists
5. **Show artist details** - Detailed view of any artist
6. **Exit** - Close the application

#### **Discord Bot Interface**
```bash
python discord_bot.py
```

**Getting Started with Discord Bot:**
1. **Deploy the bot** with just Spotify credentials and Discord token
2. **Invite the bot** to your Discord server
3. **Use `/music setup`** in any channel to enable notifications for that channel
4. **Start adding artists** with `/music add <artist>`

**Key Features:**
- 🔔 **Flexible Notifications** - Use `/music setup` to enable notifications in any channel
- 📢 **Rich Embeds** with album art and Spotify links  
- 🎯 **Smart Tracking** (separates albums from singles)
- ⏰ **Automatic Checks** twice daily (9 AM & 6 PM)

> **See [DISCORD_SETUP.md](DISCORD_SETUP.md) for complete Discord bot setup instructions**

## Features in Detail

### With Spotify API:
- 🔍 **Artist Search**: Finds artists on Spotify with official names
- 📊 **Rich Data**: Follower counts, popularity, genres
- 🆕 **Latest Releases**: Automatically tracks newest albums/singles
- 🔄 **Release Monitoring**: Check all artists for new content

### Without Spotify API:
- 📝 **Offline Mode**: Still tracks artists manually
- 💾 **Data Persistence**: Saves your list locally

## Project Structure

```
Music Updater Project/
├── main.py              # Main application with enhanced features
├── spotify_api.py       # Spotify API integration
├── data_manager.py      # Data persistence (JSON)
├── config.py            # Configuration settings
├── requirements.txt     # Python dependencies
├── .env.template        # Environment variables template
├── archive/             # Archived experimental scripts & docs
└── README.md           # This file
```

### Archived tools

Some experimental or one-off helper scripts were moved to the `archive/` folder to keep the repository root cleaner. See `ARCHIVE.md` for details about what was moved and why.


## Example Output

```
🎵 Music Updater - Artist Tracker 🎵
📁 Loaded 3 saved artists

🔍 Searching for 'Billie Eilish' on Spotify...
✅ Found on Spotify: Billie Eilish
   🎵 Genres: pop, electropop, indie pop
   👥 Followers: 106,823,245
   🆕 Latest: HIT ME HARD AND SOFT (2024-05-17)
✅ Added artist: Billie Eilish
```

## Contributing

This project is designed to grow step by step. Next planned features:
1. ✅ Spotify API integration (current)
2. ✅ Discord bot notifications (current)
3. 🔄 Web interface
4. 🔄 Database storage
5. 🔄 Advanced filtering and search

## Deployment

### Render Deployment (Recommended for 24/7 hosting)

1. **Fork this repository** to your GitHub account

2. **Create a new Web Service** on [Render](https://render.com)
   - Connect your GitHub repository
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `python3 discord_bot.py`
   - Environment: `Python 3`

3. **Configure environment variables** in Render:
   ```
   DISCORD_BOT_TOKEN=your_discord_bot_token
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   YOUTUBE_API_KEY=your_youtube_api_key
   ```

4. **Deploy** - Render will automatically deploy from your main branch

The bot includes a built-in health check server for 24/7 uptime on Render's free tier.

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/artist-tracker.git
   cd artist-tracker
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment** - Copy `.env.template` to `.env` and add your tokens

4. **Run the Discord bot**
   ```bash
   python discord_bot.py
   ```

5. **Run the CLI app** (optional)
   ```bash
   python cli_app.py
   ```
