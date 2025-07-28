"""
Keep-alive script for Render deployment
Helps prevent the service from sleeping on Render's free tier
"""

import asyncio
import aiohttp
import os
from datetime import datetime

class KeepAlive:
    def __init__(self, url=None, interval=30):  # 30 seconds default
        """
        Initialize keep-alive service
        
        Args:
            url: URL to ping (optional - uses Render service URL if available)
            interval: Ping interval in seconds (default 10 minutes)
        """
        self.url = url or os.environ.get('RENDER_EXTERNAL_URL')
        self.interval = interval
        self.session = None
        
    async def start(self):
        """Start the keep-alive service"""
        if not self.url:
            print("ℹ️  No URL configured for keep-alive - skipping")
            return
            
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        print(f"🔄 Starting keep-alive service")
        print(f"📡 Target URL: {self.url}")
        print(f"⏰ Ping interval: {self.interval} seconds")
        
        while True:
            try:
                await self.ping()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                print("🛑 Keep-alive service stopped")
                break
            except Exception as e:
                print(f"⚠️  Keep-alive error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
                
    async def ping(self):
        """Send a ping to keep the service alive"""
        if not self.session:
            return
            
        try:
            async with self.session.get(f"{self.url}/health") as response:
                status = "✅" if response.status == 200 else "⚠️"
                print(f"{status} Keep-alive ping: {response.status} at {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"❌ Keep-alive ping failed: {e}")
            
    async def stop(self):
        """Stop the keep-alive service"""
        if self.session:
            await self.session.close()

# Global keep-alive instance
keep_alive_service = KeepAlive()

async def start_keep_alive():
    """Start the keep-alive service"""
    await keep_alive_service.start()

if __name__ == "__main__":
    # Test the keep-alive service
    asyncio.run(start_keep_alive())
