# Cloud Storage Setup Guide

This guide shows you how to set up persistent storage so your artist list survives Render restarts/redeploys.

## Option 1: JSONBin.io (Easiest - No GitHub account needed)

JSONBin.io provides free cloud JSON storage (100MB free tier).

### Setup Steps:

1. **Create account** at [jsonbin.io](https://jsonbin.io)

2. **Create a new bin**:
   - Click "Create" → "JSON Bin"
   - Name it "music-bot-artists"
   - Paste your current artists data or use `[]` for empty
   - Click "Create"

3. **Get your credentials**:
   - Copy the **Bin ID** from the URL (e.g., `6123456789abcdef12345678`)
   - Go to "API Keys" → Create new API key
   - Copy the **API Key**

4. **Add to Render environment variables**:
   ```
   JSONBIN_API_KEY=your_api_key_here
   JSONBIN_BIN_ID=your_bin_id_here
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

2. **Create a Gist**:
   - Go to [gist.github.com](https://gist.github.com)
   - Create new gist with filename `artists_data.json`
   - Paste your current artists data or use `[]` for empty
   - Create as **Secret** gist
   - Copy the Gist ID from URL (e.g., `a1b2c3d4e5f6`)

3. **Add to Render environment variables**:
   ```
   GITHUB_TOKEN=your_personal_access_token
   GITHUB_GIST_ID=your_gist_id_here
   ```

## Option 3: Environment Variable Only (Current method)

Keep using your current base64 method but manually update it when needed.

## Priority Order

The bot will try to load artists in this order:
1. **Cloud storage** (JSONBin or GitHub Gist)
2. **Environment variable** (ARTISTS_DATA)
3. **Local file** (artists_data.json)

## Benefits

✅ **Persistent storage** - Artists survive restarts/redeploys  
✅ **Automatic sync** - New artists are saved to cloud immediately  
✅ **Fallback** - Multiple backup options  
✅ **Free tier friendly** - Works with free hosting  

## Recommendations

- **For personal use**: JSONBin.io (easier setup)
- **If you have GitHub**: GitHub Gist (more developer-friendly)
- **Quick start**: Keep using environment variable method
