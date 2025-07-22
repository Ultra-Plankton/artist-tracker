# Discord Bot Setup Guide

## Step 1: Create a Discord Bot

1. **Go to Discord Developer Portal**
   - Visit: https://discord.com/developers/applications
   - Click "New Application"
   - Give it a name like "Music Updater Bot"

2. **Create the Bot**
   - Go to the "Bot" section in the left menu
   - Click "Add Bot"
   - Copy the bot token (keep this secret!)

3. **Set Bot Permissions**
   - In the "Bot" section, enable these permissions:
     - ✅ Send Messages
     - ✅ Use Slash Commands
     - ✅ Embed Links
     - ✅ Read Message History
   - Copy the bot's Client ID from the "General Information" section

## Step 2: Invite Bot to Your Server

1. **Generate Invite Link**
   - Go to "OAuth2" > "URL Generator"
   - Select scopes: `bot` and `applications.commands`
   - Select permissions: 
     - Send Messages
     - Use Slash Commands
     - Embed Links
     - Read Message History
   - Copy the generated URL and open it to invite the bot

## Step 3: Configure Your Environment

Add these to your `.env` file:

```env
# Discord Bot Configuration
DISCORD_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
```

**To get Channel ID:**
1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click the channel where you want notifications
3. Click "Copy ID"

## Step 4: Run the Bot

```bash
python discord_bot.py
```

## Available Commands

Once the bot is running, use these **slash commands** in Discord:

### 🎵 **Music Commands**
- `/music help` - Show all commands
- `/music add <artist>` - Add an artist to track
- `/music list` - Show all tracked artists  
- `/music remove <artist>` - Remove an artist
- `/music check` - Check for new releases now
- `/music stats` - Show bot statistics

### ⚙️ **Admin Commands**
- `/music setup <#channel>` - Set notification channel (Admin only)

## Features

### 🔔 **Automatic Notifications**
- Checks for new releases **twice daily** (9 AM & 6 PM)
- Sends rich embed notifications with:
  - Album/Single cover art
  - Release details (title, date, track count)
  - Artist info (genres, followers)
  - Direct Spotify links

### 🎯 **Smart Tracking**
- Distinguishes between albums and singles
- Tracks both types separately
- Rich artist data from Spotify
- Persistent data storage

### 🤖 **Easy Management**
- Add/remove artists via Discord slash commands
- View all tracked artists
- Manual release checks
- Bot statistics and health monitoring

## Example Usage

```
/music add Metallica
/music add "I Prevail"
/music list
/music check
```

The bot will automatically start checking for releases and send notifications like:

```
🆕 New Album!
Metallica just released a new album!

📀 Title: 72 Seasons
📅 Release Date: 2023-04-14
🎵 Tracks: 12
🎸 Genres: metal, thrash metal, hard rock
👥 Followers: 15,123,456
🔗 Listen on Spotify
```

## Troubleshooting

### Bot Not Responding
- Check the bot token is correct
- Ensure the bot has proper permissions
- Verify the bot is online in your server

### No Notifications
- Set up the notification channel: `!music setup #your-channel`
- Check DISCORD_CHANNEL_ID in .env file
- Ensure bot has permission to send messages in the channel

### Spotify Errors
- Verify Spotify credentials in .env
- Check internet connection
- Try refreshing Spotify tokens
