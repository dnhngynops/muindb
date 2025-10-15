"""
Genius API Client for fetching song credits and metadata.
Handles authentication, rate limiting, and data extraction from Genius API.
"""

import time
import requests
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class GeniusResult:
    """Result from Genius API call."""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    rate_limited: bool = False


class GeniusClient:
    """Client for Genius API with rate limiting and error handling."""
    
    BASE_URL = "https://api.genius.com"
    USER_AGENT = "BillboardMusicDatabase/2.0 (https://github.com/your-repo)"
    RATE_LIMIT_DELAY = 0.2  # 0.2 seconds between requests (optimized)
    
    def __init__(self, access_token: str = None):
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT
        })
        if access_token:
            # Genius API uses access_token parameter, not Authorization header
            self.access_token = access_token
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Ensure we don't exceed the rate limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.RATE_LIMIT_DELAY:
            sleep_time = self.RATE_LIMIT_DELAY - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> GeniusResult:
        """Make a request to Genius API with rate limiting."""
        self._rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        # Add access_token to params if available
        if self.access_token:
            if params is None:
                params = {}
            params['access_token'] = self.access_token
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 429:  # Rate limited
                retry_after = int(response.headers.get('Retry-After', 5))
                logger.warning(f"Rate limited by Genius API, retrying after {retry_after} seconds")
                time.sleep(retry_after)
                return self._make_request(endpoint, params)  # Retry
            
            if response.status_code == 401:  # Unauthorized
                logger.error("Genius API authentication failed")
                return GeniusResult(success=False, error="Authentication failed")
            
            if response.status_code == 404:
                logger.debug(f"No results found for {endpoint}")
                return GeniusResult(success=False, error="Not found")
            
            if response.status_code != 200:
                logger.error(f"Genius API error: {response.status_code} - {response.text}")
                return GeniusResult(success=False, error=f"HTTP {response.status_code}")
            
            return GeniusResult(success=True, data=response.json())
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return GeniusResult(success=False, error=str(e))
    
    def search_song(self, song_name: str, artist_name: str) -> GeniusResult:
        """Search for a song by name and artist."""
        query = f"{song_name} {artist_name}"
        params = {
            'q': query,
            'per_page': 5
        }
        
        logger.debug(f"Searching Genius for: {song_name} by {artist_name}")
        return self._make_request('search', params)
    
    def generate_artist_variations(self, artist_name: str) -> list:
        """Generate multiple variations of artist name for better search results."""
        variations = [artist_name]  # Start with original
        
        # Remove "feat." and everything after it
        if ' feat.' in artist_name.lower():
            main_artist = artist_name.split(' feat.')[0].strip()
            variations.append(main_artist)
        
        # Remove "featuring" and everything after it
        if ' featuring' in artist_name.lower():
            main_artist = artist_name.split(' featuring')[0].strip()
            variations.append(main_artist)
        
        # Remove "presents" and everything after it
        if ' presents' in artist_name.lower():
            main_artist = artist_name.split(' presents')[0].strip()
            variations.append(main_artist)
        
        # Remove "&" and everything after it
        if ' & ' in artist_name:
            main_artist = artist_name.split(' & ')[0].strip()
            variations.append(main_artist)
        
        # Remove "and" and everything after it
        if ' and ' in artist_name.lower():
            main_artist = artist_name.split(' and ')[0].strip()
            variations.append(main_artist)
        
        # Try just the first word (for groups like "Tha Eastsidaz")
        first_word = artist_name.split()[0] if artist_name.split() else artist_name
        if len(first_word) > 2:  # Only if it's a meaningful word
            variations.append(first_word)
        
        # Try first two words
        words = artist_name.split()
        if len(words) >= 2:
            first_two = ' '.join(words[:2])
            variations.append(first_two)
        
        # Remove common prefixes
        prefixes_to_remove = ['the ', 'tha ', 'da ', 'de ', 'le ', 'la ']
        for prefix in prefixes_to_remove:
            if artist_name.lower().startswith(prefix):
                without_prefix = artist_name[len(prefix):].strip()
                variations.append(without_prefix)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for variation in variations:
            if variation and variation not in seen:
                seen.add(variation)
                unique_variations.append(variation)
        
        return unique_variations
    
    def improved_search_song(self, song_name: str, artist_name: str) -> GeniusResult:
        """Search for a song using multiple artist name variations for better results."""
        logger.debug(f"Improved search for: {song_name} by {artist_name}")
        
        # Generate artist variations
        variations = self.generate_artist_variations(artist_name)
        logger.debug(f"Trying {len(variations)} artist name variations")
        
        # Try each variation
        for variation in variations:
            search_result = self.search_song(song_name, variation)
            
            if search_result.success:
                hits = search_result.data.get('response', {}).get('hits', [])
                
                if hits:
                    # Check if any result matches our song
                    for hit in hits:
                        result = hit['result']
                        result_title = result.get('title', '').lower()
                        result_artist = result.get('primary_artist', {}).get('name', '').lower()
                        
                        # Check for title match (flexible matching)
                        if (song_name.lower() in result_title or 
                            result_title in song_name.lower() or
                            song_name.lower().replace("'", "'") in result_title or
                            result_title.replace("'", "'") in song_name.lower()):
                            logger.debug(f"Found match with variation: {variation}")
                            return search_result
            else:
                logger.debug(f"Search failed for variation '{variation}': {search_result.error}")
        
        logger.warning(f"No matches found for {song_name} by {artist_name} with any variation")
        return GeniusResult(success=False, error="No matches found with any artist variation")
    
    def get_song_details(self, song_id: int) -> Optional[Dict]:
        """Get detailed song information from Genius"""
        try:
            url = f"{self.BASE_URL}/songs/{song_id}"
            params = {'access_token': self.access_token} if self.access_token else {}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            song_details = response.json()['response']['song']
            
            producers = song_details.get('producer_artists', [])
            producer_names = [p['name'] for p in producers]
            
            writers = song_details.get('writer_artists', [])
            writer_names = [w['name'] for w in writers]
            
            custom_performances = song_details.get('custom_performances', [])
            for performance in custom_performances:
                if 'writer' in performance['label'].lower():
                    writer_names.extend([a['name'] for a in performance['artists']])
            
            return {
                'producers': ', '.join(set(producer_names)) if producer_names else 'Information not available',
                'writers': ', '.join(set(writer_names)) if writer_names else 'Information not available',
                'source': 'genius'
            }
            
        except Exception as e:
            logger.error(f"Error getting song details for ID {song_id}: {e}")
            return None
    
    def get_credits(self, title: str, artist: str) -> Dict:
        """Main method for getting credits with improved reliability"""
        logger.info(f"Getting credits for: {title} by {artist}")
        
        # Try Genius first (most reliable)
        try:
            # Use improved search with multiple artist variations
            search_result = self.improved_search_song(title, artist)
            if not search_result.success:
                logger.warning(f"Failed to search Genius: {search_result.error}")
                return self._get_fallback_credits()
            
            hits = search_result.data.get('response', {}).get('hits', [])
            if not hits:
                logger.warning(f"No songs found on Genius for: {title} by {artist}")
                return self._get_fallback_credits()
            
            # Get the first (most relevant) result
            song_hit = hits[0]
            song_id = song_hit['result']['id']
            
            # Get detailed song information
            song_details = self.get_song_details(song_id)
            if song_details:
                logger.info(f"✅ SUCCESS - Writers: {song_details.get('writers', 'N/A')}")
                logger.info(f"✅ SUCCESS - Producers: {song_details.get('producers', 'N/A')}")
                return song_details
            else:
                logger.warning("Failed to get song details from Genius")
                return self._get_fallback_credits()
                
        except Exception as e:
            logger.error(f"Genius error: {e}")
            return self._get_fallback_credits()
    
    def _get_fallback_credits(self) -> Dict:
        """Return fallback credits when all methods fail"""
        return {
            'writers': 'Information not available',
            'producers': 'Information not available',
            'source': 'failed'
        }
    
    def get_artist_details(self, artist_id: int) -> GeniusResult:
        """Get detailed information about an artist."""
        params = {
            'per_page': 50,
            'sort': 'popularity'
        }
        
        logger.debug(f"Getting artist details for ID: {artist_id}")
        return self._make_request(f'artists/{artist_id}/songs', params)


class GeniusDataExtractor:
    """Extract and normalize data from Genius API responses."""
    
    @staticmethod
    def extract_song_credits(song_data: Dict) -> List[Dict]:
        """Extract credits from song data."""
        credits = []
        
        if 'response' not in song_data or 'song' not in song_data['response']:
            return credits
        
        song = song_data['response']['song']
        
        # Extract primary artist
        if 'primary_artist' in song:
            artist = song['primary_artist']
            credits.append({
                'name': artist['name'],
                'id': artist['id'],
                'role': 'Artist',
                'source': 'genius'
            })
        
        # Extract featured artists
        if 'featured_artists' in song and song['featured_artists']:
            for artist in song['featured_artists']:
                credits.append({
                    'name': artist['name'],
                    'id': artist['id'],
                    'role': 'Featured Artist',
                    'source': 'genius'
                })
        
        # Extract songwriters (from song description or lyrics)
        # Note: Genius doesn't always have structured songwriter data
        # We'll extract from the song description if available
        if 'description' in song and song['description'] and isinstance(song['description'], str):
            description = song['description']
            # Look for common patterns in descriptions
            if 'written by' in description.lower():
                # Extract writer names from description
                # This is a simplified approach - in practice, you'd need more sophisticated parsing
                pass
        
        # Extract producer information (if available in description)
        if 'description' in song and song['description'] and isinstance(song['description'], str):
            description = song['description']
            if 'produced by' in description.lower():
                # Extract producer names from description
                # This is a simplified approach - in practice, you'd need more sophisticated parsing
                pass
        
        return credits
    
    @staticmethod
    def extract_song_metadata(song_data: Dict) -> Dict:
        """Extract general song metadata."""
        if 'response' not in song_data or 'song' not in song_data['response']:
            return {}
        
        song = song_data['response']['song']
        
        return {
            'genius_id': song.get('id'),
            'title': song.get('title'),
            'full_title': song.get('full_title'),
            'artist': song.get('primary_artist', {}).get('name'),
            'release_date': song.get('release_date_for_display'),
            'lyrics_state': song.get('lyrics_state'),
            'pyongs_count': song.get('pyongs_count', 0),
            'hot': song.get('hot', False),
            'description': song.get('description', ''),
            'url': song.get('url')
        }
    
    @staticmethod
    def normalize_credit_name(name: str) -> str:
        """Normalize credit name for matching."""
        # Remove common suffixes and normalize
        name = name.strip()
        
        # Remove "feat." and similar
        if ' feat.' in name.lower():
            name = name.split(' feat.')[0]
        
        # Remove "featuring" and similar
        if ' featuring' in name.lower():
            name = name.split(' featuring')[0]
        
        # Remove "&" and replace with "and"
        name = name.replace(' & ', ' and ')
        
        # Convert to lowercase for consistent matching
        return name.strip().lower()
    


class GeniusService:
    """High-level service for fetching and processing Genius metadata."""
    
    def __init__(self, access_token: str = None):
        # Get token from environment if not provided
        if access_token is None:
            import os
            access_token = os.getenv('GENIUS_ACCESS_TOKEN')
        
        self.client = GeniusClient(access_token)
        self.extractor = GeniusDataExtractor()
    
    def get_song_metadata(self, song_name: str, artist_name: str) -> Dict:
        """Get complete metadata for a song including credits using improved methods."""
        logger.info(f"Fetching Genius metadata for: {song_name} by {artist_name}")
        
        # Use the improved get_credits method
        credits_data = self.client.get_credits(song_name, artist_name)
        
        # Parse credits into our expected format
        credits = []
        
        # Add writers
        if credits_data.get('writers') and credits_data['writers'] != 'Information not available':
            writer_names = [name.strip() for name in credits_data['writers'].split(',')]
            for writer_name in writer_names:
                if writer_name and writer_name != 'Information not available':
                    credits.append({
                        'name': writer_name,
                        'id': None,  # Genius doesn't always provide IDs for writers
                        'role': 'Writer',
                        'source': 'genius'
                    })
        
        # Add producers
        if credits_data.get('producers') and credits_data['producers'] != 'Information not available':
            producer_names = [name.strip() for name in credits_data['producers'].split(',')]
            for producer_name in producer_names:
                if producer_name and producer_name != 'Information not available':
                    credits.append({
                        'name': producer_name,
                        'id': None,  # Genius doesn't always provide IDs for producers
                        'role': 'Producer',
                        'source': 'genius'
                    })
        
        # Note: We don't add artist names as credits here
        # Artist information is already stored in the songs table
        # Credits should only include writers, producers, engineers, etc.
        
        # Get basic song metadata from improved search
        search_result = self.client.improved_search_song(song_name, artist_name)
        metadata = {}
        genius_id = None
        
        if search_result.success:
            hits = search_result.data.get('response', {}).get('hits', [])
            if hits:
                song_hit = hits[0]['result']
                genius_id = song_hit.get('id')
                metadata = {
                    'title': song_hit.get('title', song_name),
                    'artist': song_hit.get('primary_artist', {}).get('name', artist_name),
                    'genius_id': genius_id,
                    'url': song_hit.get('url'),
                    'pyongs_count': song_hit.get('pyongs_count', 0),
                    'hot': song_hit.get('hot', False),
                    'description': song_hit.get('description', '')
                }
        
        logger.info(f"Found {len(credits)} credits")
        
        return {
            'credits': credits,
            'metadata': metadata,
            'genius_id': genius_id,
            'error': None if credits_data.get('source') != 'failed' else 'Failed to get credits'
        }
    
    def batch_get_metadata(self, songs: List[Tuple[str, str]], delay_between_songs: float = 1.0) -> List[Dict]:
        """Get metadata for multiple songs with batching."""
        results = []
        
        for i, (song_name, artist_name) in enumerate(songs):
            logger.info(f"Processing song {i+1}/{len(songs)}: {song_name} by {artist_name}")
            
            metadata = self.get_song_metadata(song_name, artist_name)
            metadata['song_name'] = song_name
            metadata['artist_name'] = artist_name
            results.append(metadata)
            
            # Add delay between songs to be respectful
            if i < len(songs) - 1:
                time.sleep(delay_between_songs)
        
        return results
