"""
Configuration settings for Music Updater
Handles environment variables and global settings
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Spotify API settings
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
SPOTIFY_MARKET = os.environ.get('SPOTIFY_MARKET', 'US')

# Discord Bot settings
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN', '')
DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID', '')
DISCORD_GUILD_ID = os.environ.get('DISCORD_GUILD_ID', '')
DISCORD_CHANNEL_ID = os.environ.get('DISCORD_CHANNEL_ID', '')
CHECK_INTERVAL_HOURS = int(os.environ.get('CHECK_INTERVAL_HOURS', '12'))

# YouTube API settings
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')

# Data storage
DATA_FILE = os.environ.get('DATA_FILE', 'artists_data.json')

# Cloud database settings
CLOUD_DB_URL = os.environ.get('CLOUD_DB_URL', '')
CLOUD_DB_PASSWORD = os.environ.get('CLOUD_DB_PASSWORD', '')
