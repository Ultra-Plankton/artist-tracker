# Music Updater Configuration
# This file will store configuration for Spotify API and Discord bot integration

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Spotify API Configuration
# To get these credentials:
# 1. Go to https://developer.spotify.com/dashboard
# 2. Create an app
# 3. Copy Client ID and Client Secret
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', '')

# Discord Bot Configuration (to be filled in later)
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
DISCORD_CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID', '')

# General Settings
MAX_ARTISTS = 100
UPDATE_INTERVAL_HOURS = 24
DATA_FILE = 'artists_data.json'

# Spotify API Settings
SPOTIFY_MARKET = 'US'  # Market for release availability
MAX_RELEASES_PER_ARTIST = 10
