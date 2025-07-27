"""
Cloud database integration for persistent artist storage
Supports multiple cloud database providers for artist data persistence
"""

import json
import os
import requests
from typing import List, Dict, Any, Optional

class CloudDatabase:
    """Base class for cloud database providers"""
    
    def save_artists(self, artists: List[Dict[str, Any]]) -> bool:
        """Save artists to cloud database"""
        raise NotImplementedError
    
    def load_artists(self) -> List[Dict[str, Any]]:
        """Load artists from cloud database"""
        raise NotImplementedError

class JSONBinDatabase(CloudDatabase):
    """JSONBin.io cloud storage - Free tier: 100MB storage"""
    
    def __init__(self):
        self.api_key = os.getenv('JSONBIN_API_KEY')
        self.bin_id = os.getenv('JSONBIN_BIN_ID')
        self.base_url = 'https://api.jsonbin.io/v3'
    
    def save_artists(self, artists: List[Dict[str, Any]]) -> bool:
        """Save artists to JSONBin"""
        if not self.api_key or not self.bin_id:
            print("⚠️  JSONBin credentials not configured")
            return False
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'X-Master-Key': self.api_key
            }
            
            response = requests.put(
                f"{self.base_url}/b/{self.bin_id}",
                headers=headers,
                json=artists,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"☁️  Saved {len(artists)} artists to cloud database")
                return True
            else:
                print(f"❌ Failed to save to cloud: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Cloud save error: {e}")
            return False
    
    def load_artists(self) -> List[Dict[str, Any]]:
        """Load artists from JSONBin"""
        if not self.api_key or not self.bin_id:
            print("⚠️  JSONBin credentials not configured")
            return []
        
        try:
            headers = {
                'X-Master-Key': self.api_key
            }
            
            response = requests.get(
                f"{self.base_url}/b/{self.bin_id}/latest",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                artists = data.get('record', [])
                print(f"☁️  Loaded {len(artists)} artists from cloud database")
                return artists
            else:
                print(f"❌ Failed to load from cloud: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Cloud load error: {e}")
            return []

class GitHubGistDatabase(CloudDatabase):
    """GitHub Gist storage - Free with GitHub account"""
    
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')
        self.gist_id = os.getenv('GITHUB_GIST_ID')
        self.filename = 'artists_data.json'
    
    def save_artists(self, artists: List[Dict[str, Any]]) -> bool:
        """Save artists to GitHub Gist"""
        if not self.token or not self.gist_id:
            print("⚠️  GitHub credentials not configured")
            return False
        
        try:
            headers = {
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            data = {
                'files': {
                    self.filename: {
                        'content': json.dumps(artists, indent=2)
                    }
                }
            }
            
            response = requests.patch(
                f"https://api.github.com/gists/{self.gist_id}",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"☁️  Saved {len(artists)} artists to GitHub Gist")
                return True
            else:
                print(f"❌ Failed to save to GitHub: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ GitHub save error: {e}")
            return False
    
    def load_artists(self) -> List[Dict[str, Any]]:
        """Load artists from GitHub Gist"""
        if not self.token or not self.gist_id:
            print("⚠️  GitHub credentials not configured")
            return []
        
        try:
            headers = {
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(
                f"https://api.github.com/gists/{self.gist_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                gist_data = response.json()
                content = gist_data['files'][self.filename]['content']
                artists = json.loads(content)
                print(f"☁️  Loaded {len(artists)} artists from GitHub Gist")
                return artists
            else:
                print(f"❌ Failed to load from GitHub: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ GitHub load error: {e}")
            return []

def get_cloud_database() -> Optional[CloudDatabase]:
    """Get configured cloud database provider"""
    # Try JSONBin first
    if os.getenv('JSONBIN_API_KEY') and os.getenv('JSONBIN_BIN_ID'):
        return JSONBinDatabase()
    
    # Try GitHub Gist
    if os.getenv('GITHUB_TOKEN') and os.getenv('GITHUB_GIST_ID'):
        return GitHubGistDatabase()
    
    return None
