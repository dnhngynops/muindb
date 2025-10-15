#!/usr/bin/env python3
"""
Last.fm Genre Client for Billboard Music Database
Extract community-driven genre classifications and tag data from Last.fm API
Adapted from ARI project for Billboard database structure
"""

import os
import sys
import json
import time
import requests
from typing import Dict, List, Optional, Any
from urllib.parse import quote

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

class LastFmGenreClient:
    """
    Last.fm API client for extracting community-driven genre classifications
    Adapted for Billboard Music Database
    """
    
    def __init__(self):
        # Get API key from environment
        self.api_key = os.getenv('LASTFM_API_KEY')
        
        if not self.api_key:
            # Use a fallback API key for testing (this is a public key)
            self.api_key = 'b337bfd175ef8d4ff131a03537e72fb0'
            print("   ⚠️  Using fallback Last.fm API key - consider setting LASTFM_API_KEY")
        
        self.base_url = "https://ws.audioscrobbler.com/2.0/"
        self.session = requests.Session()
        
        # Genre relevance weights for Last.fm tags
        self.genre_relevance_weights = {
            # High relevance - clear genre indicators
            'rock': 1.0, 'pop': 1.0, 'hip-hop': 1.0, 'country': 1.0, 'electronic': 1.0,
            'indie': 1.0, 'alternative': 1.0, 'folk': 1.0, 'jazz': 1.0, 'blues': 1.0,
            'metal': 1.0, 'punk': 1.0, 'reggae': 1.0, 'soul': 1.0, 'funk': 1.0,
            
            # Medium relevance - sub-genres and descriptors
            'indie rock': 0.9, 'pop rock': 0.9, 'alternative rock': 0.9,
            'hip hop': 0.9, 'rap': 0.9, 'country pop': 0.9, 'new country': 0.9,
            'electropop': 0.9, 'synthpop': 0.9, 'dance': 0.8, 'house': 0.8,
            'acoustic': 0.8, 'singer-songwriter': 0.8, 'indie pop': 0.8,
            
            # Lower relevance - mood/style descriptors
            'chill': 0.6, 'upbeat': 0.6, 'mellow': 0.6, 'energetic': 0.6,
            'catchy': 0.5, 'emotional': 0.5, 'atmospheric': 0.5,
            
            # Very low relevance - non-genre tags
            'male vocalists': 0.2, 'female vocalists': 0.2, 'seen live': 0.1,
            'favorites': 0.1, 'love': 0.1, 'american': 0.2, 'british': 0.2
        }
    
    def _make_request(self, params: Dict[str, Any]) -> Optional[Dict]:
        """Make a request to Last.fm API"""
        
        try:
            # Add common parameters
            params.update({
                'api_key': self.api_key,
                'format': 'json'
            })
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Last.fm API error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"   ❌ Last.fm JSON decode error: {e}")
            return None
    
    def search_artist(self, artist_name: str, limit: int = 1) -> Optional[Dict]:
        """Search for an artist on Last.fm"""
        
        params = {
            'method': 'artist.search',
            'artist': artist_name,
            'limit': limit
        }
        
        response = self._make_request(params)
        
        if response and 'results' in response:
            artists = response['results'].get('artistmatches', {}).get('artist', [])
            
            # Handle single artist vs list
            if isinstance(artists, dict):
                artists = [artists]
            
            if artists:
                return artists[0]
        
        return None
    
    def get_artist_info(self, artist_name: str) -> Optional[Dict]:
        """Get detailed artist information"""
        
        params = {
            'method': 'artist.getInfo',
            'artist': artist_name
        }
        
        response = self._make_request(params)
        
        if response and 'artist' in response:
            return response['artist']
        
        return None
    
    def get_artist_tags(self, artist_name: str, limit: int = 20) -> List[Dict]:
        """Get community tags for an artist"""
        
        params = {
            'method': 'artist.getTopTags',
            'artist': artist_name,
            'limit': limit
        }
        
        response = self._make_request(params)
        
        if response and 'toptags' in response:
            tags = response['toptags'].get('tag', [])
            
            # Handle single tag vs list
            if isinstance(tags, dict):
                tags = [tags]
            
            return tags
        
        return []
    
    def get_similar_artists(self, artist_name: str, limit: int = 10) -> List[Dict]:
        """Get similar artists for genre context"""
        
        params = {
            'method': 'artist.getSimilar',
            'artist': artist_name,
            'limit': limit
        }
        
        response = self._make_request(params)
        
        if response and 'similarartists' in response:
            artists = response['similarartists'].get('artist', [])
            
            # Handle single artist vs list
            if isinstance(artists, dict):
                artists = [artists]
            
            return artists
        
        return []
    
    def analyze_genre_relevance(self, tags: List[Dict]) -> List[Dict]:
        """Analyze genre relevance of Last.fm tags"""
        
        genre_tags = []
        
        for tag in tags:
            tag_name = tag.get('name', '').lower()
            tag_count = int(tag.get('count', 0))
            
            # Check if tag is genre-relevant
            relevance = 0.0
            
            # Exact match
            if tag_name in self.genre_relevance_weights:
                relevance = self.genre_relevance_weights[tag_name]
            else:
                # Partial match - check if tag contains genre keywords
                for genre_keyword, weight in self.genre_relevance_weights.items():
                    if genre_keyword in tag_name or tag_name in genre_keyword:
                        relevance = max(relevance, weight * 0.8)  # Slightly lower for partial matches
            
            if relevance > 0.3:  # Only include relevant tags
                genre_tags.append({
                    'name': tag_name,
                    'count': tag_count,
                    'relevance': relevance,
                    'confidence': min(relevance * (tag_count / 100), 1.0)  # Scale by usage
                })
        
        # Sort by confidence score
        genre_tags.sort(key=lambda x: x['confidence'], reverse=True)
        
        return genre_tags
    
    def extract_comprehensive_genre_data(self, artist_name: str) -> Dict[str, Any]:
        """Extract comprehensive genre data from Last.fm"""
        
        print(f"   🎵 Extracting Last.fm community data for {artist_name}...")
        
        # Get artist info
        artist_info = self.get_artist_info(artist_name)
        if not artist_info:
            print(f"   ❌ Artist not found on Last.fm")
            return {}
        
        # Get tags
        tags = self.get_artist_tags(artist_name, limit=30)
        
        # Analyze genre relevance
        genre_tags = self.analyze_genre_relevance(tags)
        
        # Get similar artists for context
        similar_artists = self.get_similar_artists(artist_name, limit=8)
        
        # Extract key metrics
        listeners = artist_info.get('stats', {}).get('listeners', 0)
        playcount = artist_info.get('stats', {}).get('playcount', 0)
        
        # Get top genre classifications
        top_genres = []
        for tag in genre_tags[:5]:  # Top 5 genre tags
            if tag['confidence'] > 0.4:  # Only high-confidence tags
                top_genres.append({
                    'name': tag['name'],
                    'confidence': tag['confidence'],
                    'community_support': tag['count']
                })
        
        return {
            'artist_name': artist_info.get('name', artist_name),
            'listeners': int(listeners) if listeners else 0,
            'playcount': int(playcount) if playcount else 0,
            'genre_tags': genre_tags,
            'top_genres': top_genres,
            'similar_artists': [a.get('name', '') for a in similar_artists[:5]],
            'bio_summary': artist_info.get('bio', {}).get('summary', ''),
            'lastfm_url': artist_info.get('url', '')
        }
    
    def get_genre_consensus(self, artist_name: str) -> Dict[str, Any]:
        """Get community consensus on artist's genre"""
        
        data = self.extract_comprehensive_genre_data(artist_name)
        
        if not data or not data['top_genres']:
            return {'consensus': 'unknown', 'confidence': 0.0}
        
        # Calculate consensus
        top_genre = data['top_genres'][0]
        
        # Check if there's strong consensus (top genre has significantly higher confidence)
        if len(data['top_genres']) > 1:
            confidence_gap = top_genre['confidence'] - data['top_genres'][1]['confidence']
            if confidence_gap > 0.3:
                consensus_strength = 'strong'
            elif confidence_gap > 0.1:
                consensus_strength = 'moderate'
            else:
                consensus_strength = 'weak'
        else:
            consensus_strength = 'single'
        
        return {
            'consensus': top_genre['name'],
            'confidence': top_genre['confidence'],
            'consensus_strength': consensus_strength,
            'alternative_genres': [g['name'] for g in data['top_genres'][1:3]],
            'community_data': data
        }

def test_lastfm_genre_client():
    """Test the Last.fm genre client"""
    
    client = LastFmGenreClient()
    
    test_artists = [
        "Taylor Swift",
        "Drake", 
        "Billie Eilish"
    ]
    
    for artist_name in test_artists:
        print(f"\n🎵 TESTING LAST.FM INTEGRATION: {artist_name}")
        print("=" * 60)
        
        data = client.extract_comprehensive_genre_data(artist_name)
        
        if data:
            print(f"   ✅ Found: {data['artist_name']}")
            print(f"   👥 Listeners: {data['listeners']:,}")
            print(f"   🎧 Playcount: {data['playcount']:,}")
            
            if data['top_genres']:
                print(f"   🏷️  Top Community Genres:")
                for genre in data['top_genres'][:3]:
                    print(f"      - {genre['name']}: {genre['confidence']:.2f} confidence ({genre['community_support']} votes)")
            
            if data['similar_artists']:
                print(f"   🔗 Similar Artists: {', '.join(data['similar_artists'])}")
            
            # Get consensus
            consensus = client.get_genre_consensus(artist_name)
            print(f"   🎯 Community Consensus: {consensus['consensus']} ({consensus['consensus_strength']} consensus)")
            
        else:
            print(f"   ❌ No Last.fm data found")
        
        print()
        
        # Rate limiting
        time.sleep(1)

if __name__ == "__main__":
    test_lastfm_genre_client()
