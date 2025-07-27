#!/usr/bin/env python3
"""
Startup script for the Discord Music Updater Bot
This ensures the bot starts correctly in production environments like Render
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        # Import and run the Discord bot
        from discord_bot import main
        import asyncio
        
        print("🚀 Starting Discord Music Updater Bot...")
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot failed to start: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
