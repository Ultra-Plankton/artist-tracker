"""
Generate YouTube Music playlist links for all artists and albums in the database
"""
import os
import json
from discord_bot import YouTubeAPI, get_youtube_music_topic_url
import time

def generate_youtube_music_playlists():
    """Generate YouTube Music playlist links for all artists and albums"""
    print("🎵 Generating YouTube Music playlist links")
    print("-" * 60)
    
    try:
        # Load existing artists data
        with open('artists_data.json', 'r') as f:
            artists = json.load(f)
            
        print(f"📋 Loaded {len(artists)} artists from database")
        
        # Load existing fallback links if available
        fallback_links = {}
        if os.path.exists('youtube_fallback_links.json'):
            try:
                with open('youtube_fallback_links.json', 'r') as f:
                    fallback_links = json.load(f)
                print(f"📄 Loaded {len(fallback_links)} existing fallback links")
            except:
                print("⚠️ Could not load existing fallback links, creating new file")
        
        # Create a new dictionary to store YouTube Music playlist links
        youtube_music_links = {}
        
        # Process each artist
        for i, artist in enumerate(artists, 1):
            artist_name = artist['name']
            print(f"\n{i}/{len(artists)} Processing: {artist_name}")
            
            # Get artist YouTube Music URL
            try:
                artist_url = get_youtube_music_topic_url(artist_name)
                youtube_music_links[artist_name.lower()] = artist_url
                print(f"✅ Artist URL: {artist_url}")
            except Exception as e:
                print(f"❌ Error getting artist URL: {e}")
            
            # Process albums
            if 'albums' in artist and artist['albums']:
                print(f"📀 Processing {len(artist['albums'])} albums")
                
                for album in artist['albums']:
                    album_name = album['name']
                    key = f"{artist_name} - {album_name}".lower()
                    
                    try:
                        # Try to find YouTube Music playlist specifically for albums
                        album_url = get_youtube_music_topic_url(artist_name, album_name)
                        youtube_music_links[key] = album_url
                        print(f"  ✅ Album '{album_name}': {album_url}")
                        
                        # Avoid hitting API rate limits
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"  ❌ Error getting album URL for '{album_name}': {e}")
            
            # Process singles
            if 'singles' in artist and artist['singles']:
                print(f"💿 Processing {len(artist['singles'])} singles")
                
                for single in artist['singles']:
                    single_name = single['name']
                    key = f"{artist_name} - {single_name}".lower()
                    
                    try:
                        # Get YouTube Music URL for the single
                        single_url = get_youtube_music_topic_url(artist_name, single_name)
                        youtube_music_links[key] = single_url
                        print(f"  ✅ Single '{single_name}': {single_url}")
                        
                        # Avoid hitting API rate limits
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"  ❌ Error getting single URL for '{single_name}': {e}")
            
            # Merge with existing fallback links
            youtube_music_links.update(fallback_links)
            
            # Save after each artist to avoid losing progress if the script crashes
            with open('youtube_music_links.json', 'w') as f:
                json.dump(youtube_music_links, f, indent=2)
                
            print(f"💾 Saved {len(youtube_music_links)} YouTube Music links")
            
            # Add a delay to avoid hitting API rate limits
            if i < len(artists):
                print("⏳ Waiting 2 seconds before next artist...")
                time.sleep(2)
        
        print("\n✅ YouTube Music playlist generation completed!")
        print(f"📊 Generated {len(youtube_music_links)} YouTube Music links")
        print(f"📄 Results saved to youtube_music_links.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_youtube_music_playlists()
