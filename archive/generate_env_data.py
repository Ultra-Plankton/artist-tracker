"""
Generate environment variable for artist data
Run this script to get the ARTISTS_DATA env var for Render deployment
"""

import json
import base64

def generate_env_var():
    try:
        # Load your current artists data
        with open('artists_data.json', 'r', encoding='utf-8') as f:
            artists_data = json.load(f)
        
        # Convert to JSON string and encode to base64
        json_string = json.dumps(artists_data, separators=(',', ':'))  # Compact JSON
        encoded_data = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
        
        print("🎵 Your artist list has been encoded for Render deployment!")
        print(f"📊 Number of artists: {len(artists_data)}")
        print(f"📏 Data size: {len(encoded_data)} characters")
        print("\n" + "="*60)
        print("Copy this environment variable to Render:")
        print("="*60)
        print(f"ARTISTS_DATA={encoded_data}")
        print("="*60)
        print("\n📋 Instructions:")
        print("1. Go to your Render dashboard")
        print("2. Select your web service")
        print("3. Go to Environment tab")
        print("4. Add a new environment variable:")
        print("   Key: ARTISTS_DATA")
        print("   Value: [paste the long string above]")
        print("5. Deploy your service")
        print("\n✅ Your bot will load this artist list on startup!")
        
    except FileNotFoundError:
        print("❌ artists_data.json not found!")
        print("Make sure you're running this from your project directory.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_env_var()
