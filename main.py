#!/usr/bin/env python3
"""
Music Updater - Artist Tracker
A simple tool to track your favorite artists and their latest releases.
Now with Spotify API integration!
"""

from datetime import datetime
from spotify_api import SpotifyAPI
from data_manager import DataManager
import asyncio

class ArtistTracker:
    def __init__(self):
        self.artists = []
        self.spotify = SpotifyAPI()
        self.data_manager = DataManager()

    async def load_data(self):
        """Load saved artist data asynchronously"""
        artists = await self.data_manager.load_artists()
        if isinstance(artists, list):
            self.artists = artists
        else:
            print("⚠️  Loaded artists is not a list, reinitializing as empty list.")
            self.artists = []
        if self.artists:
            print(f"📁 Loaded {len(self.artists)} saved artists")

    async def save_data(self):
        """Save artist data to file asynchronously"""
        if not isinstance(self.artists, list):
            print("⚠️  self.artists is not a list, cannot save.")
            return False
        return await self.data_manager.save_artists(self.artists)

    async def add_artist(self, name, genre=None):
        """Add an artist to track with Spotify integration (async)"""
        if not isinstance(self.artists, list):
            print("⚠️  self.artists is not a list, cannot add artist.")
            self.artists = []
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
        if self.spotify.is_available():
            print(f"🔍 Searching for '{name}' on Spotify...")
            spotify_data = self.spotify.search_artist(name)
            if spotify_data:
                artist_data['spotify_data'] = spotify_data
                artist_data['name'] = spotify_data['name']
                print(f"✅ Found on Spotify: {spotify_data['name']}")
                if spotify_data['genres']:
                    genres_display = ', '.join(spotify_data['genres'][:3])
                    if len(spotify_data['genres']) > 3:
                        genres_display += f" (+{len(spotify_data['genres']) - 3} more)"
                    print(f"   🎸 Genres: {genres_display}")
                    if not genre and spotify_data['genres']:
                        artist_data['genre'] = spotify_data['genres'][0]
                else:
                    print(f"   🎸 Genres: No genres listed on Spotify")
                print(f"   👥 Followers: {spotify_data['followers']:,}")
                print(f"   📊 Popularity: {spotify_data['popularity']}/100")
                releases_by_type = self.spotify.get_latest_by_type(spotify_data['id'])
                latest_album = releases_by_type['latest_album']
                latest_single = releases_by_type['latest_single']
                artist_data['latest_album'] = latest_album
                artist_data['latest_single'] = latest_single
                latest = self.spotify.get_latest_release(spotify_data['id'])
                if latest:
                    artist_data['latest_release'] = latest
                if latest_album:
                    print(f"   💿 Latest Album: {latest_album['name']} ({latest_album['release_date']})")
                if latest_single:
                    print(f"   🎵 Latest Single: {latest_single['name']} ({latest_single['release_date']})")
                if not latest_album and not latest_single and latest:
                    print(f"   🆕 Latest: {latest['name']} ({latest['release_date']})")
            else:
                print(f"⚠️  '{name}' not found on Spotify - added as offline artist")
        if isinstance(self.artists, list):
            self.artists.append(artist_data)
            await self.save_data()
            print(f"✅ Added artist: {artist_data['name']}")
        else:
            print("❌ Could not add artist, self.artists is not a list.")

    def get_current_date(self):
        return datetime.now().strftime("%Y-%m-%d")

    async def list_artists(self):
        if not isinstance(self.artists, list) or not self.artists:
            print("📭 No artists being tracked yet.")
            return
        print("\n🎵 Tracked Artists:")
        for i, artist in enumerate(self.artists, 1):
            print(f"{i}. {artist['name']} ({artist.get('genre', 'Unknown')})")
            if artist.get('latest_album'):
                print(f"   💿 Latest Album: {artist['latest_album']['name']} ({artist['latest_album']['release_date']})")
            if artist.get('latest_single'):
                print(f"   🎵 Latest Single: {artist['latest_single']['name']} ({artist['latest_single']['release_date']})")
            if artist.get('latest_release') and not artist.get('latest_album') and not artist.get('latest_single'):
                print(f"   🆕 Latest: {artist['latest_release']['name']} ({artist['latest_release']['release_date']})")

    async def remove_artist(self, name):
        if not isinstance(self.artists, list):
            print("⚠️  self.artists is not a list, cannot remove artist.")
            return
        for artist in self.artists:
            if artist['name'].lower() == name.lower():
                self.artists.remove(artist)
                await self.save_data()
                print(f"✅ Removed artist: {artist['name']}")
                return
        print(f"❌ Artist '{name}' not found in your tracking list.")

    async def show_stats(self):
        if not isinstance(self.artists, list):
            print("⚠️  self.artists is not a list, cannot show stats.")
            return
        print("\n📊 Music Updater Stats:")
        print(f"Tracked Artists: {len(self.artists)}")
        with_spotify = sum(1 for a in self.artists if a.get('spotify_data'))
        print(f"Spotify Connected: {with_spotify}/{len(self.artists)}")
        recent_albums = sum(1 for a in self.artists if a.get('latest_album'))
        recent_singles = sum(1 for a in self.artists if a.get('latest_single'))
        print(f"Albums Tracked: {recent_albums}")
        print(f"Singles Tracked: {recent_singles}")

async def main():
    tracker = ArtistTracker()
    await tracker.load_data()
    # Example usage (replace with CLI or other interface as needed)
    await tracker.list_artists()
    # await tracker.add_artist("Taylor Swift")
    # await tracker.remove_artist("Taylor Swift")
    # await tracker.show_stats()

if __name__ == "__main__":
    asyncio.run(main())
