#!/usr/bin/env python3
"""
Spotify Genre Client for Billboard Music Database
Extract genre classifications and audio features from Spotify API
Adapted from ARI project for Billboard database structure
"""

import os
import sys
import json
import time
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Dict, List, Optional, Any

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

class SpotifyGenreClient:
    """
    Spotify API client for extracting genre classifications and audio features
    Adapted for Billboard Music Database
    """
    
    def __init__(self):
        # Get credentials from environment
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ValueError("Spotify credentials not found in environment variables")
        
        # Initialize Spotify client
        client_credentials_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        
        self.sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        
        # Audio feature to genre mapping
        self.audio_feature_genres = {
            'high_energy_electronic': {'energy': 0.8, 'danceability': 0.7, 'valence': 0.6},
            'chill_electronic': {'energy': 0.3, 'danceability': 0.6, 'valence': 0.4},
            'aggressive_rock': {'energy': 0.9, 'loudness': -5, 'tempo': 120},
            'acoustic_folk': {'acousticness': 0.8, 'energy': 0.4, 'instrumentalness': 0.3},
            'hip_hop_modern': {'energy': 0.7, 'speechiness': 0.4, 'tempo': 80},
            'pop_mainstream': {'danceability': 0.7, 'energy': 0.6, 'valence': 0.6}
        }
    
    @staticmethod
    def _generate_artist_name_variations(artist_name: str) -> List[str]:
        """
        Generate multiple variations of an artist name to improve Spotify search success.
        
        Handles common formatting issues:
        - 'n sync → NSYNC, *NSYNC, N Sync
        - 3lw → 3LW, Three LW
        - 2pac → 2Pac, Tupac
        - Special character variations
        
        Returns list of variations to try, ordered by likelihood
        """
        import re
        
        variations = []
        original = artist_name.strip()
        variations.append(original)  # Always try original first
        
        # 1. Remove leading apostrophes: 'n sync → n sync
        if original.startswith("'"):
            variations.append(original[1:])
            # Also try uppercase: 'n sync → NSYNC
            variations.append(original[1:].upper())
            # Try with space: 'n sync → N Sync
            variations.append(original[1:].title())
        
        # 2. Uppercase version: 3lw → 3LW
        if original.lower() != original:
            variations.append(original.upper())
        
        # 3. Title case: eminem → Eminem
        variations.append(original.title())
        
        # 4. Remove special characters: 2pac → 2Pac
        cleaned = re.sub(r'[^\w\s]', '', original)
        if cleaned != original:
            variations.append(cleaned)
            variations.append(cleaned.title())
        
        # 5. Replace numbers with words at start: 2pac → Two Pac
        number_words = {
            '2': 'Two', '3': 'Three', '4': 'Four', '5': 'Five',
            '6': 'Six', '7': 'Seven', '8': 'Eight', '9': 'Nine'
        }
        for num, word in number_words.items():
            if original.startswith(num):
                variations.append(word + original[1:])
                variations.append((word + original[1:]).title())
        
        # 6. Remove "the" prefix: the beatles → beatles
        if original.lower().startswith('the '):
            variations.append(original[4:])
        
        # 7. Add common prefixes for special cases
        if original.lower().startswith('n sync'):
            variations.extend(['NSYNC', '*NSYNC', 'NSync', 'N-Sync'])
        
        if original == '3lw':
            variations.extend(['3LW', 'Three LW', 'ThreeLW'])
        
        if original.startswith('2pac'):
            variations.extend(['2Pac', 'Tupac', 'Tupac Shakur'])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for v in variations:
            v_lower = v.lower()
            if v_lower not in seen:
                seen.add(v_lower)
                unique_variations.append(v)
        
        return unique_variations
    
    @staticmethod
    def _calculate_match_score(artist_result: Dict, search_name: str) -> float:
        """
        Calculate a match score for an artist result.
        Higher score = better match.
        
        Factors:
        - Name similarity (most important)
        - Popularity (Billboard artists should have some recognition)
        - Exact name match bonus
        """
        from difflib import SequenceMatcher
        
        spotify_name = artist_result.get('name', '').lower()
        search_name_lower = search_name.lower()
        popularity = artist_result.get('popularity', 0)
        
        # Clean both names for comparison (remove special chars)
        clean_spotify = spotify_name.replace("'", "").replace(" ", "").replace("-", "").replace("*", "")
        clean_search = search_name_lower.replace("'", "").replace(" ", "").replace("-", "")
        
        # Calculate base similarity
        similarity = SequenceMatcher(None, clean_spotify, clean_search).ratio()
        
        # Score components
        score = 0.0
        
        # Name similarity (0-50 points)
        if similarity >= 0.9:  # Near perfect match
            score += 50
        elif similarity >= 0.7:  # Good match
            score += 40
        elif similarity >= 0.5:  # Acceptable match
            score += 25
        else:  # Poor match
            score += similarity * 20  # Proportional
        
        # Exact substring match bonus (0-20 points)
        if clean_search in clean_spotify or clean_spotify in clean_search:
            score += 20
        elif search_name_lower in spotify_name or spotify_name in search_name_lower:
            score += 15
        
        # Popularity bonus (0-20 points)
        # Billboard artists typically have popularity 30-100
        if popularity >= 50:
            score += 20
        elif popularity >= 30:
            score += 15
        elif popularity >= 20:
            score += 10
        elif popularity >= 10:
            score += 5
        # Below 10 popularity gets no bonus (but doesn't hurt if name match is good)
        
        # Genre data bonus (0-10 points)
        if artist_result.get('genres'):
            score += 10
        
        return score
    
    def search_artist(self, artist_name: str, limit: int = 10) -> Optional[Dict]:
        """
        Search for an artist and return Spotify data.
        Tries multiple name variations to improve success rate.
        Returns the best matching result based on scoring.
        """
        
        # Generate variations of the artist name
        variations = self._generate_artist_name_variations(artist_name)
        
        # Collect all candidates with their scores
        all_candidates = []
        
        # Try each variation and collect scored results
        for i, variation in enumerate(variations):
            try:
                # Search with limit=10 to get multiple candidates
                results = self.sp.search(q=f'artist:{variation}', type='artist', limit=limit)
                
                if results['artists']['items']:
                    # Score each candidate
                    for candidate in results['artists']['items']:
                        score = self._calculate_match_score(candidate, artist_name)
                        all_candidates.append({
                            'artist': candidate,
                            'score': score,
                            'variation': variation,
                            'variation_index': i
                        })
                
            except Exception as e:
                # Only print error on last attempt
                if i == len(variations) - 1 and not all_candidates:
                    print(f"   ❌ Spotify search error: {e}")
                continue
        
        if not all_candidates:
            return None
        
        # Sort by score (highest first)
        all_candidates.sort(key=lambda x: x['score'], reverse=True)
        best = all_candidates[0]
        
        # Require minimum score of 40 (out of 100) to accept
        if best['score'] < 40:
            return None
        
        # Log if we used a variation
        if best['variation_index'] > 0:
            print(f"   ℹ️  Found via variation: '{artist_name}' → '{best['variation']}' = '{best['artist']['name']}' (score: {best['score']:.1f})")
        
        return best['artist']
    
    def get_artist_genres(self, artist_id: str) -> List[str]:
        """Get genre classifications for an artist"""
        
        try:
            artist = self.sp.artist(artist_id)
            return artist.get('genres', [])
            
        except Exception as e:
            print(f"   ❌ Spotify artist error: {e}")
            return []
    
    def get_artist_top_tracks(self, artist_id: str, country: str = 'US') -> List[Dict]:
        """Get top tracks for an artist"""
        
        try:
            results = self.sp.artist_top_tracks(artist_id, country=country)
            return results.get('tracks', [])
            
        except Exception as e:
            print(f"   ❌ Spotify top tracks error: {e}")
            return []
    
    def get_audio_features(self, track_ids: List[str]) -> List[Dict]:
        """Get audio features for multiple tracks with enhanced error handling"""
        
        try:
            # Try batch request first
            all_features = []
            
            for i in range(0, len(track_ids), 100):
                batch = track_ids[i:i+100]
                try:
                    features = self.sp.audio_features(batch)
                    all_features.extend([f for f in features if f is not None])
                except Exception as batch_error:
                    print(f"   ⚠️  Batch audio features failed: {batch_error}")
                    # Try individual requests as fallback
                    for track_id in batch:
                        try:
                            feature = self.sp.audio_features([track_id])
                            if feature and feature[0]:
                                all_features.append(feature[0])
                        except Exception as individual_error:
                            print(f"   ⚠️  Individual audio feature failed for {track_id}: {individual_error}")
                            continue
            
            return all_features
            
        except Exception as e:
            print(f"   ❌ Audio features completely unavailable: {e}")
            print(f"   ℹ️  Continuing without audio features...")
            return []
    
    def analyze_artist_audio_profile(self, artist_id: str) -> Dict[str, Any]:
        """Analyze artist's audio profile for genre inference"""
        
        try:
            # Get top tracks
            top_tracks = self.get_artist_top_tracks(artist_id)
            
            if not top_tracks:
                return {
                    'error': 'No top tracks found',
                    'track_count': 0,
                    'feature_count': 0
                }
            
            # Get audio features (may fail)
            track_ids = [track['id'] for track in top_tracks]
            features = self.get_audio_features(track_ids)
            
            # Always return track info, even if audio features fail
            result = {
                'track_count': len(top_tracks),
                'feature_count': len(features),
                'top_tracks': [
                    {
                        'name': track['name'],
                        'id': track['id'],
                        'popularity': track.get('popularity', 0),
                        'explicit': track.get('explicit', False)
                    } for track in top_tracks[:5]  # First 5 tracks
                ]
            }
            
            if features:
                # Calculate average audio features
                avg_features = {}
                feature_keys = ['danceability', 'energy', 'speechiness', 'acousticness', 
                              'instrumentalness', 'liveness', 'valence', 'tempo', 'loudness']
                
                for key in feature_keys:
                    values = [f[key] for f in features if f and key in f]
                    avg_features[key] = sum(values) / len(values) if values else 0
                
                # Infer genres from audio features
                inferred_genres = self._infer_genres_from_features(avg_features)
                
                result.update({
                    'average_features': avg_features,
                    'inferred_genres': inferred_genres
                })
            else:
                print(f"   ℹ️  No audio features available - using track-based analysis")
                # Fallback: Use track names and popularity for basic inference
                result.update({
                    'average_features': {},
                    'inferred_genres': [],
                    'fallback_analysis': self._analyze_tracks_without_features(top_tracks)
                })
            
            return result
            
        except Exception as e:
            print(f"   ❌ Audio profile analysis error: {e}")
            return {
                'error': str(e),
                'track_count': 0,
                'feature_count': 0
            }
    
    def _analyze_tracks_without_features(self, tracks: List[Dict]) -> Dict[str, Any]:
        """Analyze tracks without audio features using track metadata"""
        
        analysis = {
            'average_popularity': 0,
            'explicit_ratio': 0,
            'track_names': [],
            'inferred_characteristics': []
        }
        
        if not tracks:
            return analysis
        
        # Calculate basic metrics
        popularities = [track.get('popularity', 0) for track in tracks]
        analysis['average_popularity'] = sum(popularities) / len(popularities)
        
        explicit_count = sum(1 for track in tracks if track.get('explicit', False))
        analysis['explicit_ratio'] = explicit_count / len(tracks)
        
        analysis['track_names'] = [track['name'] for track in tracks[:5]]
        
        # Basic genre inference from track characteristics
        if analysis['average_popularity'] > 70:
            analysis['inferred_characteristics'].append('mainstream_appeal')
        elif analysis['average_popularity'] < 30:
            analysis['inferred_characteristics'].append('underground')
        
        if analysis['explicit_ratio'] > 0.5:
            analysis['inferred_characteristics'].append('explicit_content')
        
        return analysis
    
    def _infer_genres_from_features(self, features: Dict[str, float]) -> List[Dict[str, Any]]:
        """Infer genres based on audio features"""
        
        inferred = []
        
        for genre, thresholds in self.audio_feature_genres.items():
            score = 0
            matches = 0
            
            for feature, threshold in thresholds.items():
                if feature in features:
                    if features[feature] >= threshold:
                        score += 1
                    matches += 1
            
            if matches > 0:
                confidence = score / matches
                if confidence >= 0.5:  # At least 50% match
                    inferred.append({
                        'genre': genre,
                        'confidence': confidence,
                        'matching_features': matches,
                        'score': score
                    })
        
        # Sort by confidence
        inferred.sort(key=lambda x: x['confidence'], reverse=True)
        
        return inferred
    
    def get_artist_playlist_context(self, artist_name: str, limit: int = 10) -> List[Dict]:
        """Get playlist context for genre inference"""
        
        try:
            # Search for playlists featuring the artist
            results = self.sp.search(q=artist_name, type='playlist', limit=limit)
            
            playlists = []
            for playlist in results['playlists']['items']:
                if playlist and playlist.get('name'):
                    playlists.append({
                        'name': playlist['name'],
                        'description': playlist.get('description', ''),
                        'owner': playlist.get('owner', {}).get('display_name', ''),
                        'follower_count': playlist.get('followers', {}).get('total', 0)
                    })
            
            return playlists
            
        except Exception as e:
            print(f"   ❌ Playlist context error: {e}")
            return []
    
    def extract_comprehensive_genre_data(self, artist_name: str) -> Dict[str, Any]:
        """Extract comprehensive genre data from Spotify with enhanced analysis"""
        
        try:
            # Search for artist
            results = self.sp.search(q=artist_name, type='artist', limit=1)
            if not results['artists']['items']:
                return None
            
            artist = results['artists']['items'][0]
            artist_id = artist['id']
            
            # Get basic artist data
            spotify_data = {
                'artist_id': artist_id,
                'artist_name': artist['name'],
                'popularity': artist['popularity'],
                'followers': artist['followers']['total'],
                'spotify_genres': artist['genres'],
                'external_urls': artist['external_urls']
            }
            
            # Get top tracks for additional context
            top_tracks = self.get_artist_top_tracks(artist_id)
            if top_tracks:
                spotify_data['top_tracks'] = top_tracks
                
                # Enhanced track-based analysis
                track_analysis = self._analyze_tracks_without_audio_features(top_tracks)
                if track_analysis:
                    spotify_data['track_analysis'] = track_analysis
            
            return spotify_data
            
        except Exception as e:
            print(f"   ❌ Error in Spotify extraction: {e}")
            return None
    
    def _analyze_tracks_without_audio_features(self, tracks: List[Dict]) -> Dict[str, Any]:
        """Analyze tracks using available data (no audio features needed)"""
        
        analysis = {
            'track_count': len(tracks),
            'track_popularity_avg': 0,
            'collaboration_count': 0,
            'track_themes': []
        }
        
        if not tracks:
            return analysis
        
        # Calculate average popularity
        popularities = [track.get('popularity', 0) for track in tracks]
        analysis['track_popularity_avg'] = sum(popularities) / len(popularities)
        
        # Count collaborations (featuring, with, etc.)
        collaboration_keywords = ['feat.', 'featuring', 'with', 'ft.', '&']
        for track in tracks:
            track_name = track.get('name', '').lower()
            if any(keyword in track_name for keyword in collaboration_keywords):
                analysis['collaboration_count'] += 1
        
        # Extract potential themes from track names
        common_themes = ['love', 'night', 'life', 'world', 'heart', 'time', 'dream', 'light', 'soul']
        for track in tracks:
            track_name = track.get('name', '').lower()
            for theme in common_themes:
                if theme in track_name and theme not in analysis['track_themes']:
                    analysis['track_themes'].append(theme)
        
        return analysis

def test_spotify_genre_client():
    """Test the Spotify genre client"""
    
    client = SpotifyGenreClient()
    
    test_artists = [
        "Taylor Swift",
        "Drake",
        "Billie Eilish"
    ]
    
    for artist_name in test_artists:
        print(f"\n🎵 TESTING SPOTIFY INTEGRATION: {artist_name}")
        print("=" * 60)
        
        data = client.extract_comprehensive_genre_data(artist_name)
        
        if data:
            print(f"   ✅ Found: {data['artist_name']}")
            print(f"   📊 Popularity: {data['popularity']}/100")
            print(f"   👥 Followers: {data['followers']:,}")
            print(f"   🎵 Spotify Genres: {', '.join(data['spotify_genres']) if data['spotify_genres'] else 'None'}")
            
            if 'track_analysis' in data:
                print(f"   🎧 Track Analysis: {data['track_analysis']['track_count']} tracks analyzed")
                print(f"   📈 Avg Popularity: {data['track_analysis']['track_popularity_avg']:.1f}")
                print(f"   🤝 Collaborations: {data['track_analysis']['collaboration_count']}")
        else:
            print(f"   ❌ No Spotify data found")
        
        print()

if __name__ == "__main__":
    test_spotify_genre_client()
