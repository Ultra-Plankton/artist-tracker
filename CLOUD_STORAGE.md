# Cloud Storage Setup Guide

This guide shows you how to set up persistent storage so your artist list survives Render restarts/redeploys.

## Option 1: JSONBin.io (Easiest - No GitHub account needed)

JSONBin.io provides free cloud JSON storage (100MB free tier).

### Setup Steps:

1. **Create account** at [jsonbin.io](https://jsonbin.io)

2. **Create bins for both data and settings**:
   
   **Artists Data Bin:**
   - Click "Create" → "JSON Bin"
   - Name it "music-bot-artists"
   - Paste your current artists data or use `[]` for empty
   - Click "Create"
   - Copy the **Bin ID** from URL (e.g., `6123456789abcdef12345678`)
   
   **Bot Settings Bin:**
   - Click "Create" → "JSON Bin" 
   - Name it "music-bot-settings"
   - Paste `{"notification_channels": []}` or your current settings
   - Click "Create"
   - Copy the **Bin ID** from URL (e.g., `9876543210fedcba87654321`)

3. **Get your credentials**:
   - Go to "API Keys" → Create new API key
   - Copy the **API Key**

4. **Add to Render environment variables**:
   ```
   JSONBIN_API_KEY=your_api_key_here
   JSONBIN_BIN_ID=your_artists_bin_id_here
   JSONBIN_SETTINGS_BIN_ID=your_settings_bin_id_here
   ```

## Option 2: GitHub Gist (Free with GitHub account)

Uses GitHub Gists as cloud storage.

### Setup Steps:

1. **Create a GitHub Personal Access Token**:
   - Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Give it a name like "music-bot-storage"
   - Select scope: `gist` (Create gists)
   - Generate and copy the token

2. **Create gists for both data and settings**:
   
   **Artists Data Gist:**
   - Go to [gist.github.com](https://gist.github.com)
   - Create new gist with filename `artists_data.json`
   - Paste your current artists data or use `[]` for empty
   - Create as **Secret** gist
   - Copy the Gist ID from URL (e.g., `a1b2c3d4e5f6`)
   
   **Bot Settings Gist:**
   - Create another gist with filename `bot_settings.json`
   - Paste `{"notification_channels": []}` or your current settings
   - Create as **Secret** gist
   - Copy the Gist ID from URL (e.g., `f6e5d4c3b2a1`)

3. **Add to Render environment variables**:
   ```
   GITHUB_TOKEN=your_personal_access_token
   GITHUB_GIST_ID=your_artists_gist_id_here
   GITHUB_SETTINGS_GIST_ID=your_settings_gist_id_here
   ```

## Option 3: Environment Variable Only (Current method)

Keep using your current base64 method but manually update it when needed.

## Priority Order

The bot will try to load artists in this order:
1. **Cloud storage** (JSONBin or GitHub Gist)
2. **Environment variable** (ARTISTS_DATA)
3. **Local file** (artists_data.json)

## Benefits

✅ **Persistent storage** - Artists AND notification channels survive restarts/redeploys  
✅ **Automatic sync** - New artists and channel subscriptions saved to cloud immediately  
✅ **Fallback** - Multiple backup options  
✅ **Free tier friendly** - Works with free hosting  
✅ **Complete state preservation** - No more re-subscribing channels after redeploys  

## Recommendations

- **For personal use**: JSONBin.io (easier setup)
- **If you have GitHub**: GitHub Gist (more developer-friendly)
- **Quick start**: Keep using environment variable method
