"""
Improved YouTube search functions for the Music Updater project
Adds more robust handling of problematic artists like Fit For A King
"""

# Function to enhance the get_youtube_music_topic_url function in discord_bot.py
def get_enhanced_youtube_music_topic_url(artist, release_title=None, try_music_link=True):
    """
    Enhanced version of get_youtube_music_topic_url with better handling of edge cases
    
    Args:
        artist (str): Artist name
        release_title (str, optional): Release title. Defaults to None.
        try_music_link (bool): Whether to try finding a YouTube Music link
        
    Returns:
        str: YouTube URL (direct video or search URL)
    """
    import os
    import json
    import urllib.parse
    import requests
    from discord_bot import YouTubeAPI
    
    # Check fallback links first for known problematic artists
    key = f"{artist} - {release_title}".lower() if release_title else artist.lower()
    
    # Try to load fallback links
    fallback_links = {}
    try:
        if os.path.exists('youtube_fallback_links.json'):
            with open('youtube_fallback_links.json', 'r') as f:
                fallback_links = json.load(f)
                print(f"📂 Loaded {len(fallback_links)} fallback links")
                
            # Check if we have a direct fallback for this artist/release
            if key in fallback_links:
                url = fallback_links[key]
                print(f"✅ Using known fallback link for '{key}': {url}")
                return url
            # If looking for a release but no specific entry, check for artist
            elif release_title and artist.lower() in fallback_links:
                print(f"ℹ️ No specific fallback for '{key}', but found artist fallback")
    except Exception as e:
        print(f"⚠️ Error loading fallback links: {e}")
    
    # Format the search query
    search_query = f"{artist} - {release_title}" if release_title else f"{artist}"
    
    if try_music_link:
        search_query += " official"
    
    print(f"🎵 Looking for YouTube link: {search_query}")
    
    # Initialize YouTube API
    youtube = YouTubeAPI()
    
    # Check if we have a valid API key
    if not youtube.api_key or len(youtube.api_key) < 10:
        print(f"⚠️ YouTube API key invalid or missing")
        return get_fallback_search_url(search_query)
    
    # STEP 1: For ARTISTS - Try multiple search strategies
    if not release_title:
        print(f"🔍 Searching for artist: {artist}")
        
        # Try multiple search strategies for artists
        artist_strategies = [
            f"{artist} topic",
            f"{artist} - Topic",
            f"{artist} official artist",
            f"{artist} music"
        ]
        
        best_artist_result = None
        best_artist_score = 0
        
        for strategy in artist_strategies:
            print(f"  🔍 Trying artist search strategy: '{strategy}'")
            result = youtube.search_videos(strategy, max_results=5)
            
            if 'items' in result and len(result['items']) > 0:
                for item in result['items']:
                    # Skip if no videoId (might be a channel instead)
                    if 'id' not in item or 'videoId' not in item.get('id', {}):
                        print(f"  ⚠️ Item missing videoId, skipping")
                        continue
                        
                    video_id = item['id']['videoId']
                    title = item['snippet']['title']
                    channel = item['snippet']['channelTitle']
                    
                    # Score the result
                    score = 0
                    
                    # Exact artist name in channel name
                    if artist.lower() in channel.lower():
                        score += 5
                    
                    # Topic channel is high value
                    if "topic" in channel.lower():
                        score += 10
                    
                    # Official channel
                    if "official" in channel.lower() or "vevo" in channel.lower():
                        score += 7
                    
                    print(f"    Result: {title} | Channel: {channel} | Score: {score}")
                    
                    if score > best_artist_score:
                        best_artist_score = score
                        best_artist_result = {
                            "video_id": video_id,
                            "title": title,
                            "channel": channel
                        }
        
        # If we found a good artist result, return it
        if best_artist_result and best_artist_score >= 5:
            video_id = best_artist_result["video_id"]
            print(f"✅ Found best artist match: {best_artist_result['title']} ({best_artist_result['channel']})")
            
            # For topic channels, use YouTube Music URL
            if "topic" in best_artist_result['channel'].lower():
                return f"https://music.youtube.com/watch?v={video_id}"
            else:
                return f"https://www.youtube.com/watch?v={video_id}"
    
    # STEP 2: For ALBUMS - Try to find official playlists
    if release_title and is_likely_album(release_title):
        print(f"🔍 Searching for album: {artist} - {release_title}")
        
        # Try multiple search strategies for albums
        playlist_strategies = [
            f"{artist} {release_title} album",
            f"{artist} {release_title} full album",
            f"{artist} {release_title} official album"
        ]
        
        for strategy in playlist_strategies:
            print(f"  🔍 Trying playlist search: '{strategy}'")
            playlist_results = youtube.search_playlists(strategy, max_results=5)
            
            if 'items' in playlist_results and len(playlist_results['items']) > 0:
                # Look for official playlists
                for item in playlist_results['items']:
                    # Skip if no playlistId
                    if 'id' not in item or 'playlistId' not in item.get('id', {}):
                        continue
                        
                    playlist_id = item['id']['playlistId']
                    title = item['snippet']['title']
                    channel = item['snippet']['channelTitle']
                    
                    # Check if likely an official playlist
                    is_official = (
                        " - Topic" in channel or 
                        "VEVO" in channel or 
                        "Official" in channel or
                        (artist.lower() in channel.lower() and 
                         any(word.lower() in title.lower() for word in release_title.lower().split()))
                    )
                    
                    # Also check if title contains enough of the release name
                    words_in_title = sum(1 for word in release_title.lower().split() 
                                      if word.lower() in title.lower())
                    words_match_ratio = words_in_title / len(release_title.lower().split())
                    
                    if is_official and words_match_ratio > 0.5:
                        print(f"  ✅ Found likely official playlist: {title} ({channel})")
                        return f"https://music.youtube.com/playlist?list={playlist_id}"
    
    # STEP 3: For TRACKS - Try to find the exact song/track or album title track
    print(f"🔍 Searching for track: {artist} - {release_title}" if release_title else f"🔍 Searching for artist: {artist}")
    
    # Try multiple search strategies
    track_strategies = [
        f"{artist} {release_title} topic" if release_title else f"{artist} topic",
        f"{artist} {release_title} official" if release_title else f"{artist} official",
        f"{artist} {release_title} audio" if release_title else f"{artist} music"
    ]
    
    best_track_result = None
    best_track_score = 0
    
    for strategy in track_strategies:
        print(f"  🔍 Trying track search: '{strategy}'")
        result = youtube.search_videos(strategy, max_results=5)
        
        if 'items' in result and len(result['items']) > 0:
            for item in result['items']:
                # Skip if no videoId
                if 'id' not in item or 'videoId' not in item.get('id', {}):
                    continue
                    
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                channel = item['snippet']['channelTitle']
                
                # Score the result
                score = 0
                
                # Artist name in title or channel
                if artist.lower() in title.lower() or artist.lower() in channel.lower():
                    score += 5
                
                # Release name in title (if we have one)
                if release_title and release_title.lower() in title.lower():
                    score += 8
                
                # Topic channel is high value
                if "topic" in channel.lower() and artist.lower() in channel.lower():
                    score += 10
                
                # Official channel
                if "official" in channel.lower() or "vevo" in channel.lower():
                    score += 7
                    
                print(f"    Result: {title} | Channel: {channel} | Score: {score}")
                
                if score > best_track_score:
                    best_track_score = score
                    best_track_result = {
                        "video_id": video_id,
                        "title": title,
                        "channel": channel
                    }
    
    # If we found a good track result, return it
    if best_track_result and best_track_score >= 5:
        video_id = best_track_result["video_id"]
        print(f"✅ Found best track match: {best_track_result['title']} ({best_track_result['channel']})")
        
        # For topic channels or if trying for music links, use YouTube Music URL
        if "topic" in best_track_result['channel'].lower() or try_music_link:
            return f"https://music.youtube.com/watch?v={video_id}"
        else:
            return f"https://www.youtube.com/watch?v={video_id}"
    
    # STEP 4: If all else fails, try fallback links or return search URL
    print(f"⚠️ No good match found after trying multiple strategies")
    
    # Try artist fallback if we were looking for a release
    if release_title and artist.lower() in fallback_links:
        url = fallback_links[artist.lower()]
        print(f"✅ Using artist fallback link: {url}")
        return url
    
    # Last resort - return a search URL
    return get_fallback_search_url(search_query)

def is_likely_album(release_title):
    """Check if a release title is likely an album based on common patterns"""
    # Common album words
    album_indicators = ['album', 'ep', 'lp', 'deluxe', 'edition', 'complete', 'full']
    
    # Check for album indicators
    for indicator in album_indicators:
        if indicator.lower() in release_title.lower():
            return True
    
    # Count number of words (albums often have fewer words than song titles)
    word_count = len(release_title.split())
    if word_count <= 4:
        return True
    
    return False

def get_fallback_search_url(query):
    """Generate a YouTube search URL for a query"""
    # Convert spaces to + for URL format and properly encode
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://music.youtube.com/search?q={encoded_query}"
    print(f"ℹ️ FALLBACK: Using YouTube Music search URL: {search_url}")
    return search_url

# Test function to compare original and enhanced implementations
def compare_search_implementations():
    """
    Compare the original and enhanced YouTube search implementations
    for problematic artists like Fit For A King
    """
    from discord_bot import get_youtube_music_topic_url as original_search
    
    test_cases = [
        {"artist": "Fit For A King", "release": None, "description": "Artist only"},
        {"artist": "Fit For A King", "release": "The Hell We Create", "description": "Album"},
        {"artist": "Fit For A King", "release": "End (The Other Side)", "description": "Song"}
    ]
    
    print("🔍 Comparing YouTube Search Implementations")
    print("=" * 60)
    
    for case in test_cases:
        artist = case["artist"]
        release = case["release"]
        desc = case["description"]
        
        print(f"\n📌 Test Case: {artist} - {release if release else 'N/A'} ({desc})")
        print("-" * 60)
        
        # Original implementation
        print("🔹 ORIGINAL IMPLEMENTATION:")
        try:
            original_url = original_search(artist, release, True)
            print(f"  Result: {original_url}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Enhanced implementation
        print("\n🔹 ENHANCED IMPLEMENTATION:")
        try:
            enhanced_url = get_enhanced_youtube_music_topic_url(artist, release, True)
            print(f"  Result: {enhanced_url}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n✅ Comparison completed!")

if __name__ == "__main__":
    compare_search_implementations()
