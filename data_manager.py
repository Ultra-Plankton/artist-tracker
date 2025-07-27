"""
Data persistence module for Music Updater (Async Version)
Handles saving and loading artist data and bot settings to/from JSON file
"""

import json
import os
from datetime import datetime
import config
import asyncio

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
    
    async def save_artists(self, artists):
        """Save artists list to cloud storage and JSON file"""
        # Try cloud storage first
        if self.cloud_db:
            if await self.cloud_db.save_artists(artists):
                return True
            else:
                print("⚠️  Cloud save failed, trying local backup...")
        
        # Fallback to local storage
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_to_file, self.data_file, artists)
        return True

    async def load_artists(self):
        """Load artists list from cloud, environment, or file"""
        # Priority 1: Try cloud storage first
        if self.cloud_db:
            cloud_artists = await self.cloud_db.load_artists()
            if cloud_artists:
                if isinstance(cloud_artists, list):
                    return cloud_artists
                elif isinstance(cloud_artists, dict):
                    # If dict, try to extract a list if possible
                    if 'artists' in cloud_artists and isinstance(cloud_artists['artists'], list):
                        return cloud_artists['artists']
                    else:
                        print("⚠️  Cloud returned dict, not list. Returning empty list.")
                        return []
                else:
                    print("⚠️  Cloud returned unknown type. Returning empty list.")
                    return []
            else:
                print("⚠️  Cloud load failed, trying other sources...")
        
        # Priority 2: Check environment variable
        env_data = os.getenv('ARTISTS_DATA')
        if env_data:
            try:
                import base64
                decoded_data = base64.b64decode(env_data).decode('utf-8')
                artists = json.loads(decoded_data)
                if isinstance(artists, list):
                    print(f"📦 Loaded {len(artists)} artists from environment variable")
                    return artists
                elif isinstance(artists, dict):
                    if 'artists' in artists and isinstance(artists['artists'], list):
                        print(f"📦 Loaded {len(artists['artists'])} artists from environment variable (dict)")
                        return artists['artists']
                    else:
                        print("⚠️  Env var returned dict, not list. Returning empty list.")
                        return []
                else:
                    print("⚠️  Env var returned unknown type. Returning empty list.")
                    return []
            except Exception as e:
                print(f"⚠️  Failed to load from environment variable: {e}")
        
        # Priority 3: Load from file
        if os.path.exists(self.data_file):
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._load_from_file, self.data_file)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                if 'artists' in data and isinstance(data['artists'], list):
                    return data['artists']
                else:
                    print("⚠️  File returned dict, not list. Returning empty list.")
                    return []
            else:
                print("⚠️  File returned unknown type. Returning empty list.")
                return []
        
        return []

    async def save_bot_settings(self, settings):
        """Save bot settings to cloud storage and JSON file"""
        if self.cloud_db:
            if await self.cloud_db.save_bot_settings(settings):
                return True
            else:
                print("⚠️  Cloud settings save failed, trying local backup...")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_to_file, self.settings_file, settings)
        return True

    async def load_bot_settings(self):
        """Load bot settings from cloud storage or JSON file"""
        if self.cloud_db:
            cloud_settings = await self.cloud_db.load_bot_settings()
            # Check for non-empty, valid settings
            if cloud_settings and (cloud_settings.get('notification_channels') or len(cloud_settings) > 1):
                return cloud_settings
            else:
                print("⚠️  Cloud settings empty or invalid, trying local file...")

        if os.path.exists(self.settings_file):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._load_from_file, self.settings_file)

        return {'notification_channels': []}

    def _save_to_file(self, file_path, data):
        """Helper function to save data to a file in a thread-safe way"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"📁 Saved data to {file_path}")
        except PermissionError:
            print(f"⚠️  Cannot write to {file_path} (read-only filesystem)")
        except Exception as e:
            print(f"❌ Error saving to file {file_path}: {e}")

    def _load_from_file(self, file_path):
        """Helper function to load data from a file in a thread-safe way"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📁 Loaded data from {file_path}")
                return data
        except Exception as e:
            print(f"❌ Error loading from file {file_path}: {e}")
            return {} if 'settings' in file_path else []

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
