#!/usr/bin/env python3
"""
Chartmetric API Client for Billboard Music Database
Handles authentication and API calls for industry data
Adapted from ARI project for Billboard database structure
"""

import os
import sys
import requests
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file."""
    env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load .env file
load_env_file()

logger = logging.getLogger(__name__)

class ChartmetricClient:
    """Client for interacting with the Chartmetric API"""
    
    def __init__(self, refresh_token: str = None):
        self.refresh_token = refresh_token or os.getenv('CHARTMETRIC_REFRESH_TOKEN')
        self.access_token = None
        self.token_expires_at = None
        self.base_url = "https://api.chartmetric.com/api"
        
        if not self.refresh_token:
            logger.warning("Chartmetric refresh token not found - API will be disabled")
    
    def get_access_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        
        if not self.refresh_token:
            return None
        
        # Check if we have a valid token
        if (self.access_token and self.token_expires_at and 
            datetime.now() < self.token_expires_at - timedelta(minutes=5)):
            return self.access_token
        
        # Get new access token
        logger.info("🔄 Getting new Chartmetric access token...")
        
        url = f"{self.base_url}/token"
        payload = {"refreshtoken": self.refresh_token}
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data.get("token")
            expires_in = data.get("expires_in", 3600)  # Default to 1 hour
            
            if not self.access_token:
                raise ValueError("No access token in response")
            
            # Set expiration based on expires_in from response
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info("✅ Successfully obtained Chartmetric access token")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to get Chartmetric access token: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error getting access token: {e}")
            return None
    
    def make_request(self, endpoint: str, params: Dict = None, method: str = "GET") -> Optional[Dict]:
        """Make an authenticated request to the Chartmetric API"""
        
        access_token = self.get_access_token()
        if not access_token:
            return None
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ Chartmetric API error for {endpoint}: {e}")
            logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request error for {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error for {endpoint}: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test the API connection and authentication"""
        
        logger.info("🧪 Testing Chartmetric API connection...")
        
        if not self.refresh_token:
            logger.warning("⚠️  Chartmetric refresh token not configured - API disabled")
            return False
        
        try:
            # Test authentication by getting an access token
            access_token = self.get_access_token()
            
            if access_token:
                logger.info("✅ Chartmetric API authentication successful!")
                logger.info(f"   🔑 Access token obtained (expires: {self.token_expires_at})")
                return True
            else:
                logger.error("❌ Chartmetric API authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing Chartmetric connection: {e}")
            return False
    
    def search_artist(self, artist_name: str, limit: int = 10) -> List[Dict]:
        """Search for artists by name"""
        
        if not self.refresh_token:
            return []
        
        params = {"q": artist_name, "type": "artists", "limit": limit}
        result = self.make_request("search", params=params)
        
        if result and result.get("obj") and result["obj"].get("artists"):
            return result["obj"]["artists"]
        
        return []
    
    def search_track(self, track_name: str, artist_name: str = None, limit: int = 10) -> List[Dict]:
        """Search for tracks by name and optionally artist"""
        
        if not self.refresh_token:
            return []
        
        query = track_name
        if artist_name:
            query = f"{track_name} {artist_name}"
        
        params = {"q": query, "type": "tracks", "limit": limit}
        result = self.make_request("search", params=params)
        
        if result and result.get("obj") and result["obj"].get("tracks"):
            return result["obj"]["tracks"]
        
        return []
    
    def get_artist_stats(self, artist_id: int, platform: str = "spotify") -> Optional[Dict]:
        """Get comprehensive stats for an artist"""
        
        if not self.refresh_token:
            return None
        
        result = self.make_request(f"artist/{artist_id}/stat/{platform}")
        return result
    
    def get_track_stats(self, track_id: int, platform: str = "spotify") -> Optional[Dict]:
        """Get comprehensive stats for a track"""
        
        if not self.refresh_token:
            return None
        
        result = self.make_request(f"track/{track_id}/stat/{platform}")
        return result
    
    def get_artist_metadata(self, artist_id: int) -> Optional[Dict]:
        """Get metadata for an artist (genre, followers, etc.)"""
        
        if not self.refresh_token:
            return None
        
        result = self.make_request(f"artist/{artist_id}")
        return result
    
    def get_track_metadata(self, track_id: int) -> Optional[Dict]:
        """Get metadata for a track (streams, genre, etc.)"""
        
        if not self.refresh_token:
            return None
        
        result = self.make_request(f"track/{track_id}")
        return result
    
    def extract_artist_genre_data(self, artist_name: str) -> Dict[str, Any]:
        """Extract genre data for an artist from Chartmetric"""
        
        if not self.refresh_token:
            return {}
        
        try:
            # Search for artist
            artists = self.search_artist(artist_name, limit=1)
            
            if not artists:
                return {}
            
            artist = artists[0]
            artist_id = artist.get('id')
            
            if not artist_id:
                return {}
            
            # Get artist metadata
            metadata = self.get_artist_metadata(artist_id)
            
            if not metadata or not metadata.get('obj'):
                return {}
            
            artist_data = metadata['obj']
            
            # Extract genre information
            genres = artist_data.get('genres', [])
            
            return {
                'artist_name': artist_data.get('name', artist_name),
                'chartmetric_id': artist_id,
                'genres': genres,
                'followers': artist_data.get('sp_followers', 0),
                'popularity': artist_data.get('sp_popularity', 0),
                'verified': artist_data.get('verified', False)
            }
            
        except Exception as e:
            logger.error(f"Error extracting Chartmetric data for {artist_name}: {e}")
            return {}

# Test function
def test_chartmetric_api():
    """Test function to verify Chartmetric API setup"""
    
    print("🚀 Testing Chartmetric API Setup")
    print("=" * 50)
    
    try:
        # Initialize client
        client = ChartmetricClient()
        
        # Test connection
        if not client.test_connection():
            print("❌ Connection test failed or API not configured")
            return False
        
        # Test artist search
        print("\n🎤 Testing artist search...")
        artists = client.search_artist("Taylor Swift", limit=3)
        if artists:
            print(f"✅ Found {len(artists)} artists:")
            for artist in artists:
                print(f"   - {artist.get('name')} (ID: {artist.get('id')})")
        else:
            print("❌ Artist search failed")
        
        # Test track search
        print("\n🎵 Testing track search...")
        tracks = client.search_track("Anti-Hero", "Taylor Swift", limit=3)
        if tracks:
            print(f"✅ Found {len(tracks)} tracks:")
            for track in tracks:
                artists_str = ", ".join([a.get('name', 'Unknown') for a in track.get('artists', [])])
                print(f"   - '{track.get('name')}' by {artists_str} (ID: {track.get('id')})")
        else:
            print("❌ Track search failed")
        
        # Test getting artist metadata if we found any
        if artists:
            print("\n📊 Testing artist metadata...")
            first_artist = artists[0]
            metadata = client.get_artist_metadata(first_artist['id'])
            if metadata:
                print(f"✅ Got metadata for {first_artist['name']}")
                if metadata.get('obj'):
                    obj = metadata['obj']
                    print(f"   📈 Followers: {obj.get('sp_followers', 'N/A')}")
                    print(f"   🎵 Genres: {obj.get('genres', 'N/A')}")
            else:
                print("❌ Failed to get artist metadata")
        
        print("\n🎉 Chartmetric API setup successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Chartmetric API: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_chartmetric_api()
