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
    
    def save_artists(self, artists):
        """Save artists list to JSON file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(artists, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            return False
    
    def load_artists(self):
        """Load artists list from JSON file"""
        if not os.path.exists(self.data_file):
            return []
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return []
    
    def save_bot_settings(self, settings):
        """Save bot settings to JSON file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return True
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
