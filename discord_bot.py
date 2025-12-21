from cloud_database import JSONBinDatabase
import requests
import io
import urllib.parse
from typing import Optional
"""
Discord Bot integration for Music Updater
Handles Discord notifications and slash commands for artist tracking
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
import sys
import traceback
import sys
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import pytz
from aiohttp import web
import aiohttp
import config
from spotify_api import SpotifyAPI
from data_manager import DataManager
import json
import math
import requests
import urllib.parse

# Helper: get Eastern timezone with safe fallback if ZoneInfo DB is missing
def get_eastern_tz():
    try:
        return ZoneInfo("America/New_York")
    except Exception:
        try:
            # Fallback to pytz on systems without IANA tz database
            return pytz.timezone('US/Eastern')
        except Exception:
            return None

# YouTube API integration
class YouTubeAPI:
    """YouTube API integration for Music Updater"""

    def __init__(self, api_key=None):
        # If no API key is provided, try to get it from config or environment
        if api_key is None:
            api_key = config.YOUTUBE_API_KEY or os.environ.get('YOUTUBE_API_KEY', '')
            
            # Try .env.template as last resort if other sources fail
            if not api_key or len(api_key) < 10:
                try:
                    with open('.env.template', 'r') as f:
                        for line in f:
                            if line.startswith('YOUTUBE_API_KEY='):
                                template_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                                if template_key and len(template_key) > 10:
                                    print(f"⚠️ Using YouTube API key from .env.template as fallback")
                                    api_key = template_key
                                    break
                except Exception as e:
                    print(f"⚠️ Could not load API key from .env.template: {e}")
        
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
        if not api_key or len(api_key) < 10:
            print(f"⚠️ WARNING: Invalid YouTube API key format")
        else:
            print(f"📺 YouTube API initialized with key: {api_key[:5]}...{api_key[-5:] if len(api_key) > 10 else ''}")
            
    async def search_playlists(self, session, query, max_results=3):
        """
        Search for playlists on YouTube, focusing on YouTube Music playlists
        
        Args:
            query (str): The search query
            max_results (int): Maximum number of results to return
            
        Returns:
            dict: The YouTube API response or error
        """
        if not self.api_key or len(self.api_key) < 10:
            print(f"❌ Cannot search YouTube: Invalid API key")
            return {"error": {"message": "Invalid YouTube API key"}, "items": []}
            
        url = f"{self.base_url}/search"
        
        # Modify query to focus on YouTube Music playlists
        search_query = f"{query} youtube music playlist"
        
        params = {
            "part": "snippet",
            "q": search_query,
            "maxResults": max_results,
            "type": "playlist",
            "key": self.api_key
        }
        
        print(f"🎵 Searching for YouTube Music playlists: '{search_query}'")
        
        try:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f"YouTube API HTTP error: {response.status} - {error_text}"
                    print(f"❌ {error_msg}")
                    return {"error": {"message": error_msg}, "items": []}
                
                result = await response.json()
            
            if 'error' in result:
                error_message = result['error'].get('message', 'Unknown error')
                print(f"❌ YouTube API error searching playlists: {error_message}")
                return result
                
            items_count = len(result.get('items', []))
            print(f"✅ Found {items_count} YouTube playlists for '{query}'")
            
            return result
            
        except Exception as e:
            print(f"❌ Error searching YouTube playlists: {e}")
            return {"error": {"message": str(e)}, "items": []}

    async def search_videos(self, session, query, max_results=5, prefer_music=True):
        """
        Search for videos on YouTube
        
        Args:
            query (str): The search query
            max_results (int): Maximum number of results to return
            prefer_music (bool): If True, will try to find YouTube Music links
        """
        if not self.api_key or len(self.api_key) < 10:
            print(f"❌ Cannot search YouTube: Invalid API key")
            return {"error": {"message": "Invalid YouTube API key"}, "items": []}
            
        url = f"{self.base_url}/search"
        
        # Add "topic" to search if looking for official music
        search_query = query
        if prefer_music and "topic" not in query.lower():
            search_query = f"{query} topic"
            print(f"🎵 Modified search to find official topic: '{search_query}'")
        
        params = {
            "part": "snippet",
            "q": search_query,
            "maxResults": max_results,
            "type": "video",
            "videoCategoryId": "10",  # Music category
            "key": self.api_key
        }
        
        print(f"🔍 Searching YouTube for: '{search_query}'")
        print(f"🔑 Using API key: {self.api_key[:5]}...{self.api_key[-5:] if len(self.api_key) > 10 else ''}")
        try:
            async with session.get(url, params=params, timeout=10) as response:
                # Check for HTTP errors
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f"YouTube API HTTP error: {response.status} - {error_text}"
                    print(f"❌ {error_msg}")
                    
                    # Check for specific errors in the response
                    if "quota" in error_text.lower():
                        return {
                            "error": {
                                "code": 403,
                                "message": "YouTube API quota exceeded. Try again tomorrow."
                            }
                        }
                    elif "expired" in error_text.lower():
                        return {
                            "error": {
                                "code": 400,
                                "message": "YouTube API key has expired. Please renew the API key."
                            }
                        }
                        
                    return {"error": {"message": error_msg}, "items": []}
                
                result = await response.json()
            
            # Check for API errors
            if 'error' in result:
                error_message = result['error'].get('message', 'Unknown error')
                error_code = result['error'].get('code', 'Unknown')
                print(f"❌ YouTube API error: {error_code} - {error_message}")
                
                # Detect specific error types
                if 'quota' in error_message.lower():
                    print("⚠️ YouTube API quota exceeded. Wait 24 hours or use a different API key.")
                elif 'expired' in error_message.lower():
                    print("⚠️ YouTube API key has expired. Please renew the API key.")
                    
                return result
            
            items_count = len(result.get('items', []))
            print(f"✅ Found {items_count} YouTube results for '{query}'")
            
            return result
        except asyncio.TimeoutError:
            print(f"⏱️ YouTube API request timed out for '{query}'")
            return {"error": {"message": "Request timed out"}, "items": []}
        except aiohttp.ClientError as e:
            print(f"❌ YouTube API request failed: {e}")
            return {"error": {"message": f"Request failed: {str(e)}"}, "items": []}
        except Exception as e:
            print(f"❌ Unexpected error in YouTube search: {e}")
            return {"error": {"message": f"Unexpected error: {str(e)}"}, "items": []}


def get_youtube_search_url(query):
    """Generate a YouTube search URL for a query"""
    # Convert spaces to + for URL format and properly encode
    encoded_query = urllib.parse.quote(query)
    return f"https://www.youtube.com/results?search_query={encoded_query}"


async def get_youtube_music_topic_url(artist, release_title=None, try_music_link=True):
    """
    Get a YouTube Music Topic URL for an artist or release.
    Tries YouTube API first, falls back to stored links if API fails.
    
    Args:
        artist (str): Artist name
        release_title (str, optional): Release title. Defaults to None.
        try_music_link (bool): Whether to try finding a YouTube Music link
        
    Returns:
        str: YouTube URL (direct video or search URL)
    """
    # Format the search query
    search_query = f"{artist} - {release_title}" if release_title else f"{artist} topic"
    
    if try_music_link:
        search_query += " official"
    
    print(f"🎵 Looking for YouTube link: {search_query}")
    
    # STEP 1: Try to use YouTube API first
    try:
        print(f"🔍 Attempting YouTube API search first...")
        youtube = YouTubeAPI()  # Will load API key automatically
        
        # Check if we have a valid API key before making the request
        if not youtube.api_key or len(youtube.api_key) < 10:
            print(f"⚠️ YouTube API key invalid or missing, length: {len(youtube.api_key) if youtube.api_key else 0}")
            raise ValueError("Invalid YouTube API key")
        
        async with aiohttp.ClientSession() as session:
            # First try searching for playlists if it's an album or we have a release title
            if try_music_link and release_title:
                print(f"🎵 Looking for YouTube Music playlist for album/release...")
                
                # For albums, try to find a playlist
                playlist_query = f"{artist} {release_title} album"
                playlist_results = await youtube.search_playlists(session, playlist_query, max_results=3)
                
                if not 'error' in playlist_results and playlist_results.get('items') and len(playlist_results['items']) > 0:
                    # Look for official playlists
                    best_playlist = None
                    
                    for item in playlist_results['items']:
                        playlist_id = item['id'].get('playlistId')
                        title = item['snippet']['title']
                        channel = item['snippet']['channelTitle']
                        
                        # Check if it's likely an official playlist
                        is_official = (" - Topic" in channel or 
                                      "VEVO" in channel or 
                                      "YouTube Music" in channel or
                                      "Official" in channel or
                                      (artist.lower() in channel.lower() and "topic" in channel.lower()))
                        
                        has_keywords = (artist.lower() in title.lower() and 
                                       any(word.lower() in title.lower() for word in release_title.lower().split()))
                        
                        # For official channels, prioritize this result
                        if is_official and has_keywords:
                            best_playlist = item
                            break
                        # For non-official channels, check if title has both artist and release name
                        elif has_keywords and not best_playlist:
                            best_playlist = item
                            # Keep searching for better matches
                
                if best_playlist:
                    playlist_id = best_playlist['id']['playlistId']
                    title = best_playlist['snippet']['title']
                    channel = best_playlist['snippet']['channelTitle']
                    
                    # Check if it's an official channel before using the YouTube Music URL
                    is_official = (" - Topic" in channel or 
                                  "VEVO" in channel or 
                                  "YouTube Music" in channel or
                                  "Official" in channel)
                    
                    # Format as a YouTube Music URL for official sources, otherwise regular YouTube
                    if is_official:
                        playlist_url = f"https://music.youtube.com/playlist?list={playlist_id}"
                        print(f"✅ SUCCESS: Found official YouTube Music playlist: {playlist_url}")
                    else:
                        playlist_url = f"https://music.youtube.com/playlist?list={playlist_id}"
                        print(f"✅ SUCCESS: Found YouTube Music playlist (non-official): {playlist_url}")
                    
                    print(f"   Title: {title}")
                    print(f"   Channel: {channel}")
                    
                    return playlist_url
        
        # If no playlist found or not looking for one, search for videos
        # Try searching for YouTube Music specific content first
        if try_music_link:
            print(f"🎵 Searching for YouTube Music link...")
            
            # Try adding "topic" to find official artist channels
            music_query = f"{search_query} music.youtube"
            
            async with aiohttp.ClientSession() as session:
                music_result = await youtube.search_videos(session, music_query, max_results=3, prefer_music=True)
                
                # Check for music-specific results
                if not 'error' in music_result and music_result.get('items') and len(music_result['items']) > 0:
                    # Look through results for YouTube Music links
                    for item in music_result['items']:
                        video_id = item['id']['videoId']
                        title = item['snippet']['title']
                        channel = item['snippet']['channelTitle']
                        
                        # Look for official topic channels
                        if " - Topic" in channel or "VEVO" in channel or "Official" in channel or "official" in title:
                            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                            # Also offer YouTube Music URL
                            youtube_music_url = f"https://music.youtube.com/watch?v={video_id}"
                            
                            print(f"✅ SUCCESS: Found official YouTube Music URL: {youtube_music_url}")
                            print(f"   Title: {title}")
                            print(f"   Channel: {channel}")
                            
                            # Return YouTube Music URL for official content
                            return youtube_music_url
                
                print(f"ℹ️ Found results but none were from official artist channels")
        
        # If no YouTube Music-specific results, do a regular search
        result = await youtube.search_videos(session, search_query, max_results=3, prefer_music=True)
        
        # Check for API errors
        if 'error' in result:
            error_message = result['error'].get('message', 'Unknown error')
            print(f"⚠️ YouTube API returned error: {error_message}")
            raise ValueError(f"YouTube API error: {error_message}")
            
        # Check if we got valid results from the API
        if result.get('items') and len(result['items']) > 0:
            best_match = None
            
            # Look for the best match among results
            for item in result['items']:
                video_id = item['id'].get('videoId')
                title = item['snippet']['title']
                channel = item['snippet']['channelTitle']
                
                # Prioritize official channels
                is_official = (" - Topic" in channel or 
                               "VEVO" in channel or 
                               "Official" in channel or
                               "official" in title)
                               
                # Check if the title contains both artist and release (if provided)
                has_keywords = artist.lower() in title.lower()
                if release_title:
                    has_release = any(word.lower() in title.lower() for word in release_title.lower().split())
                    has_keywords = has_keywords and has_release
                
                if best_match is None or (is_official and has_keywords):
                    best_match = item
                    # If it's official and has the right keywords, no need to check further
                    if is_official and has_keywords:
                        break
            
            if best_match:
                video_id = best_match['id']['videoId']
                title = best_match['snippet']['title']
                channel = best_match['snippet']['channelTitle']
                
                # For official channels or "Topic" channels, use YouTube Music URL
                if " - Topic" in channel or "VEVO" in channel or "Official" in channel:
                    youtube_music_url = f"https://music.youtube.com/watch?v={video_id}"
                    print(f"✅ SUCCESS: Found official YouTube Music URL: {youtube_music_url}")
                    print(f"   Title: {title}")
                    print(f"   Channel: {channel}")
                    return youtube_music_url
                
                # For non-official channels, use regular YouTube URL
                youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                print(f"✅ SUCCESS: Found YouTube URL via API: {youtube_url}")
                print(f"   Title: {title}")
                print(f"   Channel: {channel}")
                return youtube_url
        else:
            print(f"⚠️ YouTube API returned no results for: {search_query}")
            raise ValueError("No YouTube results found")
            
    except Exception as e:
        print(f"⚠️ YouTube API search failed: {str(e)}")
        
    # STEP 2: Try fallback links from file
    print(f"🔄 API search failed, trying fallback links...")
    try:
        # Check if fallback file exists
        if not os.path.exists('youtube_fallback_links.json'):
            print(f"⚠️ Fallback file 'youtube_fallback_links.json' not found")
            raise FileNotFoundError("Fallback links file not found")
            
        with open('youtube_fallback_links.json', 'r') as f:
            fallback_links = json.load(f)
            print(f"📂 Loaded fallback links file with {len(fallback_links)} entries")
        
        # Try to find the specific release if title was provided
        if release_title:
            key = f"{artist} - {release_title}".lower()
            if key in fallback_links:
                fallback_url = fallback_links[key]
                print(f"✅ Found fallback YouTube link for specific release: {key}")
                return fallback_url
            else:
                print(f"ℹ️ No specific fallback link for release: {key}")
        
        # Try to find just the artist
        artist_key = artist.lower()
        if artist_key in fallback_links:
            fallback_url = fallback_links[artist_key]
            print(f"✅ Found fallback YouTube link for artist: {artist_key}")
            return fallback_url
        else:
            print(f"ℹ️ No fallback link found for artist: {artist_key}")
            
    except Exception as e:
        print(f"⚠️ Failed to get fallback YouTube link: {str(e)}")
    
    # STEP 3: Last resort - return a search URL
    search_url = get_youtube_search_url(search_query)
    print(f"ℹ️ FALLBACK: Using YouTube search URL as last resort: {search_url}")
    return search_url

# Pagination Views
class ReleasePaginationView(discord.ui.View):
    async def get_apple_music_link(self, session, artist, release_name, is_album=True):
        """Fetch Apple Music link for an album or single using iTunes Search API"""
        base_url = "https://itunes.apple.com/search"
        query = f"{artist} {release_name}"
        params = {
            "term": query,
            "entity": "album" if is_album else "song",
            "limit": 1
        }
        try:
            # Some iTunes endpoints sometimes return a non-JSON mimetype (e.g. text/javascript)
            # which makes aiohttp's response.json() raise ContentTypeError. Read text and
            # parse manually to be resilient to that.
            headers = {
                "Accept": "application/json",
                "User-Agent": "MusicUpdaterBot/1.0"
            }
            async with session.get(base_url, params=params, timeout=5, headers=headers) as response:
                if response.status == 200:
                    text = await response.text()
                    try:
                        data = json.loads(text)
                    except Exception:
                        # Try to recover from JSONP-like responses such as: callback({...});
                        import re
                        m = re.search(r"\{.*\}", text, re.S)
                        if m:
                            try:
                                data = json.loads(m.group(0))
                            except Exception:
                                raise
                        else:
                            raise
                    results = data.get("results", [])
                    if results:
                        # For albums, use collectionViewUrl; for singles, use trackViewUrl
                        if is_album and "collectionViewUrl" in results[0]:
                            return results[0]["collectionViewUrl"]
                        elif not is_album and "trackViewUrl" in results[0]:
                            return results[0]["trackViewUrl"]
        except Exception as e:
            print(f"Apple Music lookup failed: {e}")
        return None

    async def get_amazon_music_link(self, session, artist, release_name, is_album=True):
        """Fetch Amazon Music link for an album or single using Amazon search page scraping"""
        import urllib.parse
        import re
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MusicUpdaterBot/1.0)"
        }
        # Amazon Music search URL
        query = f"{artist} {release_name}"
        encoded_query = urllib.parse.quote(query)
        if is_album:
            search_url = f"https://music.amazon.com/search/albums/{encoded_query}"
        else:
            search_url = f"https://music.amazon.com/search/songs/{encoded_query}"
        try:
            async with session.get(search_url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    # Try to find the first album/song link in the HTML
                    # Look for /albums/ or /albums/B... or /songs/B... links
                    text = await resp.text()
                    match = re.search(r'"(/albums/[^"]+)"', text)
                    if not match and not is_album:
                        match = re.search(r'"(/songs/[^"]+)"', text)
                    if match:
                        found_link = f"https://music.amazon.com{match.group(1)}"
                        print(f"[AmazonMusic] Found link for '{artist} - {release_name}': {found_link}")
                        return found_link
                    # If not found, just return the search page
                    print(f"[AmazonMusic] No direct album/song link found for '{artist} - {release_name}', returning search page: {search_url}")
                    return search_url
                else:
                    print(f"[AmazonMusic] HTTP error {resp.status} for '{artist} - {release_name}'")
        except Exception as e:
            print(f"Amazon Music lookup failed: {e}")
        print(f"[AmazonMusic] No link found for '{artist} - {release_name}'")
        return None
    """Pagination view for release notifications"""
    
    def __init__(self, albums, singles, *, timeout=300):
        super().__init__(timeout=timeout)
        self.albums = albums
        self.singles = singles
        self.current_page = 0
        
        # Use adaptive page size based on number of releases
        # More releases = smaller pages to prevent character limit issues
        total_releases = len(albums) + len(singles)
        if total_releases > 30:
            self.page_size = 5  # Small pages for many releases
        elif total_releases > 15:
            self.page_size = 7  # Medium pages
        else:
            self.page_size = 10  # Normal pages for few releases
        
        # Calculate pages
        all_releases = albums + singles
        self.total_pages = math.ceil(len(all_releases) / self.page_size) if all_releases else 1
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    async def create_embed(self):
        """Create embed for current page"""
        all_releases = self.albums + self.singles
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        page_releases = all_releases[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"🆕 {len(all_releases)} New Release{'s' if len(all_releases) != 1 else ''}!",
            description=f"Page {self.current_page + 1} of {self.total_pages}",
            color=0x1DB954,
            timestamp=datetime.now()
        )
        
        # Group page releases by type
        page_albums = [r for r in page_releases if r['type'] == 'album']
        page_singles = [r for r in page_releases if r['type'] == 'single']
        
        # Use our global function for YouTube links (will be more consistent)
        async def get_release_youtube_link(artist, track_name):
            """Get YouTube link with detailed logging for releases page"""
            print(f"🎵 Getting YouTube link for release page: {artist} - {track_name}")
            return await get_youtube_music_topic_url(artist, track_name)
            
        # Helper function to create release line with smart truncation
        async def create_release_line(session, release_info, max_length=80):
            artist = release_info['artist']
            release = release_info['release']
            spotify_link = release.get('external_urls', {}).get('spotify', '')
            youtube_music_link = await get_release_youtube_link(artist, release['name'])
            is_album = release_info['type'] == 'album'
            apple_music_link = await self.get_apple_music_link(session, artist, release['name'], is_album=is_album)
            # Smart truncation based on available space
            artist_name = artist[:25] + "..." if len(artist) > 25 else artist
            # Calculate remaining space for release name
            base_length = len(f"• **{artist_name}** - [] ({release['release_date']})")
            remaining_space = max_length - base_length
            release_name = release['name'][:max(10, remaining_space-5)] + "..." if len(release['name']) > remaining_space else release['name']
            # Create links list
            links = []
            if spotify_link:
                links.append(f"[Spotify]({spotify_link})")
            if youtube_music_link:
                links.append(f"[YouTube]({youtube_music_link})")
            if apple_music_link:
                links.append(f"[Apple Music]({apple_music_link})")
            if links:
                links_str = " | ".join(links)
                return f"• **{artist_name}** - {release_name} ({release['release_date']}) {links_str}"
            else:
                return f"• **{artist_name}** - {release_name} ({release['release_date']})"
        
        # Add albums for this page, splitting into multiple fields/messages if needed
        if page_albums:
            max_field_length = 1024
            album_chunks = []
            chunk = []
            current_length = 0
            async with aiohttp.ClientSession() as session:
                for album in page_albums:
                    line = await create_release_line(session, album)
                    if current_length + len(line) + 1 > max_field_length:
                        album_chunks.append(chunk)
                        chunk = []
                        current_length = 0
                    chunk.append(line)
                    current_length += len(line) + 1
            if chunk:
                album_chunks.append(chunk)
            for idx, chunk in enumerate(album_chunks):
                embed.add_field(
                    name=f"💿 Albums on this page ({len(chunk)})" + (f" (Part {idx+1})" if len(album_chunks) > 1 else ""),
                    value='\n'.join(chunk),
                    inline=False
                )

        # Add singles for this page, splitting into multiple fields/messages if needed
        if page_singles:
            max_field_length = 1024
            single_chunks = []
            chunk = []
            current_length = 0
            async with aiohttp.ClientSession() as session:
                for single in page_singles:
                    line = await create_release_line(session, single)
                    if current_length + len(line) + 1 > max_field_length:
                        single_chunks.append(chunk)
                        chunk = []
                        current_length = 0
                    chunk.append(line)
                    current_length += len(line) + 1
            if chunk:
                single_chunks.append(chunk)
            for idx, chunk in enumerate(single_chunks):
                embed.add_field(
                    name=f"🎵 Singles on this page ({len(chunk)})" + (f" (Part {idx+1})" if len(single_chunks) > 1 else ""),
                    value='\n'.join(chunk),
                    inline=False
                )
        
        # Add summary (keep this short)
        embed.add_field(
            name="📊 Total Summary",
            value=f"Albums: {len(self.albums)} • Singles: {len(self.singles)}",
            inline=True
        )
        
        embed.set_footer(text="Music Updater Bot")
        return embed
    
    @discord.ui.button(label='◀️ Previous', style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=await self.create_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label='▶️ Next', style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=await self.create_embed(), view=self)
        else:
            await interaction.response.defer()

class ArtistPaginationView(discord.ui.View):
    """Pagination view for artist list"""
    
    def __init__(self, artists, *, timeout=300):
        super().__init__(timeout=timeout)
        self.artists = artists
        self.current_page = 0
        
        # Calculate pages (10 artists per page)
        self.total_pages = math.ceil(len(artists) / 10) if artists else 1
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    async def create_embed(self):
        """Create embed for current page"""
        start_idx = self.current_page * 10
        end_idx = start_idx + 10
        page_artists = self.artists[start_idx:end_idx]
        
        embed = discord.Embed(
            title="🎵 Tracked Artists",
            description=f"Page {self.current_page + 1} of {self.total_pages} • Total: **{len(self.artists)}** artists",
            color=0x1DB954
        )
        
        for i, artist in enumerate(page_artists, 1):
            global_index = start_idx + i
            value = ""
            if artist.get('spotify_data'):
                followers = artist['spotify_data']['followers']
                value += f"👥 {followers:,} followers\n"
                if artist['spotify_data']['genres']:
                    value += f"🎸 {', '.join(artist['spotify_data']['genres'][:2])}\n"
            
            if artist.get('latest_single'):
                value += f"🎵 Latest: {artist['latest_single']['name']} ({artist['latest_single']['release_date']})"
            elif artist.get('latest_album'):
                value += f"💿 Latest: {artist['latest_album']['name']} ({artist['latest_album']['release_date']})"
            
            embed.add_field(
                name=f"{global_index}. {artist['name']}", 
                value=value or "No recent releases", 
                inline=True
            )
        
        embed.set_footer(text=f"Use `/music add` to add more artists • Page {self.current_page + 1}/{self.total_pages}")
        return embed
    
    @discord.ui.button(label='◀️ Previous', style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=await self.create_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label='▶️ Next', style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=await self.create_embed(), view=self)
        else:
            await interaction.response.defer()

class ConcertsPaginationView(discord.ui.View):
    """Pagination view for concerts locations"""

    def __init__(self, locations, *, title="🎟️ Upcoming Concerts", days_ahead: int = 180, states: Optional[str] = None, timeout=300):
        super().__init__(timeout=timeout)
        self.locations = locations  # list of [((city,state,date), events)]
        self.current_page = 0
        self.page_size = 10  # locations per page
        self.title = title
        self.days_ahead = days_ahead
        self.states = states
        self.total_pages = math.ceil(len(locations) / self.page_size) if locations else 1
        self.update_buttons()

    def update_buttons(self):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1

    async def create_embed(self):
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        page_locations = self.locations[start_idx:end_idx]

        timestamp = datetime.now(tz=get_eastern_tz() or ZoneInfo("UTC"))
        embed = discord.Embed(
            title=self.title,
            description=f"States: {self.states or 'All'} • Window: {self.days_ahead} days\nPage {self.current_page + 1} of {self.total_pages}",
            color=0x1DB954,
            timestamp=timestamp
        )

        max_events_per_location = 3
        for (city, state_name, date), events in page_locations:
            lines = []
            for event_name, url, stubhub_url, artists_list in events[:max_events_per_location]:
                artist_str = ", ".join(artists_list)
                links = []
                if url:
                    links.append(f"[Ticketmaster]({url})")
                if stubhub_url:
                    links.append(f"[StubHub]({stubhub_url})")
                links_str = " • ".join(links) if links else "No link available"
                premium_tag = " • Premium" if "premium" in (event_name or "").lower() else ""
                lines.append(f"**{event_name}**{premium_tag} — {artist_str}\n{links_str}")
            field_value = "\n\n".join(lines) if lines else "No details available"
            # Safe field name
            field_name = f"{city}, {state_name} — {date}".strip()
            if not (city or state_name):
                field_name = f"Unknown location — {date}"
            embed.add_field(name=field_name, value=field_value, inline=False)

        total_events = sum(len(ev) for _, ev in self.locations)
        embed.set_footer(text=f"Found {total_events} events across {len(self.locations)} locations • States: {self.states or 'All'}")
        return embed

    @discord.ui.button(label='◀️ Previous', style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=await self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label='▶️ Next', style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=await self.create_embed(), view=self)
        else:
            await interaction.response.defer()


class MusicBot(commands.Bot):
    def __init__(self):
        # Set up bot intents - only use basic intents to avoid privileged intent requirements
        intents = discord.Intents.default()
        intents.message_content = False  # We don't need message content for slash commands
        
        super().__init__(command_prefix='!', intents=intents)
        
        # Initialize components
        self.spotify = SpotifyAPI()
        self.data_manager = DataManager()
        self.notification_channels = []  # Support multiple notification channels
        self.artists = []
        self.setup_tasks()
    
    async def get_latest_by_type_with_retries(
        self,
        artist_id: str,
        retries: int = 3,
        backoff: float = 1.0,
        timeout: float = 15.0,
    ):
        """Call SpotifyAPI.get_latest_by_type in a thread executor with retries on transient errors."""
        loop = asyncio.get_running_loop()
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                # Run the possibly-blocking spotify call in the default executor with an overall timeout
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, self.spotify.get_latest_by_type, artist_id),
                    timeout=timeout,
                )
                return result
            except asyncio.TimeoutError as e:
                last_exc = e
                print(
                    f"⏱️ Spotify request for artist ID '{artist_id}' timed out (attempt {attempt}/{retries}, {timeout:.0f}s limit)"
                )
            except (requests.exceptions.RequestException, ConnectionResetError, OSError) as e:
                last_exc = e
                print(f"❌ Error getting albums for artist ID '{artist_id}' (attempt {attempt}/{retries}): {e}")
                if attempt < retries:
                    sleep_time = backoff * (2 ** (attempt - 1))
                    print(f"ℹ️ Retrying in {sleep_time:.1f}s...")
                    await asyncio.sleep(sleep_time)
                else:
                    print(f"❌ Exhausted retries for artist ID '{artist_id}'")
                continue
            if attempt < retries:
                sleep_time = backoff * (2 ** (attempt - 1))
                print(f"ℹ️ Retrying in {sleep_time:.1f}s...")
                await asyncio.sleep(sleep_time)
            else:
                print(f"❌ Exhausted retries for artist ID '{artist_id}'")
        # Re-raise the last exception so caller can handle/log it
        if last_exc:
            raise last_exc
        return None

    def setup_tasks(self):
        """Set up scheduled tasks for checking releases"""
        # Define Eastern Time zone with safe fallback
        eastern = get_eastern_tz() or ZoneInfo("UTC")
        
        release_times = [time(9, 0, tzinfo=eastern), time(18, 0, tzinfo=eastern)]

        @tasks.loop(time=release_times)
        async def check_releases_scheduled():
            await self.check_and_notify_releases()
        
        # Schedule weekly summary (and concerts) to run exactly at 12:05 AM Eastern Time every Friday
        @tasks.loop(time=[time(0, 5, tzinfo=eastern)])
        async def weekly_summary_task():
            now_eastern = datetime.now(tz=eastern)
            # Only run if it's Friday (weekday() == 4)
            if now_eastern.weekday() == 4:
                print(f"📅 Running weekly summary + concerts for Friday at 12:05 AM... (EST time: {now_eastern.strftime('%Y-%m-%d %H:%M:%S')})")
                concerts_locations = None
                concerts_new_ids = None
                concerts_result = await self.check_and_notify_concerts(schedule_label="Weekly check", return_data=True)
                if concerts_result:
                    concerts_locations = concerts_result[0]
                    concerts_new_ids = concerts_result[1] if len(concerts_result) > 1 else None
                await self.send_weekly_summary(
                    concerts_locations=concerts_locations,
                    concerts_new_ids_by_artist=concerts_new_ids,
                )

        self.check_releases_task = check_releases_scheduled
        self.weekly_summary_task = weekly_summary_task

    async def load_data(self):
        """Load artist data and bot settings asynchronously"""
        self.artists = await self.data_manager.load_artists()
        # Ensure concerts tracking field exists for all artists
        added_concert_field = False
        for artist in self.artists:
            if "notified_concert_ids" not in artist:
                artist["notified_concert_ids"] = []
                added_concert_field = True
        if added_concert_field:
            await self.save_data()
        bot_settings = await self.data_manager.load_bot_settings()
        if isinstance(bot_settings, dict):
            self.notification_channels = bot_settings.get('notification_channels', [])
        else:
            self.notification_channels = []
        if config.DISCORD_CHANNEL_ID and not self.notification_channels:
            try:
                channel_id = int(config.DISCORD_CHANNEL_ID)
                self.notification_channels = [channel_id]
                await self.save_bot_settings()
            except ValueError:
                print("⚠️  Invalid Discord channel ID in config")
        print(f"📋 Loaded {len(self.notification_channels)} notification channels")

    async def save_data(self):
        """Save artist data asynchronously"""
        return await self.data_manager.save_artists(self.artists)

    async def save_bot_settings(self):
        """Save bot settings (notification channels, etc.) asynchronously"""
        settings = {
            'notification_channels': self.notification_channels,
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return await self.data_manager.save_bot_settings(settings)

    def get_seen_concert_ids_by_artist(self):
        """Return a mapping of artist name -> set of notified Ticketmaster event IDs."""
        mapping = {}
        for artist in self.artists:
            name = artist.get("name")
            if not name:
                continue
            existing = artist.get("notified_concert_ids") or []
            mapping[name.lower()] = set(existing)
        return mapping

    async def record_seen_concert_ids(self, new_event_ids_by_artist):
        """Persist newly notified concert IDs to artists_data.json to avoid repeats."""
        if not new_event_ids_by_artist:
            return
        updated = False
        max_keep = 300  # cap stored IDs per artist to keep file small
        for artist in self.artists:
            name = artist.get("name")
            if not name:
                continue
            key = name.lower()
            ids_for_artist = new_event_ids_by_artist.get(key)
            if ids_for_artist:
                existing = list(dict.fromkeys(artist.get("notified_concert_ids", [])))
                # Append new IDs while preserving order
                for event_id in ids_for_artist:
                    if event_id not in existing:
                        existing.append(event_id)
                if len(existing) > max_keep:
                    existing = existing[-max_keep:]
                artist["notified_concert_ids"] = existing
                updated = True
        if updated:
            await self.save_data()

    async def add_notification_channel_async(self, channel_id: int):
        """Add a channel to receive automatic notifications asynchronously"""
        if channel_id not in self.notification_channels:
            self.notification_channels.append(channel_id)
            await self.save_bot_settings()
            print(f"✅ Added notification channel: {channel_id}")
            return True
        return False

    async def remove_notification_channel_async(self, channel_id: int):
        """Remove a channel from automatic notifications asynchronously"""
        if channel_id in self.notification_channels:
            self.notification_channels.remove(channel_id)
            await self.save_bot_settings()
            print(f"✅ Removed notification channel: {channel_id}")
            return True
        return False

    async def setup_hook(self):
        await self.load_data()
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"❌ Failed to sync slash commands: {e}")

    async def on_ready(self):
        print(f'🤖 {self.user} is online and ready!')
        print(f'📊 Tracking {len(self.artists)} artists')
        if hasattr(self, 'check_releases_task') and not self.check_releases_task.is_running():
            self.check_releases_task.start()
            print('🔄 PRODUCTION MODE: Release checks twice daily (9 AM & 6 PM Eastern)')
        if hasattr(self, 'weekly_summary_task') and not self.weekly_summary_task.is_running():
            self.weekly_summary_task.start()
            print('📅 Weekly summary task started (Fridays at 12:05 AM EST)')
        
        # Send startup message if channels are configured
        if self.notification_channels:
            startup_embed = discord.Embed(
                title="🎵 Music Updater Bot Online!",
                description=f"Now tracking **{len(self.artists)}** artists for new releases.",
                color=0x1DB954  # Spotify green
            )
            startup_embed.add_field(
                name="📅 Schedule", 
                value="Releases: twice daily (9 AM & 6 PM)\nConcerts: weekly with Friday summary (12:05 AM)", 
                inline=False
            )
            startup_embed.add_field(
                name="🗓️ Weekly Summary", 
                value="Every Friday at 12:05 AM - weekly release roundup", 
                inline=False
            )
            startup_embed.add_field(
                name="🎯 Commands", 
                value="Use `/music help` to see all commands", 
                inline=False
            )
            
            # Send to all configured notification channels
            for channel_id in self.notification_channels:
                channel = self.get_channel(channel_id)
                # Only send to TextChannel or Thread (not Category, Forum, or Private channels)
                if isinstance(channel, (discord.TextChannel, discord.Thread)):
                    try:
                        await channel.send(embed=startup_embed)
                    except Exception as e:
                        print(f"⚠️  Could not send startup message to channel {channel_id}: {e}")
    
    async def check_and_notify_releases(self):
        """Check for new releases and send notifications"""
        if not self.spotify.is_available():
            print("❌ Spotify API not available - skipping release check")
            return
        
        if not self.notification_channels:
            print("ℹ️  No notification channels configured - releases will only show in slash command responses")
        
        print(f"🔍 Checking releases for {len(self.artists)} artists...")
        new_releases = []
        
        for artist in self.artists:
            if not artist.get('spotify_data'):
                continue  # Skip offline artists
            
            try:
                # Get latest releases by type (use retry wrapper to handle transient network errors)
                releases_by_type = await self.get_latest_by_type_with_retries(artist['spotify_data']['id'])
                
                # FIX: Check if the API call was successful before proceeding
                if not releases_by_type:
                    print(f"⚠️ Could not fetch releases for {artist['name']} after retries. Skipping.")
                    continue

                latest_album = releases_by_type.get('latest_album')
                latest_single = releases_by_type.get('latest_single')
                
                # PRODUCTION MODE: Check for actual new releases
                # Check for new album
                if latest_album and (not artist.get('latest_album') or 
                    latest_album['release_date'] > artist['latest_album']['release_date']):
                    new_releases.append({
                        'artist': artist['name'],
                        'type': 'album',
                        'release': latest_album,
                        'artist_data': artist
                    })
                    artist['latest_album'] = latest_album
                
                # Check for new single
                if latest_single and (not artist.get('latest_single') or 
                    latest_single['release_date'] > artist['latest_single']['release_date']):
                    new_releases.append({
                        'artist': artist['name'],
                        'type': 'single',
                        'release': latest_single,
                        'artist_data': artist
                    })
                    artist['latest_single'] = latest_single
                
                artist['last_checked'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                
            except Exception as e:
                print(f"❌ Error checking {artist['name']}: {e}")
        
        # Save data if we found new releases
        if new_releases:
            await self.save_data()
            
            # Send consolidated notification to all configured channels
            if self.notification_channels:
                await self.send_consolidated_release_notifications(new_releases)
            
            print(f"✅ Found {len(new_releases)} new releases")
        else:
            print("ℹ️  No new releases found")
    
    async def send_consolidated_release_notifications(self, new_releases):
        """Send a paginated consolidated notification for all new releases"""
        if not new_releases:
            return
        
        # Group releases by type for better organization
        albums = [r for r in new_releases if r['type'] == 'album']
        singles = [r for r in new_releases if r['type'] == 'single']
        
        # Send to all notification channels
        for channel_id in self.notification_channels:
            channel = self.get_channel(channel_id)
            # Only send to TextChannel or Thread (not Category, Forum, or Private channels)
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    # Create pagination view
                    view = ReleasePaginationView(albums, singles)
                    embed = await view.create_embed()
                    
                    # Only show pagination buttons if there are multiple pages
                    if view.total_pages > 1:
                        await channel.send(embed=embed, view=view)
                    else:
                        await channel.send(embed=embed)
                        
                except Exception as e:
                    print(f"⚠️  Could not send notification to channel {channel_id}: {e}")
                    
                    # If it still fails, send a simplified message
                    try:
                        simple_embed = discord.Embed(
                            title=f"🆕 {len(new_releases)} New Releases!",
                            description=f"Found {len(albums)} albums and {len(singles)} singles from your tracked artists.\n\nUse `/music list` to see details.",
                            color=0x1DB954,
                            timestamp=datetime.now()
                        )
                        simple_embed.set_footer(text="Music Updater Bot")
                        await channel.send(embed=simple_embed)
                        print(f"✅ Sent simplified notification to channel {channel_id}")
                    except Exception as e2:
                        print(f"❌ Failed to send even simplified notification to channel {channel_id}: {e2}")

    async def collect_concert_events(
        self,
        states: str = "NH,MA,RI,CT",
        max_events: int = 5,
        days_ahead: int = 180,
        artists: Optional[list] = None,
        seen_event_ids_by_artist: Optional[dict] = None,
        return_event_ids: bool = False,
    ):
        """Collect upcoming concerts for artists.
        
        If ``artists`` is None, uses ``self.artists`` (loaded from ``artists_data.json`` via DataManager).
        If ``seen_event_ids_by_artist`` is provided, skips events already notified for that artist (by Ticketmaster event ID).
        When ``return_event_ids`` is True, returns a tuple of (locations, new_event_ids_by_artist).
        Returns a list of ``[((city, state, date), [(event_name, url, stubhub_url, artists_list), ...])...]``
        sorted by date, state, city.
        """
        api_key = getattr(config, "TICKETMASTER_API_KEY", None) or os.environ.get("TICKETMASTER_API_KEY")
        if not api_key:
            print("❌ Ticketmaster API key not configured - skipping concerts collection")
            return []
        target_artists = artists if artists is not None else self.artists
        if not target_artists:
            print("ℹ️ No tracked artists loaded - skipping concerts collection")
            return []

        from collections import defaultdict
        import urllib.parse

        base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
        location_events = defaultdict(list)  # {(city, state, date): [ (event_name, url, stubhub, [artists]) ]}
        seen_event_ids = set()
        seen_map = {k: set(v) for k, v in (seen_event_ids_by_artist or {}).items()}
        new_event_ids_by_artist = defaultdict(set) if return_event_ids else None
        today = datetime.now(tz=get_eastern_tz() or ZoneInfo("UTC")).date()
        latest_date = today + timedelta(days=days_ahead)

        async with aiohttp.ClientSession() as session:
            # Prepare state codes list (iterate per code for Ticketmaster compatibility)
            state_codes = [s.strip() for s in str(states).split(",") if s.strip()] if states else [None]

            # Build query list
            queries = []
            for artist in target_artists:
                name = artist.get("name")
                if not name:
                    continue
                for st in state_codes:
                    queries.append((name, st))

            # Limit concurrency to avoid rate limits
            sem = asyncio.Semaphore(3)  # Reduced from 8 to 3

            async def fetch_one(name: str, st_code: Optional[str]):
                params = {
                    "apikey": api_key,
                    "keyword": name,
                    "countryCode": "US",
                    "size": max_events,
                }
                if st_code:
                    params["stateCode"] = st_code
                
                # Retry with exponential backoff on rate limit
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        async with sem:
                            # Add small delay between requests to avoid rate limiting
                            await asyncio.sleep(0.25)
                            async with session.get(base_url, params=params, timeout=10) as resp:
                                status = resp.status
                                
                                # Handle rate limiting
                                if status == 429:
                                    retry_after = int(resp.headers.get('Retry-After', 2))
                                    print(f"⚠️ Rate limited for '{name}' - waiting {retry_after}s (attempt {attempt+1}/{max_retries})")
                                    if attempt < max_retries - 1:
                                        await asyncio.sleep(retry_after)
                                        continue
                                    return name, st_code, None
                                
                                if status != 200:
                                    print(f"⚠️ Concert lookup HTTP {status} for '{name}' (state={st_code or 'ALL'})")
                                    return name, st_code, None
                                
                                data = await resp.json()
                                raw_events = data.get("_embedded", {}).get("events", [])
                                print(f"🎟️ Ticketmaster: '{name}' in {st_code or 'ALL'} — {len(raw_events)} raw events")
                                return name, st_code, data
                    except Exception as e:
                        print(f"⚠️ Concert lookup failed for '{name}' (state={st_code or 'ALL'}): {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        return name, st_code, None
                return name, st_code, None

            results = await asyncio.gather(*(fetch_one(n, s) for (n, s) in queries), return_exceptions=False)

            # Process all results
            for name, st_code, data in results:
                if not data:
                    continue
                events = data.get("_embedded", {}).get("events", [])
                for event in events:
                    event_id = event.get("id")
                    artist_key = (name or "").lower()
                    # Fallback ID to ensure we can persist seen events even if Ticketmaster omits event IDs
                    fallback_id = event_id or f"{artist_key}|{event.get('name','unknown')}|{date_str}|{city}|{state_name}"
                    if fallback_id:
                        if fallback_id in seen_event_ids:
                            continue
                        if seen_map and artist_key in seen_map and fallback_id in seen_map[artist_key]:
                            continue
                    event_name = event.get("name", "Unknown Event")
                    dates = event.get("dates", {}).get("start", {})
                    date_str = dates.get("localDate") or dates.get("dateTime") or "?"
                    try:
                        event_date = datetime.fromisoformat(date_str).date() if date_str not in (None, "?") else None
                    except Exception:
                        event_date = None
                    if event_date and (event_date < today or event_date > latest_date):
                        continue

                    venue = event.get("_embedded", {}).get("venues", [{}])[0]
                    city = venue.get("city", {}).get("name", "")
                    state_name = venue.get("state", {}).get("name", "")
                    url = event.get("url", "")

                    # Build artists list; accept all events returned by keyword search
                    artists_list = []
                    if "_embedded" in event and "attractions" in event["_embedded"]:
                        for attr in event["_embedded"].get("attractions", []):
                            nm = attr.get("name")
                            if nm:
                                artists_list.append(nm)
                    if not artists_list:
                        # Fallback: show the queried artist name if attractions missing
                        artists_list = [name]

                    stubhub_url = f"https://www.stubhub.com/find/s/?q={urllib.parse.quote_plus(event_name)}"
                    key = (city, state_name, date_str or "?")
                    location_events[key].append((event_name, url, stubhub_url, artists_list))
                    if fallback_id:
                        seen_event_ids.add(fallback_id)
                        if new_event_ids_by_artist is not None:
                            new_event_ids_by_artist[artist_key].add(fallback_id)

        locations = sorted(location_events.items(), key=lambda x: (x[0][2], x[0][1], x[0][0]))
        total_events = sum(len(ev) for _, ev in locations)
        print(f"✅ Concerts aggregation complete — {total_events} events across {len(locations)} locations")
        if return_event_ids:
            return locations, {k: set(v) for k, v in (new_event_ids_by_artist or {}).items()}
        return locations

    async def collect_concert_events_raw(self, states: str = "NH,MA,RI,CT", max_events: int = 10, days_ahead: int = 365, artists: Optional[list] = None):
        """Collect raw Ticketmaster events for artists without filtering by attractions/keywords.
        Returns a flat list of dicts with keys: event_name, date, city, state, url, artists, premium.
        """
        api_key = getattr(config, "TICKETMASTER_API_KEY", None) or os.environ.get("TICKETMASTER_API_KEY")
        if not api_key:
            return []
        target_artists = artists if artists is not None else self.artists
        if not target_artists:
            return []

        results = []
        today = datetime.now(tz=get_eastern_tz() or ZoneInfo("UTC")).date()
        latest_date = today + timedelta(days=days_ahead)

        async with aiohttp.ClientSession() as session:
            state_codes = [s.strip() for s in str(states).split(",") if s.strip()] if states else [None]

            sem = asyncio.Semaphore(3)  # Reduced from 8 to 3
            base_url = "https://app.ticketmaster.com/discovery/v2/events.json"

            async def fetch_raw(name: str, st_code: Optional[str]):
                params = {
                    "apikey": api_key,
                    "keyword": name,
                    "countryCode": "US",
                    "size": max_events,
                }
                if st_code:
                    params["stateCode"] = st_code
                
                # Retry with exponential backoff on rate limit
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        async with sem:
                            # Add small delay between requests
                            await asyncio.sleep(0.25)
                            async with session.get(base_url, params=params, timeout=10) as resp:
                                # Handle rate limiting
                                if resp.status == 429:
                                    retry_after = int(resp.headers.get('Retry-After', 2))
                                    print(f"⚠️ Rate limited for '{name}' - waiting {retry_after}s")
                                    if attempt < max_retries - 1:
                                        await asyncio.sleep(retry_after)
                                        continue
                                    return []
                                
                                if resp.status != 200:
                                    return []
                                data = await resp.json()
                                events = data.get("_embedded", {}).get("events", [])
                                out = []
                                for event in events:
                                    event_name = event.get("name", "Unknown Event")
                                    dates = event.get("dates", {}).get("start", {})
                                    date_str = dates.get("localDate") or dates.get("dateTime") or "?"
                                    try:
                                        event_date = datetime.fromisoformat(date_str).date() if date_str not in (None, "?") else None
                                    except Exception:
                                        event_date = None
                                    if event_date and (event_date < today or event_date > latest_date):
                                        continue
                                    venue = event.get("_embedded", {}).get("venues", [{}])[0]
                                    city = venue.get("city", {}).get("name", "")
                                    state_name = venue.get("state", {}).get("name", "")
                                    url = event.get("url", "")
                                    artists_list = []
                                    if "_embedded" in event and "attractions" in event["_embedded"]:
                                        for attr in event["_embedded"].get("attractions", []):
                                            nm = attr.get("name")
                                            if nm:
                                                artists_list.append(nm)
                                    out.append({
                                        "event_name": event_name,
                                        "date": date_str or "?",
                                        "city": city,
                                        "state": state_name,
                                        "url": url,
                                        "artists": artists_list,
                                        "premium": ("premium" in (event_name or "").lower()),
                                    })
                                return out
                    except Exception:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        return []
                return []            # Build queries and fetch concurrently
            queries = []
            for artist in target_artists:
                name = artist.get("name")
                if not name:
                    continue
                for st in state_codes:
                    queries.append((name, st))
            raw_lists = await asyncio.gather(*(fetch_raw(n, s) for (n, s) in queries), return_exceptions=False)
            for chunk in raw_lists:
                results.extend(chunk)
        return results

    async def check_and_notify_concerts(
        self,
        states: str = "NH,MA,RI,CT",
        max_events: int = 5,
        *,
        schedule_label: str = "Weekly check",
        return_data: bool = False,
    ):
        """Fetch upcoming concerts for tracked artists and notify configured channels.

        Filters out concerts already notified (stored in ``artists_data.json``) and optionally returns the
        locations plus the new event IDs that were recorded.
        """
        skip_send = False
        if not self.notification_channels:
            skip_send = True
            print("ℹ️ No notification channels configured - will collect concerts but skip sending")

        seen_map = self.get_seen_concert_ids_by_artist()
        result = await self.collect_concert_events(
            states=states,
            max_events=max_events,
            days_ahead=30,  # keep scheduled notifications scoped to 30 days to avoid flooding
            seen_event_ids_by_artist=seen_map,
            return_event_ids=True,
        )

        locations: list = []
        new_event_ids_by_artist: dict = {}
        if isinstance(result, tuple):
            locations, new_event_ids_by_artist = result
        else:
            locations = result

        if not locations:
            print("ℹ️ Concerts check: no events found")
            return (locations, new_event_ids_by_artist) if return_data else None

        max_locations = 10
        max_events_per_location = 3
        timestamp = datetime.now(tz=get_eastern_tz() or ZoneInfo("UTC"))

        if not skip_send:
            for channel_id in self.notification_channels:
                channel = self.get_channel(channel_id)
                if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                    continue
                try:
                    embed = discord.Embed(
                        title="🎟️ Upcoming Concerts",
                        description=f"{schedule_label} • States: {states or 'All'}",
                        color=0x1DB954,
                        timestamp=timestamp
                    )

                    for (city, state_name, date), events in locations[:max_locations]:
                        lines = []
                        for event_name, url, stubhub_url, artists_list in events[:max_events_per_location]:
                            artist_str = ", ".join(artists_list)
                            links = []
                            if url:
                                links.append(f"[Ticketmaster]({url})")
                            if stubhub_url:
                                links.append(f"[StubHub]({stubhub_url})")
                            links_str = " • ".join(links) if links else "No link available"
                            premium_tag = " • Premium" if "premium" in event_name.lower() else ""
                            lines.append(f"**{event_name}**{premium_tag} — {artist_str}\n{links_str}")
                        field_value = "\n\n".join(lines) if lines else "No details available"
                        embed.add_field(name=f"{city}, {state_name} — {date}", value=field_value, inline=False)

                    if len(locations) > max_locations:
                        embed.set_footer(text=f"Showing first {max_locations} locations out of {len(locations)}")

                    await channel.send(embed=embed)
                    print(f"✅ Sent concerts update to channel {channel_id}")
                except Exception as e:
                    print(f"⚠️ Could not send concerts update to channel {channel_id}: {e}")

        # Persist newly seen concerts so we skip them on the next weekly run
        await self.record_seen_concert_ids(new_event_ids_by_artist)

        if return_data:
            return locations, new_event_ids_by_artist

    async def send_weekly_summary(self, concerts_locations=None, concerts_new_ids_by_artist=None):
        """Send a weekly summary of all releases from the past week.

        Optionally pass ``concerts_locations`` (and ``concerts_new_ids_by_artist``) to reuse already-fetched
        concerts data from the weekly concerts check.
        """
        if not self.spotify.is_available():
            print("❌ Spotify API not available - skipping weekly summary")
            return
        
        if not self.notification_channels:
            print("ℹ️  No notification channels configured - skipping weekly summary")
            return
        
        print("📅 Generating weekly summary...")
        
        # Calculate date range for the past week (Saturday to Friday, 6 days back)
        today = datetime.now().date()
        # Find the most recent Friday (including today if it's Friday)
        days_since_friday = (today.weekday() - 4) % 7
        this_friday = today - timedelta(days=days_since_friday)
        # Go back 6 days to get the previous Saturday
        last_saturday = this_friday - timedelta(days=6)

        week_start = last_saturday
        week_end = this_friday

        week_start_str = week_start.strftime("%Y-%m-%d")
        week_end_str = week_end.strftime("%Y-%m-%d")

        print(f"📅 Collecting releases from {week_start_str} to {week_end_str}")
        
        weekly_releases = []
        
        for artist in self.artists:
            if not artist.get('spotify_data'):
                continue  # Skip offline artists
            
            try:
                # Get all albums and singles for this artist
                releases_by_type = await self.get_latest_by_type_with_retries(artist['spotify_data']['id'])
                
                # FIX: Check if the API call was successful before proceeding
                if not releases_by_type:
                    continue

                # Check albums released this week
                latest_week_album = releases_by_type.get('latest_album')
                if latest_week_album:
                    album_date = latest_week_album['release_date']
                    if week_start_str <= album_date <= week_end_str:
                        weekly_releases.append({
                            'artist': artist['name'],
                            'type': 'album',
                            'release': latest_week_album,
                            'artist_data': artist
                        })
                
                # Check singles released this week
                latest_week_single = releases_by_type.get('latest_single')
                if latest_week_single:
                    single_date = latest_week_single['release_date']
                    if week_start_str <= single_date <= week_end_str:
                        weekly_releases.append({
                            'artist': artist['name'],
                            'type': 'single',
                            'release': latest_week_single,
                            'artist_data': artist
                        })
                        
            except Exception as e:
                print(f"❌ Error checking weekly releases for {artist['name']}: {e}")
        
        # Collect concerts for the summary (upcoming within next 30 days), skipping already-notified events
        local_new_ids = concerts_new_ids_by_artist or {}
        if concerts_locations is None:
            seen_map = self.get_seen_concert_ids_by_artist()
            result = await self.collect_concert_events(days_ahead=30, seen_event_ids_by_artist=seen_map, return_event_ids=True)
            if isinstance(result, tuple):
                concerts_locations, local_new_ids = result
            else:
                concerts_locations = result

        # Send weekly summary to all notification channels
        if weekly_releases:
            await self.send_weekly_summary_notifications(weekly_releases, week_start, week_end, concerts_locations=concerts_locations)
            print(f"✅ Weekly summary sent: {len(weekly_releases)} releases")
        elif concerts_locations:
            # If no releases but concerts exist, send a concerts-only summary
            await self.send_weekly_summary_notifications([], week_start, week_end, concerts_locations=concerts_locations)
            print("ℹ️  Weekly summary sent with concerts only")
        else:
            # Send a "no releases" summary
            await self.send_no_releases_summary(week_start, week_end)
            print("ℹ️  Weekly summary sent: no new releases or concerts")

        # Persist newly seen concerts to avoid repeats on the next weekly run
        if local_new_ids:
            await self.record_seen_concert_ids(local_new_ids)

    async def send_weekly_summary_notifications(self, weekly_releases, week_start, week_end, concerts_locations=None):
        """Send formatted weekly summary notifications, splitting into multiple embeds if needed."""
        albums = [r for r in weekly_releases if r['type'] == 'album']
        singles = [r for r in weekly_releases if r['type'] == 'single']

        class WeeklySummaryView(ReleasePaginationView):
            async def create_embed(self):
                embed = await super().create_embed()
                week_start_formatted = week_start.strftime("%B %d")
                week_end_formatted = week_end.strftime("%B %d, %Y")
                embed.title = f"🗓️ Weekly Release Summary"
                embed.description = f"**{week_start_formatted} - {week_end_formatted}**\nPage {self.current_page + 1} of {self.total_pages}"
                embed.color = 0x9932CC
                embed.set_footer(text="Music Updater Bot • Weekly Summary")
                return embed

        async def split_embeds(view):
            embeds = []
            for page in range(view.total_pages):
                view.current_page = page
                embed = await view.create_embed()
                # Split fields into smaller chunks if any field is too long
                new_fields = []
                for field in embed.fields:
                    if len(field.value) > 1024:
                        lines = field.value.split('\n')
                        chunk = []
                        chunk_len = 0
                        part = 1
                        for line in lines:
                            if chunk_len + len(line) + 1 > 1024:
                                # Add part number to name if splitting
                                name = f"{field.name} (Part {part})" if part > 1 or len(lines) > 1 else field.name
                                new_fields.append({'name': name, 'value': '\n'.join(chunk), 'inline': field.inline})
                                chunk = []
                                chunk_len = 0
                                part += 1
                            chunk.append(line)
                            chunk_len += len(line) + 1
                        if chunk:
                            name = f"{field.name} (Part {part})" if part > 1 or len(lines) > 1 else field.name
                            new_fields.append({'name': name, 'value': '\n'.join(chunk), 'inline': field.inline})
                    else:
                        new_fields.append({'name': field.name, 'value': field.value, 'inline': field.inline})
                # Now, build embeds from new_fields, keeping under 6000 chars
                temp_embed = None
                temp_len = 0
                for nf in new_fields:
                    if temp_embed is None:
                        temp_embed = await view.create_embed()
                        temp_embed.clear_fields()
                        temp_len = len(temp_embed.description or '') + len(temp_embed.title or '')
                    field_len = len(nf['name']) + len(nf['value'])
                    if temp_len + field_len > 5900 or len(temp_embed.fields) >= 25:
                        embeds.append(temp_embed)
                        temp_embed = await view.create_embed()
                        temp_embed.clear_fields()
                        temp_len = len(temp_embed.description or '') + len(temp_embed.title or '')
                    temp_embed.add_field(name=nf['name'], value=nf['value'], inline=nf['inline'])
                    temp_len += field_len
                if temp_embed and len(temp_embed.fields) > 0:
                    embeds.append(temp_embed)
            return embeds

        for channel_id in self.notification_channels:
            channel = self.get_channel(channel_id)
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    embeds = []
                    if weekly_releases:
                        view = WeeklySummaryView(albums, singles)
                        embeds = await split_embeds(view)

                    # Add concerts embed if available
                    if concerts_locations:
                        max_locations = 10
                        max_events_per_location = 3
                        timestamp = datetime.now(tz=get_eastern_tz() or ZoneInfo("UTC"))
                        concerts_embed = discord.Embed(
                            title="🎟️ Upcoming Concerts (next 30 days)",
                            description="Based on your tracked artists",
                            color=0x1DB954,
                            timestamp=timestamp
                        )
                        for (city, state_name, date), events in concerts_locations[:max_locations]:
                            lines = []
                            for event_name, url, stubhub_url, artists_list in events[:max_events_per_location]:
                                artist_str = ", ".join(artists_list)
                                links = []
                                if url:
                                    links.append(f"[Ticketmaster]({url})")
                                if stubhub_url:
                                    links.append(f"[StubHub]({stubhub_url})")
                                links_str = " • ".join(links) if links else "No link available"
                                lines.append(f"**{event_name}** — {artist_str}\n{links_str}")
                            field_value = "\n\n".join(lines) if lines else "No details available"
                            concerts_embed.add_field(name=f"{city}, {state_name} — {date}", value=field_value, inline=False)

                        if len(concerts_locations) > max_locations:
                            concerts_embed.set_footer(text=f"Showing first {max_locations} locations out of {len(concerts_locations)}")

                        embeds.append(concerts_embed)

                    for embed in embeds:
                        await channel.send(embed=embed)
                except Exception as e:
                    print(f"⚠️  Could not send weekly summary to channel {channel_id}: {e}")

    async def send_no_releases_summary(self, week_start, week_end):
        """Send a summary when no releases were found for the week"""
        week_start_formatted = week_start.strftime("%B %d")
        week_end_formatted = week_end.strftime("%B %d, %Y")
        
        embed = discord.Embed(
            title="🗓️ Weekly Release Summary",
            description=f"**{week_start_formatted} - {week_end_formatted}**\n\nNo new releases from your tracked artists this week.",
            color=0x9932CC,  # Purple for weekly summaries
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📊 Current Stats",
            value=f"Tracking {len(self.artists)} artists across all genres",
            inline=False
        )
        
        embed.add_field(
            name="🎯 What's Next?",
            value="New releases will be posted as they come out!\nUse `/music add` to track more artists.",
            inline=False
        )
        
        embed.set_footer(text="Music Updater Bot • Weekly Summary")
        
        # Send to all notification channels
        for channel_id in self.notification_channels:
            channel = self.get_channel(channel_id)
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"⚠️  Could not send weekly summary to channel {channel_id}: {e}")

    async def send_release_notifications(self, release_info):
        """Send a formatted notification for a new release to all notification channels"""
        # This method is kept for backwards compatibility but not used in the new flow
        artist = release_info['artist']
        release = release_info['release']
        release_type = release_info['type']
        artist_data = release_info['artist_data']
        
        # Create rich embed
        title = f"🆕 New {release_type.title()}!"
        description = f"**{artist}** just released a new {release_type}!"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x1DB954,  # Spotify green
            timestamp=datetime.now()
        )
        
        # Add release details
        embed.add_field(name="📀 Title", value=release['name'], inline=True)
        embed.add_field(name="📅 Release Date", value=release['release_date'], inline=True)
        embed.add_field(name="🎵 Tracks", value=str(release['total_tracks']), inline=True)
        
        # Add artist info
        if artist_data.get('spotify_data'):
            spotify_data = artist_data['spotify_data']
            embed.add_field(
                name="🎸 Genres", 
                value=', '.join(spotify_data['genres'][:3]) if spotify_data['genres'] else 'Unknown', 
                inline=True
            )
            embed.add_field(
                name="👥 Followers", 
                value=f"{spotify_data['followers']:,}", 
                inline=True
            )
        
        # Add Spotify link if available
        if release.get('external_urls', {}).get('spotify'):
            embed.add_field(
                name="🔗 Listen on Spotify", 
                value=f"[Open in Spotify]({release['external_urls']['spotify']})", 
                inline=False
            )
        
        # Set thumbnail if available
        if release.get('images') and release['images']:
            embed.set_thumbnail(url=release['images'][0]['url'])
        
        embed.set_footer(text="Music Updater Bot")
        
        # Send to all notification channels
        for channel_id in self.notification_channels:
            channel = self.get_channel(channel_id)
            # Only send to TextChannel or Thread (not Category, Forum, or Private channels)
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"⚠️  Could not send notification to channel {channel_id}: {e}")
                    
    def add_notification_channel(self, channel_id: int):
        """Add a channel to receive automatic notifications (legacy sync, for compatibility)"""
        if channel_id not in self.notification_channels:
            self.notification_channels.append(channel_id)
            # Fix: Await the async save_bot_settings
            import asyncio
            asyncio.create_task(self.save_bot_settings())
            print(f"✅ Added notification channel: {channel_id}")
            return True
        return False
    
    def remove_notification_channel(self, channel_id: int):
        """Remove a channel from automatic notifications (legacy sync, for compatibility)"""
        if channel_id in self.notification_channels:
            self.notification_channels.remove(channel_id)
            # Fix: Await the async save_bot_settings
            import asyncio
            asyncio.create_task(self.save_bot_settings())
            print(f"✅ Removed notification channel: {channel_id}")
            return True
        return False

# Slash Commands - Using a more compatible approach
async def add_artist_command(interaction: discord.Interaction, artist: str):
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'artists'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    for existing_artist in bot.artists:
        if existing_artist['name'].lower() == artist.lower():
            await interaction.response.send_message(f"⚠️ **{artist}** is already being tracked!", ephemeral=True)
            return
    if not bot.spotify.is_available():
        await interaction.response.send_message("❌ Spotify API not available. Cannot add artists.", ephemeral=True)
        return
    await interaction.response.defer()
    try:
        loop = asyncio.get_event_loop()
        spotify_data = await loop.run_in_executor(None, bot.spotify.search_artist, artist, False)
        if not spotify_data:
            await interaction.followup.send(f"❌ Could not find **{artist}** on Spotify.")
            return
        artist_data = {
            'name': spotify_data['name'],
            'genre': spotify_data['genres'][0] if spotify_data['genres'] else None,
            'added_date': datetime.now().strftime("%Y-%m-%d"),
            'spotify_data': spotify_data,
            'last_checked': None,
            'latest_release': None,
            'latest_album': None,
            'latest_single': None
        }
        releases_by_type = await bot.get_latest_by_type_with_retries(spotify_data['id'])
        if releases_by_type:
            artist_data['latest_album'] = releases_by_type.get('latest_album')
            artist_data['latest_single'] = releases_by_type.get('latest_single')
        
        if isinstance(bot.artists, list):
            bot.artists.append(artist_data)
            await bot.save_data()
        embed = discord.Embed(
            title="✅ Artist Added!",
            description=f"Now tracking **{spotify_data['name']}**",
            color=0x1DB954
        )
        if spotify_data['genres']:
            embed.add_field(name="🎸 Genres", value=', '.join(spotify_data['genres'][:3]), inline=True)
        embed.add_field(name="👥 Followers", value=f"{spotify_data['followers']:,}", inline=True)
        embed.add_field(name="📊 Popularity", value=f"{spotify_data['popularity']}/100", inline=True)
        if artist_data['latest_album']:
            embed.add_field(
                name="💿 Latest Album", 
                value=f"{artist_data['latest_album']['name']} ({artist_data['latest_album']['release_date']})", 
                inline=False
            )
        if artist_data['latest_single']:
            embed.add_field(
                name="🎵 Latest Single", 
                value=f"{artist_data['latest_single']['name']} ({artist_data['latest_single']['release_date']})", 
                inline=False
            )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error adding artist: {str(e)}")

async def list_artists_command(interaction: discord.Interaction):
    """List all tracked artists with pagination"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'artists') or not bot.artists:
        await interaction.response.send_message("📭 No artists being tracked yet. Use `/music add` to start!", ephemeral=True)
        return
    
    # Create pagination view
    view = ArtistPaginationView(bot.artists)
    embed = await view.create_embed()
    
    # Only show pagination buttons if there are multiple pages
    if view.total_pages > 1:
        await interaction.response.send_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed)

async def remove_artist_command(interaction: discord.Interaction, artist: str):
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'artists'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    if not bot.artists:
        await interaction.response.send_message("📭 No artists being tracked yet. Use `/music add` to start!", ephemeral=True)
        return
    artist_to_remove = None
    for existing_artist in bot.artists:
        if existing_artist['name'].lower() == artist.lower():
            artist_to_remove = existing_artist
            break
    if not artist_to_remove:
        available_artists = [a['name'] for a in bot.artists]
        embed = discord.Embed(
            title="❌ Artist Not Found",
            description=f"**{artist}** is not in your tracking list.",
            color=0xff0000
        )
        embed.add_field(
            name="📋 Currently Tracked Artists:",
            value="\n".join([f"• {name}" for name in available_artists[:10]]),
            inline=False
        )
        if len(available_artists) > 10:
            embed.set_footer(text=f"Showing first 10 of {len(available_artists)} artists")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    if isinstance(bot.artists, list):
        bot.artists.remove(artist_to_remove)
        await bot.save_data()
    embed = discord.Embed(
        title="✅ Artist Removed!",
        description=f"**{artist_to_remove['name']}** has been removed from tracking.",
        color=0x1DB954
    )
    embed.add_field(
        name="📊 Remaining Artists",
        value=f"Now tracking {len(bot.artists)} artists",
        inline=True
    )
    await interaction.response.send_message(embed=embed)

from typing import Optional

async def setup_notifications_command(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'add_notification_channel_async'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    target_channel = channel or interaction.channel
    if target_channel is None or not hasattr(target_channel, "id"):
        await interaction.response.send_message("❌ Could not determine the target channel for notifications.", ephemeral=True)
        return
    # Resolve Member object (interaction.user may be a User or Member depending on context)
    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    guild = getattr(interaction, "guild", None)
    if not member and guild is not None:
        # Try cached member first, then fetch from API if not found in cache
        member = guild.get_member(interaction.user.id)
        if member is None:
            try:
                member = await guild.fetch_member(interaction.user.id)
            except Exception:
                member = None

    has_permission = False
    # Guild-level checks: owner, administrator, or manage_channels
    if member:
        if getattr(interaction, "guild", None) and getattr(interaction.guild, "owner_id", None) == member.id:
            has_permission = True
        else:
            perms = getattr(member, "guild_permissions", None)
            if perms:
                has_permission = bool(perms.administrator or perms.manage_channels)

    # Channel-level permission check if a specific channel was provided
    if not has_permission and target_channel and member:
        try:
            ch_perms = target_channel.permissions_for(member)
            if ch_perms and (ch_perms.administrator or ch_perms.manage_channels):
                has_permission = True
        except Exception:
            # If permissions check fails for any reason, don't grant access
            pass

    if not has_permission:
        await interaction.response.send_message("❌ You must be the server owner, or have Administrator or Manage Channels permission to set up notifications.", ephemeral=True)
        return
    if await bot.add_notification_channel_async(target_channel.id):
        embed = discord.Embed(
            title="✅ Notifications Enabled!",
            description=f"This channel will now receive automatic release notifications.",
            color=0x1DB954
        )
        embed.add_field(name="📅 Schedule", value="Twice daily at 9 AM & 6 PM", inline=True)
        channel_display = getattr(target_channel, "mention", None) or getattr(target_channel, "name", None) or f"ID: {target_channel.id}"
        embed.add_field(name="📋 Channel", value=channel_display, inline=True)
        await interaction.response.send_message(embed=embed)
    else:
        channel_display = getattr(target_channel, "mention", None) or getattr(target_channel, "name", None) or f"ID: {target_channel.id}"
        await interaction.response.send_message(f"⚠️ {channel_display} is already receiving notifications.", ephemeral=True)

from typing import Optional

async def remove_notifications_command(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'remove_notification_channel_async'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    target_channel = channel or interaction.channel
    if target_channel is None or not hasattr(target_channel, "id"):
        await interaction.response.send_message("❌ Could not determine the target channel for notifications.", ephemeral=True)
        return
    # Resolve Member object (interaction.user may be a User or Member depending on context)
    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    guild = getattr(interaction, "guild", None)
    if not member and guild is not None:
        # Try cached member first, then fetch from the API if not cached
        member = guild.get_member(interaction.user.id)
        if member is None:
            try:
                member = await guild.fetch_member(interaction.user.id)
            except Exception:
                member = None

    has_permission = False
    # Guild-level checks: owner, administrator, or manage_channels
    if member:
        if getattr(interaction, "guild", None) and getattr(interaction.guild, "owner_id", None) == member.id:
            has_permission = True
        else:
            perms = getattr(member, "guild_permissions", None)
            if perms:
                has_permission = bool(perms.administrator or perms.manage_channels)

    # Channel-level permission check if a specific channel was provided
    if not has_permission and target_channel and member:
        try:
            ch_perms = target_channel.permissions_for(member)
            if ch_perms and (ch_perms.administrator or ch_perms.manage_channels):
                has_permission = True
        except Exception:
            pass

    if not has_permission:
        await interaction.response.send_message("❌ You must be the server owner, or have Administrator or Manage Channels permission to manage notifications.", ephemeral=True)
        return
    if await bot.remove_notification_channel_async(target_channel.id):
        await interaction.response.send_message(f"✅ Notifications disabled for {getattr(target_channel, 'mention', getattr(target_channel, 'name', f'ID: {target_channel.id}'))}.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ {getattr(target_channel, 'mention', getattr(target_channel, 'name', f'ID: {target_channel.id}'))} wasn't receiving notifications.", ephemeral=True)

async def check_releases_command(interaction: discord.Interaction):
    """Manually check for new releases"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'check_and_notify_releases'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    
    # Defer response since this might take a moment
    await interaction.response.defer()
    
    try:
        # Store original notification channels
        original_channels = bot.notification_channels.copy()
        
        # Temporarily add the current channel for manual check results
        if interaction.channel and hasattr(interaction.channel, 'id'):
            current_channel_id = interaction.channel.id
            if current_channel_id not in bot.notification_channels:
                bot.notification_channels.append(current_channel_id)
        
        # Run the release check
        await bot.check_and_notify_releases()
        
        # Restore original notification channels
        bot.notification_channels = original_channels
        
        await interaction.followup.send("✅ Release check completed! Results shown below.")
        
    except Exception as e:
        # Restore original notification channels in case of error
        bot.notification_channels = original_channels
        await interaction.followup.send(f"❌ Error checking releases: {str(e)}")

async def weekly_summary_command(interaction: discord.Interaction):
    """Generate a manual weekly summary"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'send_weekly_summary'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    
    # Defer response since this might take a moment
    await interaction.response.defer()
    
    try:
        # Store original notification channels
        original_channels = bot.notification_channels.copy()
        
        # Temporarily add the current channel for manual summary results
        if interaction.channel and hasattr(interaction.channel, 'id'):
            current_channel_id = interaction.channel.id
            if current_channel_id not in bot.notification_channels:
                bot.notification_channels.append(current_channel_id)
        
        # Run the weekly summary
        await bot.send_weekly_summary()
        
        # Restore original notification channels
        bot.notification_channels = original_channels
        
        await interaction.followup.send("✅ Weekly summary completed! Results shown above.")
        
    except Exception as e:
        # Restore original notification channels in case of error
        bot.notification_channels = original_channels
        await interaction.followup.send(f"❌ Error generating weekly summary: {str(e)}")

async def song_lookup_command(interaction: discord.Interaction, query: str):
    """Look up a song across Spotify, Apple Music, and YouTube Music"""
    await interaction.response.defer()
    
    import re
    import urllib.parse
    
    # Detect if query is a URL and extract metadata
    spotify_match = re.search(r'open\.spotify\.com/(track|album)/([a-zA-Z0-9]+)', query)
    apple_match = re.search(r'music\.apple\.com/[a-z]{2}/(album|song)/[^/]+/([0-9]+)', query)
    youtube_match = re.search(r'(music\.youtube\.com|youtube\.com)/watch\?v=([a-zA-Z0-9_-]+)', query)
    
    artist_name = None
    track_name = None
    
    try:
        async with aiohttp.ClientSession() as session:
            # If Spotify URL, extract metadata
            if spotify_match:
                content_type = spotify_match.group(1)
                content_id = spotify_match.group(2)
                bot: MusicBot = interaction.client  # type: ignore
                
                # Get track/album info from Spotify
                if hasattr(bot, 'spotify') and bot.spotify.sp:
                    try:
                        data = None
                        if content_type == 'track':
                            data = bot.spotify.sp.track(content_id)
                        else:
                            data = bot.spotify.sp.album(content_id)
                        
                        if data:
                            track_name = data.get('name')
                            artist_name = data.get('artists', [{}])[0].get('name')
                    except Exception as e:
                        print(f"Error fetching Spotify metadata: {e}")
            
            # If no metadata extracted, use query as-is
            if not artist_name or not track_name:
                # Try to parse "Artist - Song" format
                if ' - ' in query:
                    parts = query.split(' - ', 1)
                    artist_name = parts[0].strip()
                    track_name = parts[1].strip()
                else:
                    track_name = query
                    artist_name = ""
            
            search_query = f"{artist_name} {track_name}".strip()
            
            # Search all platforms
            spotify_link = None
            apple_link = None
            youtube_link = None
            
            # Spotify search
            bot: MusicBot = interaction.client  # type: ignore
            if hasattr(bot, 'spotify') and bot.spotify.sp:
                try:
                    results = bot.spotify.sp.search(q=search_query, type='track', limit=1)
                    if results:
                        tracks = results.get('tracks', {}).get('items', [])
                        if tracks:
                            spotify_link = tracks[0]['external_urls']['spotify']
                            if not artist_name:
                                artist_name = tracks[0]['artists'][0]['name']
                            if not track_name:
                                track_name = tracks[0]['name']
                except Exception as e:
                    print(f"Error searching Spotify: {e}")
            
            # Apple Music search
            apple_url = "https://itunes.apple.com/search"
            params = {'term': search_query, 'entity': 'song', 'limit': 1}
            async with session.get(apple_url, params=params, timeout=5) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    try:
                        data = json.loads(text)
                        results = data.get('results', [])
                        if results and 'trackViewUrl' in results[0]:
                            apple_link = results[0]['trackViewUrl']
                    except Exception:
                        pass
            
            # YouTube Music search
            youtube_link = await get_youtube_music_topic_url(artist_name or "", track_name or query, try_music_link=True)
            
            # Build embed
            embed = discord.Embed(
                title=f"🔍 Song Lookup Results",
                description=f"**{track_name}**" + (f" by {artist_name}" if artist_name else ""),
                color=0x1DB954
            )
            
            links = []
            if spotify_link:
                links.append(f"🎧 [Spotify]({spotify_link})")
            if apple_link:
                links.append(f"🍎 [Apple Music]({apple_link})")
            if youtube_link:
                links.append(f"🎵 [YouTube Music]({youtube_link})")
            
            if links:
                embed.add_field(
                    name="Available On",
                    value="\n".join(links),
                    inline=False
                )
            else:
                embed.add_field(
                    name="⚠️ No Results Found",
                    value="Could not find this song on any platform. Try refining your search.",
                    inline=False
                )
            
            embed.set_footer(text="Music Updater Bot • Song Lookup")
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error looking up song: {str(e)}")

async def stats_command(interaction: discord.Interaction):
    """Show bot statistics"""
    bot: MusicBot = interaction.client  # type: ignore
    if not hasattr(bot, 'artists'):
        await interaction.response.send_message("❌ Bot not properly initialized.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📊 Music Updater Bot Stats",
        color=0x1DB954
    )
    
    embed.add_field(name="🎵 Tracked Artists", value=str(len(bot.artists)), inline=True)
    embed.add_field(name="🔔 Notification Channels", value=str(len(bot.notification_channels)), inline=True)
    embed.add_field(name="🏠 Servers", value=str(len(bot.guilds)), inline=True)
    
    # Add some artist stats
    if bot.artists:
        with_spotify = sum(1 for a in bot.artists if a.get('spotify_data'))
        embed.add_field(name="🎧 Spotify Connected", value=f"{with_spotify}/{len(bot.artists)}", inline=True)
        
        recent_albums = sum(1 for a in bot.artists if a.get('latest_album'))
        recent_singles = sum(1 for a in bot.artists if a.get('latest_single'))
        embed.add_field(name="💿 Albums Tracked", value=str(recent_albums), inline=True)
        embed.add_field(name="🎵 Singles Tracked", value=str(recent_singles), inline=True)
    
    embed.set_footer(text="Next automatic check: 9 AM or 6 PM (whichever comes first)")
    await interaction.response.send_message(embed=embed)

async def help_command(interaction: discord.Interaction):
    """Show all available commands"""
    embed = discord.Embed(
        title="🎵 Music Updater Bot Commands",
        description="Manage your artist tracking and get release notifications!\n\n**All commands work in any channel where you can use slash commands.**",
        color=0x1DB954
    )
    
    commands_list = [
        ("📝 `/music add <artist>`", "Add an artist to track"),
        ("📋 `/music list`", "Show all tracked artists"),
        ("🗑️ `/music remove <artist>`", "Remove an artist from tracking"),
        ("🔍 `/music check`", "Check for new releases now"),
        ("�️ `/music weekly`", "Generate weekly release summary"),
        ("�📊 `/music stats`", "Show bot statistics"),
        ("🔔 `/music setup [channel]`", "Enable notifications (Admin only)"),
        ("🔕 `/music unsetup [channel]`", "Disable notifications (Admin only)"),
        ("❓ `/music help`", "Show this help message")
    ]
    
    for command, description in commands_list:
        embed.add_field(name=command, value=description, inline=False)
    
    embed.add_field(
        name="📢 About Notifications",
        value="• Use `/music setup` to enable automatic notifications in a channel\n• Releases: twice daily at 9 AM & 6 PM\n• Concerts: weekly with Friday summary (12:05 AM)\n• Weekly summaries every Friday at midnight\n• Commands work in any channel, notifications go to configured channels",
        inline=False
    )
    embed.set_footer(text="🔔 Bot works globally - no need to be in a specific channel!")
    await interaction.response.send_message(embed=embed)

# Music command group
class MusicGroup(app_commands.Group):

    @app_commands.command(name="concerts", description="Show upcoming concerts for your tracked artists. Optionally filter by artist and state.")
    @app_commands.describe(artist="Filter to a single artist", state="Comma-separated US state codes (e.g., MA,RI,CT)", days="Days ahead window (default 180)")
    async def concerts(self, interaction: discord.Interaction, artist: Optional[str] = None, state: Optional[str] = None, days: Optional[int] = None):
        """Show upcoming concerts using artists from `artists_data.json` (via bot data).

        - If `artist` is provided, filters to that artist.
        - If `state` is provided, uses it (comma-separated codes supported). Otherwise uses `config.TICKETMASTER_STATES` or default.
        """
        bot: MusicBot = interaction.client  # type: ignore
        TICKETMASTER_API_KEY = getattr(config, "TICKETMASTER_API_KEY", None) or os.environ.get("TICKETMASTER_API_KEY")
        if not TICKETMASTER_API_KEY:
            await interaction.response.send_message("❌ Ticketmaster API key not configured. Set TICKETMASTER_API_KEY in config or environment.", ephemeral=True)
            return

        await interaction.response.defer()

        # Determine tracked artists from bot memory; fall back to local JSON if needed
        tracked = []
        try:
            if hasattr(bot, "artists") and bot.artists:
                tracked = bot.artists
            else:
                with open("artists_data.json", "r", encoding="utf-8") as f:
                    tracked = json.load(f)
        except Exception as e:
            await interaction.followup.send(f"❌ Could not load artists from JSON: {e}")
            return

        # Optional filter by artist name
        if artist:
            filtered = [a for a in tracked if a.get("name", "").lower() == artist.lower()]
            if not filtered:
                await interaction.followup.send(f"❌ Artist '{artist}' not found in your tracked list.")
                return
            tracked = filtered

        if not tracked:
            await interaction.followup.send("📭 No tracked artists found.")
            return

        # To avoid long stalls, cap number of artists when not filtering by a single artist
        truncated_note = None
        if not artist and len(tracked) > 20:
            truncated_note = f"(limited to first 20 of {len(tracked)} tracked artists)"
            tracked = tracked[:20]

        states_arg = None
        if state and state.strip():
            states_arg = state.strip()
        else:
            states_arg = getattr(config, "TICKETMASTER_STATES", None) or "NH,MA,RI,CT"

        days_ahead = days if (isinstance(days, int) and days > 0) else getattr(config, "TICKETMASTER_DAYS_AHEAD", 30)

        if not interaction.response.is_done():
            await interaction.response.defer()

        try:
            locations = await bot.collect_concert_events(states=states_arg, max_events=5, days_ahead=days_ahead, artists=tracked)
        except Exception as e:
            await interaction.followup.send(f"❌ Error collecting concerts: {e}")
            return

        if not locations:
            # Fallback: show raw Ticketmaster results for visibility
            raw = await bot.collect_concert_events_raw(states=states_arg, max_events=10, days_ahead=days_ahead, artists=tracked)
            if raw:
                timestamp = datetime.now(tz=get_eastern_tz() or ZoneInfo("UTC"))
                embed = discord.Embed(
                    title="🎟️ Ticketmaster Raw Events",
                    description=f"States: {states_arg or 'All'} • Unfiltered results",
                    color=0x808080,
                    timestamp=timestamp
                )
                max_items = 12
                for item in raw[:max_items]:
                    artists_str = ", ".join(item.get("artists") or []) or "Unknown"
                    premium_tag = " • Premium" if item.get("premium") else ""
                    links = []
                    if item.get("url"):
                        links.append(f"[Ticketmaster]({item['url']})")
                    links_str = " • ".join(links) if links else "No link available"
                    # Safe field name
                    city = item.get('city','')
                    state_name = item.get('state','')
                    date = item.get('date','?')
                    field_name = f"{city}, {state_name} — {date}".strip()
                    if not (city or state_name):
                        field_name = f"Unknown location — {date}"
                    embed.add_field(
                        name=field_name,
                        value=f"**{item.get('event_name','Unknown Event')}**{premium_tag}\nArtists: {artists_str}\n{links_str}",
                        inline=False
                    )
                if len(raw) > max_items:
                    embed.set_footer(text=f"Showing first {max_items} of {len(raw)} raw events")
                await interaction.followup.send(embed=embed)
                return
            await interaction.followup.send("ℹ️ No upcoming concerts found (and no raw events to display).")
            return

        # Paginate all locations to show full list
        view = ConcertsPaginationView(locations, days_ahead=days_ahead, states=states_arg)
        first_embed = await view.create_embed()
        if view.total_pages > 1:
            await interaction.followup.send(embed=first_embed, view=view)
        else:
            await interaction.followup.send(embed=first_embed)
    """Music tracking commands"""
    
    def __init__(self):
        super().__init__(name='music', description='Track artists and get release notifications')
    
    @app_commands.command(name='add', description='Add an artist to track')
    @app_commands.describe(artist="The name of the artist to add")
    async def add(self, interaction: discord.Interaction, artist: str):
        await add_artist_command(interaction, artist)
    
    @app_commands.command(name='list', description='List all tracked artists')
    async def list(self, interaction: discord.Interaction):
        await list_artists_command(interaction)
    
    @app_commands.command(name='remove', description='Remove an artist from tracking')
    @app_commands.describe(artist="The name of the artist to remove")
    async def remove(self, interaction: discord.Interaction, artist: str):
        await remove_artist_command(interaction, artist)
    
    @app_commands.command(name='help', description='Show all commands')
    async def help(self, interaction: discord.Interaction):
        await help_command(interaction)
    
    @app_commands.command(name='setup', description='Enable notifications in current/specified channel')
    @app_commands.describe(channel="Channel to receive notifications (defaults to current channel)")
    async def setup(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        await setup_notifications_command(interaction, channel)
    
    @app_commands.command(name='unsetup', description='Disable notifications in current/specified channel')
    @app_commands.describe(channel="Channel to stop receiving notifications (defaults to current channel)")
    async def unsetup(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        await remove_notifications_command(interaction, channel)
    
    @app_commands.command(name='check', description='Check for new releases now')
    async def check(self, interaction: discord.Interaction):
        await check_releases_command(interaction)
    
    @app_commands.command(name='weekly', description='Generate weekly release summary')
    async def weekly(self, interaction: discord.Interaction):
        await weekly_summary_command(interaction)
    
    @app_commands.command(name='stats', description='Show bot statistics')
    async def stats(self, interaction: discord.Interaction):
        await stats_command(interaction)
    
    @app_commands.command(name='song', description='Look up a song across Spotify, Apple Music, and YouTube Music')
    @app_commands.describe(query="Song name, 'Artist - Song', or a URL from Spotify/Apple Music/YouTube")
    async def song(self, interaction: discord.Interaction, query: str):
        await song_lookup_command(interaction, query)

# Initialize and run bot
async def health_check(request):
    """Simple health check endpoint for keep-alive service"""
    return web.json_response({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "music-updater-bot"
    })

async def start_health_server():
    """Start a simple health check server for keep-alive"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)  # Root endpoint too
    
    preferred_port = int(os.environ.get('PORT', 8080))  # Render uses PORT env var
    runner = web.AppRunner(app)
    await runner.setup()

    # Try preferred port, fall back to next few if in use
    last_exc = None
    for port in [preferred_port] + list(range(8081, 8091)) + [0]:
        try:
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            print(f"🏥 Health check server started on port {port}")
            return runner
        except OSError as e:
            last_exc = e
            continue
    # If all attempts fail, raise the last error
    raise last_exc or RuntimeError("Unable to start health server")

async def run_discord_bot():
    """Initialize and run the Discord bot"""
    token = config.DISCORD_TOKEN or os.environ.get("DISCORD_TOKEN") or os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ Discord token not configured. Please set DISCORD_TOKEN in config.py or as an environment variable.")
        raise RuntimeError("Discord token not configured")
    
    bot = MusicBot()
    
    # Add the music command group
    bot.tree.add_command(MusicGroup())
    
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        print("\n🛑 Bot shutdown requested...")
    except Exception as e:
        print(f"❌ Error starting Discord bot: {e}")
    finally:
        # Ensure proper cleanup
        if not bot.is_closed():
            await bot.close()

async def main():
    """Main entry point that starts both the health server and Discord bot"""
    print("🚀 Starting Music Updater Discord Bot...")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🐍 Python version: {sys.version.split()[0]}")
    
    # Start health check server for Render
    print("🏥 Starting health check server...")
    health_runner = await start_health_server()
    
    try:
        # Start the Discord bot (this will run indefinitely)
        print("🤖 Starting Discord bot...")
        await run_discord_bot()
    finally:
        # Cleanup health server if bot stops
        print("🧹 Cleaning up health server...")
        await health_runner.cleanup()

if __name__ == "__main__":
    # Run the bot with proper event loop handling
    try:
        print("🎯 Executing discord_bot.py as main module")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            print("✅ Bot stopped cleanly")
        else:
            print(f"❌ Runtime error: {e}")
            raise
    except Exception as e:
        print(f"❌ Unexpected error during startup: {e}")
        import traceback
        traceback.print_exc()
        raise
