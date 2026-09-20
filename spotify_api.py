"""
Spotify API integration for Music Updater
Handles fetching artist data and latest releases from Spotify
"""

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import config
from datetime import datetime
import re
from difflib import SequenceMatcher

class SpotifyAPI:
    def __init__(self):
        self.sp = None
        self.initialize_spotify()
    
    def initialize_spotify(self):
        """Initialize Spotify API client"""
        try:
            if not config.SPOTIFY_CLIENT_ID or not config.SPOTIFY_CLIENT_SECRET:
                print("⚠️  Spotify credentials not configured. Running in offline mode.")
                return False
            
            client_credentials_manager = SpotifyClientCredentials(
                client_id=config.SPOTIFY_CLIENT_ID,
                client_secret=config.SPOTIFY_CLIENT_SECRET
            )
            # Set explicit request timeout and retry behaviour so stalled HTTP calls do not hang the bot
            self.sp = spotipy.Spotify(
                client_credentials_manager=client_credentials_manager,
                requests_timeout=10,
                retries=5,
            )
            print("✅ Spotify API initialized successfully!")
            return True
        except Exception as e:
            print(f"❌ Error initializing Spotify API: {e}")
            return False
    
    def search_artist(self, artist_name, interactive=True):
        """Search for an artist on Spotify"""
        if not self.sp:
            return None
        
        try:
            results = self.sp.search(q=artist_name, type='artist', limit=10)
            if results and results['artists']['items']:
                # Show multiple results if available for better matching
                artists = results['artists']['items']
                
                # If only one result, return it
                if len(artists) == 1:
                    artist = artists[0]
                else:
                    # For Discord bot (non-interactive), return the best match
                    if not interactive:
                        def similarity_score(artist, search_term):
                            normalized_artist = re.sub(r"[^a-z0-9]+", " ", artist['name'].casefold()).strip()
                            normalized_search = re.sub(r"[^a-z0-9]+", " ", search_term.casefold()).strip()
                            artist_tokens = set(normalized_artist.split())
                            search_tokens = set(normalized_search.split())
                            shared_tokens = len(artist_tokens & search_tokens)
                            sequence_similarity = SequenceMatcher(
                                None, normalized_search, normalized_artist
                            ).ratio()
                            exact_match = normalized_artist == normalized_search
                            starts_with_search = normalized_artist.startswith(normalized_search + " ")
                            extra_tokens = max(len(artist_tokens - search_tokens), 0)

                            return (
                                exact_match,
                                starts_with_search,
                                shared_tokens,
                                sequence_similarity,
                                -extra_tokens,
                                artist['popularity'],
                                artist['followers']['total'],
                            )
                        
                        artist = max(artists, key=lambda a: similarity_score(a, artist_name))
                    else:
                        # Show multiple options for user to choose (CLI mode)
                        print(f"\nFound {len(artists)} artists matching '{artist_name}':")
                        for i, artist in enumerate(artists, 1):
                            genres_str = ', '.join(artist['genres'][:3]) if artist['genres'] else 'No genres listed'
                            followers = artist['followers']['total']
                            popularity = artist['popularity']
                            print(f"   {i}. {artist['name']} ({followers:,} followers, {popularity}/100 popularity) - {genres_str}")
                        
                        while True:
                            try:
                                choice = input(f"\nSelect artist (1-{len(artists)}, or 0 to cancel): ").strip()
                                if choice == '0':
                                    return None
                                choice_idx = int(choice) - 1
                                if 0 <= choice_idx < len(artists):
                                    artist = artists[choice_idx]
                                    break
                                else:
                                    print("Invalid choice. Please try again.")
                            except ValueError:
                                print("Please enter a valid number.")
                
                return {
                    'id': artist['id'],
                    'name': artist['name'],
                    'followers': artist['followers']['total'],
                    'popularity': artist['popularity'],
                    'genres': artist['genres'],
                    'external_urls': artist['external_urls'],
                    'images': artist['images']
                }
        except Exception as e:
            print(f"❌ Error searching for artist '{artist_name}': {e}")
        
        return None
    
    def get_artist_albums(self, artist_id, limit=10):
        """Get latest albums/releases for an artist"""
        if not self.sp:
            return []
        
        try:
            # Get albums, singles, and compilations
            albums = self.sp.artist_albums(
                artist_id, 
                album_type='album,single,compilation', 
                country=config.SPOTIFY_MARKET,
                limit=limit
            )
            
            releases = []
            if albums and albums['items']:
                for album in albums['items']:
                    release = {
                        'name': album['name'],
                        'release_date': album['release_date'],
                        'type': album['album_type'],
                        'total_tracks': album['total_tracks'],
                        'external_urls': album['external_urls'],
                        'images': album['images']
                    }
                    releases.append(release)
            
            # Sort by release date (newest first)
            releases.sort(key=lambda x: x['release_date'], reverse=True)
            return releases
            
        except Exception as e:
            print(f"❌ Error getting albums for artist ID '{artist_id}': {e}")
            return []
    
    def get_latest_release(self, artist_id):
        """Get the most recent release for an artist"""
        albums = self.get_artist_albums(artist_id, limit=1)
        return albums[0] if albums else None
    
    def get_latest_by_type(self, artist_id):
        """Get the latest release by type (album vs single)"""
        if not self.sp:
            return {'latest_album': None, 'latest_single': None}
        
        try:
            # Get more releases to find both albums and singles
            all_releases = self.get_artist_albums(artist_id, limit=20)
            
            latest_album = None
            latest_single = None
            
            for release in all_releases:
                # Check for latest album (full albums only)
                if release['type'] == 'album' and not latest_album:
                    latest_album = release
                
                # Check for latest single/EP
                if release['type'] in ['single', 'ep'] and not latest_single:
                    latest_single = release
                
                # Stop once we have both
                if latest_album and latest_single:
                    break
            
            return {
                'latest_album': latest_album,
                'latest_single': latest_single
            }
            
        except Exception as e:
            print(f"❌ Error getting releases by type for artist ID '{artist_id}': {e}")
            return {'latest_album': None, 'latest_single': None}
    
    def is_available(self):
        """Check if Spotify API is available"""
        return self.sp is not None
