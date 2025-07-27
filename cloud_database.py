"""
Cloud database integration for persistent artist storage (Async Version)
Supports multiple cloud database providers for artist data persistence
"""

import json
import os
import aiohttp
from typing import List, Dict, Any, Optional

class CloudDatabase:
    """Base class for cloud database providers"""
    
    async def save_artists(self, artists: List[Dict[str, Any]]) -> bool:
        """Save artists to cloud database"""
        raise NotImplementedError
    
    async def load_artists(self) -> List[Dict[str, Any]]:
        """Load artists from cloud database"""
        raise NotImplementedError
    
    async def save_bot_settings(self, settings: Dict[str, Any]) -> bool:
        """Save bot settings to cloud database"""
        raise NotImplementedError
    
    async def load_bot_settings(self) -> Dict[str, Any]:
        """Load bot settings from cloud database"""
        raise NotImplementedError

class JSONBinDatabase(CloudDatabase):
    """JSONBin.io cloud storage - Free tier: 100MB storage"""
    
    def __init__(self):
        self.api_key = os.getenv('JSONBIN_API_KEY')
        self.bin_id = os.getenv('JSONBIN_BIN_ID')
        self.settings_bin_id = os.getenv('JSONBIN_SETTINGS_BIN_ID')
        self.base_url = 'https://api.jsonbin.io/v3'
    
    async def save_artists(self, artists: List[Dict[str, Any]]) -> bool:
        """Save artists to JSONBin"""
        if not self.api_key or not self.bin_id:
            print("⚠️  JSONBin credentials not configured for artists")
            return False
        
        headers = {'Content-Type': 'application/json', 'X-Master-Key': self.api_key}
        url = f"{self.base_url}/b/{self.bin_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, json=artists, timeout=10) as response:
                    if response.status == 200:
                        print(f"✅ Saved {len(artists)} artists to cloud database")
                        return True
                    else:
                        print(f"❌ Failed to save artists to cloud: {response.status}")
                        print(f"☁️  Response body: {await response.text()}")
                        return False
        except Exception as e:
            print(f"❌ Cloud artists save error: {e}")
            return False
    
    async def load_artists(self) -> List[Dict[str, Any]]:
        """Load artists from JSONBin"""
        if not self.api_key or not self.bin_id:
            print("⚠️  JSONBin credentials not configured for artists")
            return []
            
        headers = {'X-Master-Key': self.api_key}
        url = f"{self.base_url}/b/{self.bin_id}/latest"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        artists = data.get('record', [])
                        print(f"✅ Loaded {len(artists)} artists from cloud database")
                        return artists
                    else:
                        print(f"❌ Failed to load artists from cloud: {response.status}")
                        print(f"☁️  Response body: {await response.text()}")
                        return []
        except Exception as e:
            print(f"❌ Cloud artists load error: {e}")
            return []
    
    async def save_bot_settings(self, settings: Dict[str, Any]) -> bool:
        """Save bot settings to JSONBin (separate bin)"""
        if not self.api_key or not self.settings_bin_id:
            print("⚠️  JSONBin settings bin not configured")
            return False
            
        headers = {'Content-Type': 'application/json', 'X-Master-Key': self.api_key}
        url = f"{self.base_url}/b/{self.settings_bin_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, json=settings, timeout=10) as response:
                    if response.status == 200:
                        print("✅ Bot settings saved to cloud")
                        return True
                    else:
                        print(f"❌ Failed to save settings to cloud: {response.status}")
                        print(f"☁️  Response body: {await response.text()}")
                        return False
        except Exception as e:
            print(f"❌ Cloud settings save error: {e}")
            return False
    
    async def load_bot_settings(self) -> Dict[str, Any]:
        """Load bot settings from JSONBin (separate bin)"""
        if not self.api_key or not self.settings_bin_id:
            print("⚠️  JSONBin settings bin not configured")
            return {'notification_channels': []}

        headers = {'X-Master-Key': self.api_key}
        url = f"{self.base_url}/b/{self.settings_bin_id}/latest"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        settings = data.get('record', {'notification_channels': []})
                        if 'notification_channels' not in settings:
                            settings['notification_channels'] = []
                        print("✅ Bot settings loaded from cloud")
                        return settings
                    else:
                        print(f"❌ Failed to load settings from cloud: {response.status}")
                        print(f"☁️  Response body: {await response.text()}")
                        return {'notification_channels': []}
        except Exception as e:
            print(f"❌ Cloud settings load error: {e}")
            return {'notification_channels': []}

class GitHubGistDatabase(CloudDatabase):
    """GitHub Gist storage - Free with GitHub account"""
    
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')
        self.gist_id = os.getenv('GITHUB_GIST_ID')
        self.settings_gist_id = os.getenv('GITHUB_SETTINGS_GIST_ID')
        self.base_url = 'https://api.github.com'
    
    async def save_artists(self, artists: List[Dict[str, Any]]) -> bool:
        """Save artists to GitHub Gist"""
        if not self.token or not self.gist_id:
            print("⚠️  GitHub credentials not configured for artists")
            return False

        headers = {'Authorization': f'token {self.token}', 'Accept': 'application/vnd.github.v3+json'}
        url = f"{self.base_url}/gists/{self.gist_id}"
        data = {'files': {'artists_data.json': {'content': json.dumps(artists, indent=2)}}}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, headers=headers, json=data, timeout=10) as response:
                    if response.status == 200:
                        print(f"✅ Saved {len(artists)} artists to GitHub Gist")
                        return True
                    else:
                        print(f"❌ Failed to save artists to GitHub: {response.status}")
                        print(f"☁️  Response body: {await response.text()}")
                        return False
        except Exception as e:
            print(f"❌ GitHub artists save error: {e}")
            return False
    
    async def load_artists(self) -> List[Dict[str, Any]]:
        """Load artists from GitHub Gist"""
        if not self.token or not self.gist_id:
            print("⚠️  GitHub credentials not configured for artists")
            return []

        headers = {'Authorization': f'token {self.token}', 'Accept': 'application/vnd.github.v3+json'}
        url = f"{self.base_url}/gists/{self.gist_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        gist_data = await response.json()
                        content = gist_data['files']['artists_data.json']['content']
                        artists = json.loads(content)
                        print(f"✅ Loaded {len(artists)} artists from GitHub Gist")
                        return artists
                    else:
                        print(f"❌ Failed to load artists from GitHub: {response.status}")
                        print(f"☁️  Response body: {await response.text()}")
                        return []
        except Exception as e:
            print(f"❌ GitHub artists load error: {e}")
            return []
    
    async def save_bot_settings(self, settings: Dict[str, Any]) -> bool:
        """Save bot settings to GitHub Gist (separate gist)"""
        if not self.token or not self.settings_gist_id:
            print("⚠️  GitHub settings gist not configured")
            return False

        headers = {'Authorization': f'token {self.token}', 'Accept': 'application/vnd.github.v3+json'}
        url = f"{self.base_url}/gists/{self.settings_gist_id}"
        data = {'files': {'bot_settings.json': {'content': json.dumps(settings, indent=2)}}}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, headers=headers, json=data, timeout=10) as response:
                    if response.status == 200:
                        print("✅ Bot settings saved to GitHub Gist")
                        return True
                    else:
                        print(f"❌ Failed to save settings to GitHub: {response.status}")
                        print(f"☁️  Response body: {await response.text()}")
                        return False
        except Exception as e:
            print(f"❌ GitHub settings save error: {e}")
            return False
    
    async def load_bot_settings(self) -> Dict[str, Any]:
        """Load bot settings from GitHub Gist (separate gist)"""
        if not self.token or not self.settings_gist_id:
            print("⚠️  GitHub settings gist not configured")
            return {'notification_channels': []}

        headers = {'Authorization': f'token {self.token}', 'Accept': 'application/vnd.github.v3+json'}
        url = f"{self.base_url}/gists/{self.settings_gist_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        gist_data = await response.json()
                        content = gist_data['files']['bot_settings.json']['content']
                        settings = json.loads(content)
                        if 'notification_channels' not in settings:
                            settings['notification_channels'] = []
                        print("✅ Bot settings loaded from GitHub Gist")
                        return settings
                    else:
                        print(f"❌ Failed to load settings from GitHub: {response.status}")
                        print(f"☁️  Response body: {await response.text()}")
                        return {'notification_channels': []}
        except Exception as e:
            print(f"❌ GitHub settings load error: {e}")
            return {'notification_channels': []}

def get_cloud_database() -> Optional[CloudDatabase]:
    """Get configured cloud database provider"""
    # Try JSONBin first
    if os.getenv('JSONBIN_API_KEY') and os.getenv('JSONBIN_BIN_ID'):
        return JSONBinDatabase()
    
    # Try GitHub Gist
    if os.getenv('GITHUB_TOKEN') and os.getenv('GITHUB_GIST_ID'):
        return GitHubGistDatabase()
    
    return None
