#!/usr/bin/env python3
"""
API Configuration Helper for Billboard Music Database
Helps configure free APIs for optimal performance
"""

import os
import sys
from pathlib import Path

def get_lastfm_api_key():
    """Guide user through getting Last.fm API key"""
    print("🎵 Last.fm API Setup")
    print("=" * 50)
    print("Last.fm provides free community-driven genre tags.")
    print("Getting an API key will improve genre classification accuracy.")
    print()
    print("Steps to get your Last.fm API key:")
    print("1. Go to: https://www.last.fm/api")
    print("2. Click 'Get an API account'")
    print("3. Fill out the form (it's free)")
    print("4. You'll receive an API key")
    print()
    
    api_key = input("Enter your Last.fm API key (or press Enter to skip): ").strip()
    return api_key if api_key else None

def update_env_file(api_key: str):
    """Update the .env file with the Last.fm API key"""
    env_file = Path(__file__).parent / '.env'
    
    # Read existing content
    lines = []
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()
    
    # Check if LASTFM_API_KEY already exists
    lastfm_found = False
    for i, line in enumerate(lines):
        if line.startswith('LASTFM_API_KEY'):
            lines[i] = f'LASTFM_API_KEY={api_key}\n'
            lastfm_found = True
            break
    
    # Add if not found
    if not lastfm_found:
        lines.append(f'LASTFM_API_KEY={api_key}\n')
    
    # Write back to file
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Updated {env_file} with Last.fm API key")

def test_apis():
    """Test all configured APIs"""
    print("\n🧪 Testing API Configuration")
    print("=" * 50)
    
    # Test Last.fm
    try:
        from src.api.lastfm_genre_client import LastFmGenreClient
        client = LastFmGenreClient()
        print("✅ Last.fm API: Configured")
    except Exception as e:
        print(f"❌ Last.fm API: {e}")
    
    # Test Spotify
    try:
        from src.api.spotify_genre_client import SpotifyGenreClient
        client = SpotifyGenreClient()
        print("✅ Spotify API: Configured")
    except Exception as e:
        print(f"❌ Spotify API: {e}")
    
    # Test Genius
    try:
        from src.api.genius_client import GeniusService
        client = GeniusService()
        print("✅ Genius API: Configured")
    except Exception as e:
        print(f"❌ Genius API: {e}")
    
    # Test Chartmetric
    try:
        from src.api.chartmetric_client import ChartmetricClient
        client = ChartmetricClient()
        if client.refresh_token:
            print("✅ Chartmetric API: Configured")
        else:
            print("⚠️  Chartmetric API: Not configured (optional)")
    except Exception as e:
        print(f"❌ Chartmetric API: {e}")

def main():
    """Main configuration function"""
    print("🚀 Billboard Music Database - API Configuration")
    print("=" * 60)
    print()
    
    # Check current configuration
    print("Current API Status:")
    test_apis()
    print()
    
    # Offer to configure Last.fm
    lastfm_key = get_lastfm_api_key()
    if lastfm_key:
        update_env_file(lastfm_key)
        print("\n🎉 Last.fm API configured successfully!")
    else:
        print("\n⏭️  Skipped Last.fm configuration")
    
    print("\n" + "=" * 60)
    print("Configuration complete!")
    print()
    print("Next steps:")
    print("1. Test the genre classification system:")
    print("   python scripts/genre_classification_system.py --test")
    print()
    print("2. For Chartmetric API (optional, paid):")
    print("   See CHARTMETRIC_SETUP.md for instructions")
    print()
    print("3. Run full classification:")
    print("   python scripts/genre_processing_manager.py --full")

if __name__ == "__main__":
    main()
