#!/usr/bin/env python3
"""
Music Updater - Artist Tracker
A simple tool to track your favorite artists and their latest releases.
Now with Spotify API integration!
"""

from datetime import datetime
from spotify_api import SpotifyAPI
from data_manager import DataManager

class ArtistTracker:
    def __init__(self):
        self.artists = []
        self.spotify = SpotifyAPI()
        self.data_manager = DataManager()
        self.load_data()
    
    def load_data(self):
        """Load saved artist data"""
        self.artists = self.data_manager.load_artists()
        if self.artists:
            print(f"📁 Loaded {len(self.artists)} saved artists")
    
    def save_data(self):
        """Save artist data to file"""
        return self.data_manager.save_artists(self.artists)
    
    def add_artist(self, name, genre=None):
        """Add an artist to track with Spotify integration"""
        # Check if artist already exists
        for artist in self.artists:
            if artist['name'].lower() == name.lower():
                print(f"⚠️  Artist '{name}' is already being tracked!")
                return
        
        artist_data = {
            'name': name,
            'genre': genre,
            'added_date': self.get_current_date(),
            'spotify_data': None,
            'last_checked': None,
            'latest_release': None
        }
        
        # Try to get Spotify data
        if self.spotify.is_available():
            print(f"🔍 Searching for '{name}' on Spotify...")
            spotify_data = self.spotify.search_artist(name)
            
            if spotify_data:
                artist_data['spotify_data'] = spotify_data
                artist_data['name'] = spotify_data['name']  # Use official Spotify name
                print(f"✅ Found on Spotify: {spotify_data['name']}")
                
                # Display genres with better formatting
                if spotify_data['genres']:
                    genres_display = ', '.join(spotify_data['genres'][:3])
                    if len(spotify_data['genres']) > 3:
                        genres_display += f" (+{len(spotify_data['genres']) - 3} more)"
                    print(f"   🎸 Genres: {genres_display}")
                    # Auto-set genre if none provided by user
                    if not genre and spotify_data['genres']:
                        artist_data['genre'] = spotify_data['genres'][0]  # Primary genre
                else:
                    print(f"   🎸 Genres: No genres listed on Spotify")
                
                print(f"   👥 Followers: {spotify_data['followers']:,}")
                print(f"   📊 Popularity: {spotify_data['popularity']}/100")
                
                # Get latest releases by type
                releases_by_type = self.spotify.get_latest_by_type(spotify_data['id'])
                latest_album = releases_by_type['latest_album']
                latest_single = releases_by_type['latest_single']
                
                # Store both in artist data
                artist_data['latest_album'] = latest_album
                artist_data['latest_single'] = latest_single
                
                # Also keep the overall latest release for backward compatibility
                latest = self.spotify.get_latest_release(spotify_data['id'])
                if latest:
                    artist_data['latest_release'] = latest
                
                # Display latest releases
                if latest_album:
                    print(f"   💿 Latest Album: {latest_album['name']} ({latest_album['release_date']})")
                if latest_single:
                    print(f"   🎵 Latest Single: {latest_single['name']} ({latest_single['release_date']})")
                
                if not latest_album and not latest_single and latest:
                    print(f"   🆕 Latest: {latest['name']} ({latest['release_date']})")
            else:
                print(f"⚠️  '{name}' not found on Spotify - added as offline artist")
        
        self.artists.append(artist_data)
        self.save_data()
        print(f"✅ Added artist: {artist_data['name']}")
    
    def list_artists(self):
        """List all tracked artists with enhanced info"""
        if not self.artists:
            print("No artists being tracked yet.")
            return
        
        print("\n" + "="*60)
        print("🎵 TRACKED ARTISTS")
        print("="*60)
        
        for i, artist in enumerate(self.artists, 1):
            print(f"\n{i}. {artist['name']}")
            
            # Show genre information with priority to Spotify data
            if artist['spotify_data'] and artist['spotify_data']['genres']:
                genres_display = ', '.join(artist['spotify_data']['genres'][:3])
                if len(artist['spotify_data']['genres']) > 3:
                    genres_display += f" (+{len(artist['spotify_data']['genres']) - 3} more)"
                print(f"   🎸 Genres: {genres_display}")
            elif artist['genre']:
                print(f"   📂 Genre: {artist['genre']}")
            else:
                print(f"   📂 Genre: Not specified")
            
            # Show Spotify info
            if artist['spotify_data']:
                print(f"   🎵 Spotify: ✅ ({artist['spotify_data']['followers']:,} followers, {artist['spotify_data']['popularity']}/100 popularity)")
                
                # Show latest releases with better formatting
                if artist.get('latest_album'):
                    album = artist['latest_album']
                    print(f"   💿 Latest Album: {album['name']} ({album['release_date']})")
                
                if artist.get('latest_single'):
                    single = artist['latest_single']
                    print(f"   🎵 Latest Single: {single['name']} ({single['release_date']})")
                
                # Fallback to general latest release if specific types not available
                if not artist.get('latest_album') and not artist.get('latest_single') and artist.get('latest_release'):
                    release = artist['latest_release']
                    print(f"   🆕 Latest: {release['name']} ({release['release_date']})")
            else:
                print(f"   🎵 Spotify: ❌ (Offline)")
            
            print(f"   📅 Added: {artist['added_date']}")
    
    def remove_artist(self, name):
        """Remove an artist from tracking"""
        for artist in self.artists:
            if artist['name'].lower() == name.lower():
                self.artists.remove(artist)
                self.save_data()
                print(f"✅ Removed artist: {name}")
                return
        print(f"❌ Artist '{name}' not found.")
    
    def check_new_releases(self):
        """Check for new releases from all tracked artists"""
        if not self.spotify.is_available():
            print("❌ Spotify API not available - cannot check for new releases")
            return
        
        print("\n🔄 Checking for new releases...")
        new_releases_found = False
        
        for artist in self.artists:
            if not artist['spotify_data']:
                continue  # Skip offline artists
            
            print(f"🔍 Checking {artist['name']}...")
            
            try:
                # Get latest releases by type
                releases_by_type = self.spotify.get_latest_by_type(artist['spotify_data']['id'])
                latest_album = releases_by_type['latest_album']
                latest_single = releases_by_type['latest_single']
                
                release_found = False
                
                # Check for new album
                if latest_album and (not artist.get('latest_album') or 
                    latest_album['release_date'] > artist['latest_album']['release_date']):
                    print(f"🆕 NEW ALBUM: {artist['name']} - {latest_album['name']} ({latest_album['release_date']})")
                    artist['latest_album'] = latest_album
                    release_found = True
                
                # Check for new single
                if latest_single and (not artist.get('latest_single') or 
                    latest_single['release_date'] > artist['latest_single']['release_date']):
                    print(f"🆕 NEW SINGLE: {artist['name']} - {latest_single['name']} ({latest_single['release_date']})")
                    artist['latest_single'] = latest_single
                    release_found = True
                
                # Also update the general latest release for backward compatibility
                latest = self.spotify.get_latest_release(artist['spotify_data']['id'])
                if latest and (not artist.get('latest_release') or 
                    latest['release_date'] > artist['latest_release']['release_date']):
                    artist['latest_release'] = latest
                
                if release_found:
                    new_releases_found = True
                
                artist['last_checked'] = self.get_current_date()
                
            except Exception as e:
                print(f"❌ Error checking {artist['name']}: {e}")
        
        if new_releases_found:
            self.save_data()
            print("✅ Found new releases! Data updated.")
        else:
            print("ℹ️  No new releases found.")
    
    def show_artist_details(self, name):
        """Show detailed information about a specific artist"""
        for artist in self.artists:
            if artist['name'].lower() == name.lower():
                print(f"\n" + "="*50)
                print(f"🎤 {artist['name']}")
                print("="*50)
                
                if artist['spotify_data']:
                    sd = artist['spotify_data']
                    print(f"🎵 Spotify ID: {sd['id']}")
                    print(f"👥 Followers: {sd['followers']:,}")
                    print(f"📊 Popularity: {sd['popularity']}/100")
                    print(f"🎸 Genres: {', '.join(sd['genres']) if sd['genres'] else 'Unknown'}")
                    
                    # Show latest releases by type
                    if artist.get('latest_album'):
                        album = artist['latest_album']
                        print(f"\n💿 Latest Album:")
                        print(f"   📀 {album['name']}")
                        print(f"   📅 {album['release_date']}")
                        print(f"   🎵 Tracks: {album['total_tracks']}")
                    
                    if artist.get('latest_single'):
                        single = artist['latest_single']
                        print(f"\n🎵 Latest Single/EP:")
                        print(f"   📀 {single['name']}")
                        print(f"   📅 {single['release_date']}")
                        print(f"   🎵 Tracks: {single['total_tracks']}")
                    
                    # Fallback to general latest release
                    if not artist.get('latest_album') and not artist.get('latest_single') and artist.get('latest_release'):
                        lr = artist['latest_release']
                        print(f"\n🆕 Latest Release:")
                        print(f"   📀 {lr['name']}")
                        print(f"   📅 {lr['release_date']}")
                        print(f"   📂 Type: {lr['type']}")
                        print(f"   🎵 Tracks: {lr['total_tracks']}")
                    
                    # Get recent releases
                    print(f"\n📋 Recent Releases:")
                    releases = self.spotify.get_artist_albums(sd['id'], limit=8)
                    for i, release in enumerate(releases, 1):
                        type_emoji = "💿" if release['type'] == 'album' else "🎵" if release['type'] == 'single' else "📀"
                        print(f"   {i}. {type_emoji} {release['name']} ({release['release_date']}) - {release['type']}")
                
                print(f"\n📅 Added to tracker: {artist['added_date']}")
                print(f"🔍 Last checked: {artist['last_checked'] or 'Never'}")
                return
        
        print(f"❌ Artist '{name}' not found in your tracking list.")
    
    def get_current_date(self):
        """Get current date as string"""
        return datetime.now().strftime("%Y-%m-%d")

def main():
    """Main function to run the artist tracker"""
    tracker = ArtistTracker()
    
    print("🎵 Music Updater - Artist Tracker 🎵")
    print("Now with Spotify integration!")
    
    if not tracker.spotify.is_available():
        print("\n⚠️  Running in offline mode. To enable Spotify features:")
        print("   1. Get credentials from https://developer.spotify.com/dashboard")
        print("   2. Create a .env file with SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")
    
    while True:
        print("\nWhat would you like to do?")
        print("1. Add artist")
        print("2. List artists")
        print("3. Remove artist")
        print("4. Check for new releases")
        print("5. Show artist details")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            name = input("Enter artist name: ").strip()
            genre = input("Enter genre (optional): ").strip()
            genre = genre if genre else None
            tracker.add_artist(name, genre)
        
        elif choice == '2':
            tracker.list_artists()
        
        elif choice == '3':
            name = input("Enter artist name to remove: ").strip()
            tracker.remove_artist(name)
        
        elif choice == '4':
            tracker.check_new_releases()
        
        elif choice == '5':
            name = input("Enter artist name for details: ").strip()
            tracker.show_artist_details(name)
        
        elif choice == '6':
            print("Thanks for using Music Updater! 🎵")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
