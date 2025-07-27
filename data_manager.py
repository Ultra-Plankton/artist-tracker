"""
Data persistence module for Music Updater
Handles saving and loading artist data and bot settings to/from JSON file
"""

import json
import os
from datetime import datetime
import config

class DataManager:
    def __init__(self):
        self.data_file = config.DATA_FILE
        self.settings_file = 'bot_settings.json'
        self.cloud_db = None
        
        # Try to initialize cloud database
        try:
            from cloud_database import get_cloud_database
            self.cloud_db = get_cloud_database()
            if self.cloud_db:
                print("☁️  Cloud database initialized")
        except ImportError:
            print("📁 Cloud database not available, using local storage only")
    
    def save_artists(self, artists):
        """Save artists list to JSON file and cloud storage"""
        # Try cloud storage first
        if self.cloud_db:
            if self.cloud_db.save_artists(artists):
                return True
            else:
                print("⚠️  Cloud save failed, trying local backup...")
        
        # Fallback to local storage
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(artists, f, indent=2, ensure_ascii=False)
            return True
        except PermissionError:
            print(f"⚠️  Cannot write to {self.data_file} (read-only filesystem)")
            print("📌 Artist data will be preserved in memory for this session")
            return False
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            return False
    
    def load_artists(self):
        """Load artists list from cloud storage, environment variable, or JSON file"""
        # Priority 1: Try cloud storage first
        if self.cloud_db:
            cloud_artists = self.cloud_db.load_artists()
            if cloud_artists:
                return cloud_artists
            else:
                print("⚠️  Cloud load failed, trying other sources...")
        
        # Priority 2: Check if we have artists data in environment variable
        env_data = os.getenv('ARTISTS_DATA')
        if env_data:
            try:
                import base64
                # Decode base64 encoded JSON data
                decoded_data = base64.b64decode(env_data).decode('utf-8')
                artists = json.loads(decoded_data)
                print(f"📦 Loaded {len(artists)} artists from environment variable")
                return artists
            except Exception as e:
                print(f"⚠️  Failed to load from environment variable: {e}")
                # Fall through to file loading
        
        # Priority 3: Load from file if no cloud/env data
        if not os.path.exists(self.data_file):
            return []
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                artists = json.load(f)
                print(f"📁 Loaded {len(artists)} artists from file")
                return artists
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return []
    
    def save_bot_settings(self, settings):
        """Save bot settings to JSON file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return True
        except PermissionError:
            print(f"⚠️  Cannot write to {self.settings_file} (read-only filesystem)")
            print("📌 Bot settings will be preserved in memory for this session")
            return False
        except Exception as e:
            print(f"❌ Error saving bot settings: {e}")
            return False
    
    def load_bot_settings(self):
        """Load bot settings from JSON file"""
        if not os.path.exists(self.settings_file):
            return {'notification_channels': []}
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # Ensure notification_channels exists
                if 'notification_channels' not in settings:
                    settings['notification_channels'] = []
                return settings
        except Exception as e:
            print(f"❌ Error loading bot settings: {e}")
            return {'notification_channels': []}
    
    def backup_data(self):
        """Create a backup of the current data"""
        if not os.path.exists(self.data_file):
            return False
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"artists_data_backup_{timestamp}.json"
            
            with open(self.data_file, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            print(f"✅ Data backed up to: {backup_file}")
            return True
        except Exception as e:
            print(f"❌ Error creating backup: {e}")
            return False
