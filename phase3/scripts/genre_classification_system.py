#!/usr/bin/env python3
"""
Multi-Source Genre Classification System for Billboard Music Database
A&R-grade precision through weighted reasoning across multiple data sources
Adapted from ARI project for Billboard database structure
"""

import os
import sys
import logging
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file."""
    env_file = project_root / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load .env file
load_env_file()

from database.connection import get_database_manager
from database.models import Songs, Artists
from database.phase2_models import Genres, SongGenres
from database.spotify_models import SpotifyTracks, SongSpotifyGenres, SpotifyGenres
from api.chartmetric_client import ChartmetricClient
from api.spotify_genre_client import SpotifyGenreClient
from api.lastfm_genre_client import LastFmGenreClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class GenreClassification:
    """Individual genre classification from a specific source"""
    name: str
    confidence: float
    source: str
    source_id: Optional[str] = None
    category: str = 'unknown'  # primary, secondary, sub, community, etc.
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ArtistGenreProfile:
    """Complete genre profile for an artist across all sources"""
    artist_name: str
    artist_id: Optional[str] = None
    classifications: List[GenreClassification] = field(default_factory=list)
    confidence_score: float = 0.0
    primary_genre: Optional[str] = None
    secondary_tags: List[str] = field(default_factory=list)  # Independent secondary genre tags
    crossover_indicators: List[str] = field(default_factory=list)
    a_and_r_insights: Dict[str, Any] = field(default_factory=dict)
    source_data: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class GenreResult:
    """Result of genre classification for an artist or song."""
    primary_genre: str
    secondary_tags: List[str]
    confidence_score: float
    sources: List[str]
    reasoning: str


class GenreClassificationSystem:
    """
    Multi-source genre classification system for A&R-grade precision
    
    Data Sources:
    1. Chartmetric (industry standard)
    2. Spotify API (algorithmic + audio features + playlist placement)
    3. Last.fm (community consensus)
    4. Genius (existing database data)
    """
    
    def __init__(self):
        # Initialize clients
        try:
            self.chartmetric_client = ChartmetricClient()
            self.chartmetric_available = True
        except Exception as e:
            logger.warning(f"Chartmetric API not available: {e}")
            self.chartmetric_client = None
            self.chartmetric_available = False
        
        # Initialize Spotify client (optional - depends on API keys)
        try:
            self.spotify_client = SpotifyGenreClient()
            self.spotify_available = True
        except Exception as e:
            logger.warning(f"Spotify API not available: {e}")
            self.spotify_client = None
            self.spotify_available = False
        
        # Initialize Last.fm client (optional - works with or without API key)
        try:
            self.lastfm_client = LastFmGenreClient()
            self.lastfm_available = True
        except Exception as e:
            logger.warning(f"Last.fm API not available: {e}")
            self.lastfm_client = None
            self.lastfm_available = False
        
        # Initialize database manager
        self.db_manager = get_database_manager()
        
        # Initialize caching
        self._classification_cache = {}  # In-memory cache for this session
        self.cache_file = project_root / 'phase3' / 'api_cache.json'
        self.api_cache = self._load_api_cache()
        
        # HIERARCHICAL GENRE SYSTEM
        # Primary Genres (fixed, broad categories for business/A&R purposes)
        self.primary_genres = [
            'pop', 'hip-hop', 'rock', 'alternative', 'country', 
            'electronic', 'r&b', 'latin', 'folk', 'jazz', 'other'
        ]
        
        # Primary Genre Mapping Rules (detailed genre -> primary genre)
        self.primary_genre_mapping = {
            # Pop variants
            'pop': 'pop',
            'dance pop': 'pop',
            'electropop': 'pop',
            'synth pop': 'pop',
            'teen pop': 'pop',
            'power pop': 'pop',
            'art pop': 'pop',
            'baroque pop': 'pop',
            'chamber pop': 'pop',
            
            # Hip-Hop variants
            'rap': 'hip-hop',
            'hip-hop': 'hip-hop',
            'hip hop': 'hip-hop',
            'trap': 'hip-hop',
            'pop rap': 'hip-hop',
            'melodic rap': 'hip-hop',
            'conscious hip hop': 'hip-hop',
            'old school hip hop': 'hip-hop',
            'east coast hip hop': 'hip-hop',
            'west coast hip hop': 'hip-hop',
            'southern hip hop': 'hip-hop',
            'drill': 'hip-hop',
            'grime': 'hip-hop',
            
            # Rock variants
            'rock': 'rock',
            'hard rock': 'rock',
            'classic rock': 'rock',
            'progressive rock': 'rock',
            'psychedelic rock': 'rock',
            'garage rock': 'rock',
            'blues rock': 'rock',
            'folk rock': 'rock',
            'pop rock': 'rock',
            'punk rock': 'rock',
            'metal': 'rock',
            'heavy metal': 'rock',
            
            # Alternative variants
            'alternative': 'alternative',
            'alternative rock': 'alternative',
            'indie': 'alternative',
            'indie rock': 'alternative',
            'indie pop': 'alternative',
            'alternative pop': 'alternative',
            'indie folk': 'alternative',
            'shoegaze': 'alternative',
            'post-punk': 'alternative',
            'post-rock': 'alternative',
            'emo': 'alternative',
            'grunge': 'alternative',
            'new wave': 'alternative',
            'britpop': 'alternative',
            
            # Country variants
            'country': 'country',
            'country pop': 'country',
            'new country': 'country',
            'country rock': 'country',
            'americana': 'country',
            'bluegrass': 'country',
            'country folk': 'country',
            
            # Electronic variants
            'electronic': 'electronic',
            'edm': 'electronic',
            'house': 'electronic',
            'techno': 'electronic',
            'trance': 'electronic',
            'dubstep': 'electronic',
            'ambient': 'electronic',
            'drum and bass': 'electronic',
            'breakbeat': 'electronic',
            'garage': 'electronic',
            'uk garage': 'electronic',
            'future bass': 'electronic',
            'synthwave': 'electronic',
            
            # R&B variants
            'r&b': 'r&b',
            'rnb': 'r&b',
            'rhythm and blues': 'r&b',
            'soul': 'r&b',
            'neo soul': 'r&b',
            'contemporary r&b': 'r&b',
            'funk': 'r&b',
            'gospel': 'r&b',
            'motown': 'r&b',
            
            # Latin variants
            'latin': 'latin',
            'reggaeton': 'latin',
            'latin pop': 'latin',
            'latin trap': 'latin',
            'salsa': 'latin',
            'bachata': 'latin',
            'merengue': 'latin',
            'cumbia': 'latin',
            'regional mexican': 'latin',
            'mariachi': 'latin',
            
            # Folk variants
            'folk': 'folk',
            'acoustic': 'folk',
            'singer-songwriter': 'folk',
            'contemporary folk': 'folk',
            'traditional folk': 'folk',
            'celtic': 'folk',
            'world music': 'folk',
            'world': 'folk',
            
            # Jazz variants
            'jazz': 'jazz',
            'smooth jazz': 'jazz',
            'bebop': 'jazz',
            'fusion': 'jazz',
            'acid jazz': 'jazz',
            'latin jazz': 'jazz',
            'big band': 'jazz',
            'swing': 'jazz',
            'cool jazz': 'jazz',
            'hard bop': 'jazz'
        }
        
        # Source weights for confidence scoring
        self.source_weights = {
            'chartmetric': 0.35,  # Industry standard
            'spotify': 0.30,      # Algorithmic + audio features
            'lastfm': 0.25,       # Community consensus
            'genius': 0.10        # Existing database data
        }
        
        # Cache for results
        self._classification_cache = {}
        
        logger.info("Genre Classification System initialized with ARI features")
    
    def _load_api_cache(self) -> Dict[str, Any]:
        """Load API cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    logger.info(f"Loaded API cache with {len(cache)} entries")
                    return cache
            except Exception as e:
                logger.warning(f"Failed to load API cache: {e}")
        return {}
    
    def _save_api_cache(self):
        """Save API cache to file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.api_cache, f, indent=2)
                logger.info(f"Saved API cache with {len(self.api_cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to save API cache: {e}")
    
    def _get_cached_response(self, source: str, query: str) -> Optional[Any]:
        """Get cached API response."""
        cache_key = f"{source}:{query.lower()}"
        return self.api_cache.get(cache_key)
    
    def _cache_response(self, source: str, query: str, response: Any):
        """Cache API response."""
        cache_key = f"{source}:{query.lower()}"
        self.api_cache[cache_key] = response
        # Save cache every 10 new entries
        if len(self.api_cache) % 10 == 0:
            self._save_api_cache()
    
    def _get_existing_classification(self, artist_name: str, year: str = None) -> Optional[ArtistGenreProfile]:
        """
        Check if artist already has a high-confidence classification in database.
        Only returns existing profile if ALL songs by the artist are classified.
        This ensures incomplete classifications are completed on subsequent runs.
        """
        try:
            with self.db_manager.get_session() as session:
                # Find ALL songs by this artist in the target year
                query = session.query(Songs).filter(
                    Songs.artist_name.ilike(f"%{artist_name}%")
                )
                
                # Filter by year if provided
                if year:
                    query = query.filter(Songs.first_chart_appearance.like(f'{year}%'))
                
                songs = query.all()
                
                if not songs:
                    return None
                
                # Count how many songs have high-confidence genres
                song_ids = [song.song_id for song in songs]
                classified_count = session.query(SongGenres).filter(
                    SongGenres.song_id.in_(song_ids),
                    SongGenres.confidence_score > 0.8
                ).count()
                
                # Only skip if ALL songs are classified
                if classified_count == len(songs) and classified_count > 0:
                    # Get the genre from any of the classified songs
                    song_genre = session.query(SongGenres).join(Genres).filter(
                        SongGenres.song_id.in_(song_ids),
                        SongGenres.confidence_score > 0.8
                    ).first()
                    
                    if song_genre:
                        # Create a profile from existing data
                        profile = ArtistGenreProfile(
                            artist_name=artist_name,
                            primary_genre=song_genre.genre.genre_name,
                            confidence_score=song_genre.confidence_score
                        )
                        return profile
                
                # If not all songs are classified, return None to trigger re-classification
                return None
        except Exception as e:
            logger.warning(f"Error checking existing classification for {artist_name}: {e}")
            return None
    
    @staticmethod
    def _extract_primary_artist(artist_name: str) -> str:
        """
        Extract the primary artist from an artist string that may contain featured artists.
        
        Examples:
            "clint black feat. steve wariner" -> "clint black"
            "mariah carey feat. jay-z" -> "mariah carey"
            "jay-z & kanye west" -> "jay-z"
            "drake ft. lil wayne" -> "drake"
            "beyonce featuring jay-z" -> "beyonce"
            
        Args:
            artist_name: Full artist string potentially with featured artists
            
        Returns:
            Primary artist name (cleaned)
        """
        import re
        
        # List of featuring indicators (case-insensitive)
        featuring_patterns = [
            r'\s+feat\.?\s+',  # feat. or feat
            r'\s+ft\.?\s+',     # ft. or ft
            r'\s+featuring\s+', # featuring
            r'\s+with\s+',      # with
            r'\s+&\s+',         # &
            r'\s+x\s+',         # x (collaboration marker)
            r'\s+\+\s+',        # +
        ]
        
        # Try each pattern to find where the primary artist ends
        primary_artist = artist_name.lower().strip()
        
        for pattern in featuring_patterns:
            match = re.search(pattern, primary_artist, re.IGNORECASE)
            if match:
                # Extract everything before the featuring indicator
                primary_artist = primary_artist[:match.start()].strip()
                break
        
        return primary_artist
    
    def classify_artist(self, artist_name: str) -> ArtistGenreProfile:
        """
        Classify an artist with hierarchical genre system using ARI-style multi-source approach.
        
        Args:
            artist_name: Name of the artist to classify (may include featured artists)
            
        Returns:
            ArtistGenreProfile with comprehensive classification data
        """
        # Extract primary artist for API lookups (remove featured artists)
        primary_artist = self._extract_primary_artist(artist_name)
        
        # Log if we're using a different artist name for lookup
        if primary_artist != artist_name.lower().strip():
            logger.info(f"Extracting primary artist: '{artist_name}' -> '{primary_artist}'")
        
        # Check if artist already has high-confidence classification
        existing_profile = self._get_existing_classification(artist_name)
        if existing_profile and existing_profile.confidence_score > 0.8:
            logger.info(f"Skipping {artist_name} - already has high-confidence classification ({existing_profile.confidence_score:.2f})")
            return existing_profile
        
        # Check cache first (use primary artist for cache key)
        cache_key = f"artist_{primary_artist}"
        if cache_key in self._classification_cache:
            logger.debug(f"Using cached classification for {primary_artist}")
            return self._classification_cache[cache_key]
        
        logger.info(f"Classifying artist: {primary_artist}")
        
        # Initialize profile
        profile = ArtistGenreProfile(artist_name=artist_name)
        
        # Collect data from all available sources
        source_data = {}
        
        # 1. Spotify (Primary - Fastest, Most Reliable)
        spotify_has_good_data = False
        if self.spotify_available:
            try:
                spotify_data = self.spotify_client.extract_comprehensive_genre_data(primary_artist)
                if spotify_data and spotify_data.get('spotify_genres'):
                    source_data['spotify'] = spotify_data
                    # Add classifications
                    for genre in spotify_data.get('spotify_genres', []):
                        classification = GenreClassification(
                            name=genre,
                            confidence=0.7,  # Good confidence for algorithmic data
                            source='spotify',
                            category='algorithmic'
                        )
                        profile.classifications.append(classification)
                    spotify_has_good_data = True
            except Exception as e:
                logger.warning(f"Spotify error for {primary_artist}: {e}")
        
        # Skip slower sources if Spotify gave us good data
        if not spotify_has_good_data:
            # 2. Chartmetric (Industry Standard) - Only if Spotify failed
            if self.chartmetric_available:
                try:
                    chartmetric_data = self.chartmetric_client.extract_artist_genre_data(primary_artist)
                    if chartmetric_data:
                        source_data['chartmetric'] = chartmetric_data
                        # Add classifications
                        for genre in chartmetric_data.get('genres', []):
                            classification = GenreClassification(
                                name=genre,
                                confidence=0.8,  # High confidence for industry data
                                source='chartmetric',
                                category='industry'
                            )
                            profile.classifications.append(classification)
                except Exception as e:
                    logger.warning(f"Chartmetric error for {primary_artist}: {e}")
        
        # 3. Last.fm (Community Consensus) - Always try for additional data
        if self.lastfm_available:
            try:
                lastfm_data = self.lastfm_client.extract_comprehensive_genre_data(primary_artist)
                if lastfm_data:
                    source_data['lastfm'] = lastfm_data
                    # Add classifications from top genres
                    for genre_info in lastfm_data.get('top_genres', []):
                        classification = GenreClassification(
                            name=genre_info['name'],
                            confidence=genre_info['confidence'],
                            source='lastfm',
                            category='community'
                        )
                        profile.classifications.append(classification)
            except Exception as e:
                logger.warning(f"Last.fm error for {primary_artist}: {e}")
        
        # 4. Genius (Existing Database)
        try:
            genius_genres = self._get_genius_artist_genres(artist_name)
            if genius_genres:
                source_data['genius'] = {'genres': genius_genres}
                for genre in genius_genres:
                    classification = GenreClassification(
                        name=genre,
                        confidence=0.6,  # Medium confidence for database data
                        source='genius',
                        category='database'
                    )
                    profile.classifications.append(classification)
        except Exception as e:
            logger.warning(f"Genius error for {artist_name}: {e}")
        
        # Store source data
        profile.source_data = source_data
        
        # Apply reasoning engine
        self._apply_ari_reasoning_engine(profile)
        
        # Generate A&R insights
        profile.a_and_r_insights = self._generate_ar_insights(profile, source_data)
        
        # Cache the result
        self._classification_cache[cache_key] = profile
        
        return profile
    
    def _apply_ari_reasoning_engine(self, profile: ArtistGenreProfile):
        """Apply ARI-style reasoning engine to determine primary genre and secondary tags."""
        
        if not profile.classifications:
            profile.primary_genre = 'other'
            profile.confidence_score = 0.0
            return
        
        # Group classifications by primary genre
        primary_genre_votes = {}
        secondary_tags = set()
        
        for classification in profile.classifications:
            # Map to primary genre
            primary_genre = self._map_to_primary_genre(classification.name)
            
            # Weight by source and confidence
            weight = self.source_weights.get(classification.source, 0.1) * classification.confidence
            
            if primary_genre not in primary_genre_votes:
                primary_genre_votes[primary_genre] = 0
            primary_genre_votes[primary_genre] += weight
            
            # Collect secondary tags (non-primary genre classifications)
            if classification.name.lower() != primary_genre:
                secondary_tags.add(classification.name.lower())
        
        # Determine primary genre
        if primary_genre_votes:
            profile.primary_genre = max(primary_genre_votes, key=primary_genre_votes.get)
            
            # Calculate confidence score
            total_weight = sum(primary_genre_votes.values())
            primary_weight = primary_genre_votes[profile.primary_genre]
            profile.confidence_score = primary_weight / total_weight if total_weight > 0 else 0.0
        else:
            profile.primary_genre = 'other'
            profile.confidence_score = 0.0
        
        # Set secondary tags
        profile.secondary_tags = list(secondary_tags)[:10]  # Limit to top 10
        
        # Detect crossover indicators
        profile.crossover_indicators = self._detect_crossover_indicators(profile)
    
    def _map_to_primary_genre(self, genre: str) -> str:
        """Map a detailed genre to its primary genre category."""
        genre_lower = genre.lower().strip()
        
        # Direct mapping
        if genre_lower in self.primary_genre_mapping:
            return self.primary_genre_mapping[genre_lower]
        
        # Fuzzy matching for common variations
        for detailed_genre, primary_genre in self.primary_genre_mapping.items():
            if genre_lower in detailed_genre or detailed_genre in genre_lower:
                return primary_genre
        
        # Default to 'other' if no mapping found
        return 'other'
    
    def _detect_crossover_indicators(self, profile: ArtistGenreProfile) -> List[str]:
        """Detect crossover potential indicators."""
        indicators = []
        
        # Check for multiple strong genre classifications
        genre_strengths = {}
        for classification in profile.classifications:
            primary = self._map_to_primary_genre(classification.name)
            weight = self.source_weights.get(classification.source, 0.1) * classification.confidence
            
            if primary not in genre_strengths:
                genre_strengths[primary] = 0
            genre_strengths[primary] += weight
        
        # Sort by strength
        sorted_genres = sorted(genre_strengths.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_genres) >= 2:
            # Check if second strongest is significant
            primary_strength = sorted_genres[0][1]
            secondary_strength = sorted_genres[1][1]
            
            if secondary_strength > primary_strength * 0.6:  # Secondary is at least 60% of primary
                indicators.append('multi_genre_crossover')
                indicators.append(f"primary_{sorted_genres[0][0]}_secondary_{sorted_genres[1][0]}")
        
        # Check for high secondary tag count
        if len(profile.secondary_tags) > 5:
            indicators.append('high_genre_diversity')
        
        return indicators
    
    def _generate_ar_insights(self, profile: ArtistGenreProfile, source_data: Dict) -> Dict[str, Any]:
        """Generate A&R insights from the classification data."""
        insights = {
            'market_positioning': {},
            'crossover_potential': {},
            'source_consensus': {},
            'recommendations': []
        }
        
        # Market positioning
        if profile.primary_genre:
            insights['market_positioning']['primary_genre'] = profile.primary_genre
            insights['market_positioning']['confidence'] = profile.confidence_score
        
        # Crossover potential
        if profile.crossover_indicators:
            insights['crossover_potential']['indicators'] = profile.crossover_indicators
            insights['crossover_potential']['score'] = len(profile.crossover_indicators) / 3.0
        
        # Source consensus
        source_agreement = {}
        for classification in profile.classifications:
            primary = self._map_to_primary_genre(classification.name)
            if primary not in source_agreement:
                source_agreement[primary] = []
            source_agreement[primary].append(classification.source)
        
        # Find genres with multiple source agreement
        consensus_genres = {genre: sources for genre, sources in source_agreement.items() 
                          if len(sources) > 1}
        insights['source_consensus'] = consensus_genres
        
        # Generate recommendations
        if profile.confidence_score > 0.8:
            insights['recommendations'].append('high_confidence_classification')
        elif profile.confidence_score < 0.5:
            insights['recommendations'].append('low_confidence_requires_review')
        
        if profile.crossover_indicators:
            insights['recommendations'].append('consider_crossover_marketing')
        
        return insights
    
    def save_artist_classification(self, artist_name: str, profile: ArtistGenreProfile, year: str = None):
        """Save artist classification to database for all their songs in a given year."""
        try:
            with self.db_manager.get_session() as session:
                # Find all songs by this artist
                query = session.query(Songs).filter(
                    Songs.artist_name.ilike(f"%{artist_name}%")
                )
                
                # Filter by year if provided
                if year:
                    query = query.filter(Songs.first_chart_appearance.like(f'{year}%'))
                
                songs = query.all()
                
                if not songs:
                    year_msg = f"in {year}" if year else "in database"
                    logger.warning(f"No songs found for artist {artist_name} {year_msg}")
                    return
                
                # Save primary genre
                if profile.primary_genre:
                    # Check if genre exists
                    genre = session.query(Genres).filter(
                        Genres.genre_name == profile.primary_genre
                    ).first()
                    
                    if not genre:
                        genre = Genres(genre_name=profile.primary_genre)
                        session.add(genre)
                        session.flush()
                    
                    # Save song-genre relationships for all songs by this artist
                    for song in songs:
                        # Check if relationship already exists
                        existing = session.query(SongGenres).filter(
                            SongGenres.song_id == song.song_id,
                            SongGenres.genre_id == genre.genre_id
                        ).first()
                        
                        if not existing:
                            song_genre = SongGenres(
                                song_id=song.song_id,
                                genre_id=genre.genre_id,
                                confidence_score=profile.confidence_score,
                                source='multi_source_classification'
                            )
                            session.add(song_genre)
                
                session.commit()
                logger.info(f"Saved classification for artist {artist_name} ({len(songs)} songs)")
                
        except Exception as e:
            logger.error(f"Error saving artist classification: {e}")
    
    def save_artist_subgenres(self, artist_name: str, profile: ArtistGenreProfile, year: str = None):
        """
        Save detailed subgenres from API responses for artist's songs.
        Stores the original detailed genres (nu metal, neo soul, etc.) as subgenres.
        """
        try:
            # Import subgenre models
            from database.phase2_models import Subgenres, SongSubgenres
            
            with self.db_manager.get_session() as session:
                # Find all songs by this artist
                query = session.query(Songs).filter(
                    Songs.artist_name.ilike(f"%{artist_name}%")
                )
                
                # Filter by year if provided
                if year:
                    query = query.filter(Songs.first_chart_appearance.like(f'{year}%'))
                
                songs = query.all()
                
                if not songs:
                    return
                
                # Get primary genre ID
                primary_genre_id = None
                if profile.primary_genre:
                    genre = session.query(Genres).filter(
                        Genres.genre_name == profile.primary_genre
                    ).first()
                    if genre:
                        primary_genre_id = genre.genre_id
                
                # Get ALL primary genre names from database to filter them out
                primary_genre_names = set()
                all_genres = session.query(Genres.genre_name).all()
                for (genre_name,) in all_genres:
                    primary_genre_names.add(genre_name.lower())
                
                # Also add common genre-level terms that shouldn't be subgenres
                genre_level_terms = {
                    'soul', 'blues', 'funk', 'disco', 'gospel', 'reggae',
                    'punk', 'metal', 'indie', 'dance', 'edm', 'house',
                    'techno', 'trance', 'dubstep', 'r&b', 'rnb',
                    'rap', 'hip hop', 'hip-hop', 'country', 'folk',
                    'rock', 'pop', 'jazz', 'classical', 'latin',
                    'electronic', 'alternative', 'other'
                }
                primary_genre_names.update(genre_level_terms)
                
                # Extract detailed genres from classifications
                # We want to keep the ORIGINAL detailed genre names before mapping
                detailed_genres = []
                
                for classification in profile.classifications:
                    # Skip if this is the same as primary genre
                    if classification.name.lower() == profile.primary_genre:
                        continue
                    
                    # Skip if this is itself a primary/genre-level term
                    if classification.name.lower() in primary_genre_names:
                        continue
                    
                    # Also skip if it maps to primary genre (but keep if it's more specific)
                    mapped = self._map_to_primary_genre(classification.name)
                    
                    # Keep detailed genres that provide more info than primary
                    # E.g., "nu metal" is more specific than "rock", "soul" is too generic
                    detailed_genres.append({
                        'name': classification.name.lower(),
                        'confidence': classification.confidence,
                        'source': classification.source,
                        'mapped_primary': mapped
                    })
                
                # Deduplicate and rank by confidence
                seen_names = {}
                for detail in detailed_genres:
                    name = detail['name']
                    if name not in seen_names or detail['confidence'] > seen_names[name]['confidence']:
                        seen_names[name] = detail
                
                # Sort by confidence and take top 3
                top_subgenres = sorted(seen_names.values(), key=lambda x: x['confidence'], reverse=True)[:3]
                
                if not top_subgenres:
                    logger.debug(f"No subgenres to save for {artist_name}")
                    return
                
                # Save subgenres for each song
                subgenres_saved = 0
                for song in songs:
                    for rank, subgenre_data in enumerate(top_subgenres, 1):
                        # Get or create subgenre
                        subgenre = session.query(Subgenres).filter(
                            Subgenres.subgenre_name == subgenre_data['name'],
                            Subgenres.parent_genre_id == primary_genre_id
                        ).first()
                        
                        if not subgenre:
                            subgenre = Subgenres(
                                subgenre_name=subgenre_data['name'],
                                parent_genre_id=primary_genre_id
                            )
                            session.add(subgenre)
                            session.flush()
                        
                        # Check if song-subgenre relationship already exists
                        existing = session.query(SongSubgenres).filter(
                            SongSubgenres.song_id == song.song_id,
                            SongSubgenres.subgenre_id == subgenre.subgenre_id
                        ).first()
                        
                        if not existing:
                            song_subgenre = SongSubgenres(
                                song_id=song.song_id,
                                subgenre_id=subgenre.subgenre_id,
                                confidence_score=subgenre_data['confidence'],
                                source=subgenre_data['source'],
                                rank=rank
                            )
                            session.add(song_subgenre)
                            subgenres_saved += 1
                
                session.commit()
                
                if subgenres_saved > 0:
                    logger.info(f"Saved {len(top_subgenres)} subgenres for {artist_name} ({subgenres_saved} song-subgenre links)")
                
        except Exception as e:
            logger.error(f"Error saving subgenres for {artist_name}: {e}")
    
    def enrich_with_producer_subgenres(self, year: str = None):
        """
        Enrich songs with producer-based subgenres using Phase 2 credits data.
        This adds subgenres based on producer genre specialization patterns.
        """
        try:
            from database.phase2_models import Subgenres, SongSubgenres, Credits, SongCredits, CreditRoles
            from api.producer_genre_patterns import analyze_producer_contribution
            from sqlalchemy import text
            
            with self.db_manager.get_session() as session:
                # Get songs with producers but potentially missing subgenres
                query_str = """
                    SELECT DISTINCT s.song_id, s.song_name, s.artist_name, 
                           strftime('%Y', s.first_chart_appearance) as year,
                           g.genre_id, g.genre_name
                    FROM songs s
                    JOIN song_credits sc ON s.song_id = sc.song_id
                    JOIN credit_roles cr ON sc.role_id = cr.role_id
                    JOIN song_genres sg ON s.song_id = sg.song_id
                    JOIN genres g ON sg.genre_id = g.genre_id
                    WHERE cr.role_name = 'Producer'
                """
                
                if year:
                    query_str += f" AND strftime('%Y', s.first_chart_appearance) = '{year}'"
                
                query_str += " ORDER BY s.peak_position LIMIT 50"
                
                result = session.execute(text(query_str))
                songs_with_producers = result.fetchall()
                
                logger.info(f"Found {len(songs_with_producers)} songs with producers to enrich")
                
                enriched_count = 0
                
                for song_id, song_name, artist_name, song_year, genre_id, genre_name in songs_with_producers:
                    # Get producers for this song
                    producers_query_str = """
                        SELECT c.credit_name
                        FROM credits c
                        JOIN song_credits sc ON c.credit_id = sc.credit_id
                        JOIN credit_roles cr ON sc.role_id = cr.role_id
                        WHERE sc.song_id = :song_id AND cr.role_name = 'Producer'
                    """
                    
                    producer_result = session.execute(text(producers_query_str), {'song_id': song_id})
                    producers = [row[0] for row in producer_result.fetchall()]
                    
                    if producers:
                        # Analyze producer contribution
                        producer_signals = analyze_producer_contribution(producers, int(song_year))
                        
                        if producer_signals and producer_signals['suggested_subgenres']:
                            # Add these as subgenres
                            for rank, subgenre_name in enumerate(producer_signals['suggested_subgenres'], 1):
                                # Get or create subgenre
                                subgenre = session.query(Subgenres).filter(
                                    Subgenres.subgenre_name == subgenre_name,
                                    Subgenres.parent_genre_id == genre_id
                                ).first()
                                
                                if not subgenre:
                                    subgenre = Subgenres(
                                        subgenre_name=subgenre_name,
                                        parent_genre_id=genre_id,
                                        description=f'Producer-based: {", ".join(producers)}'
                                    )
                                    session.add(subgenre)
                                    session.flush()
                                
                                # Check if already exists
                                existing = session.query(SongSubgenres).filter(
                                    SongSubgenres.song_id == song_id,
                                    SongSubgenres.subgenre_id == subgenre.subgenre_id
                                ).first()
                                
                                if not existing:
                                    # Determine rank
                                    max_rank_result = session.execute(
                                        text("SELECT COALESCE(MAX(rank), 0) FROM song_subgenres WHERE song_id = :song_id"),
                                        {'song_id': song_id}
                                    ).fetchone()
                                    new_rank = max_rank_result[0] + 1 if max_rank_result else 1
                                    
                                    song_subgenre = SongSubgenres(
                                        song_id=song_id,
                                        subgenre_id=subgenre.subgenre_id,
                                        confidence_score=producer_signals['confidence'],
                                        source='producer_specialization',
                                        rank=new_rank
                                    )
                                    session.add(song_subgenre)
                                    enriched_count += 1
                
                session.commit()
                logger.info(f"Enriched {enriched_count} song-subgenre links using producer data")
                
        except Exception as e:
            logger.error(f"Error enriching with producer subgenres: {e}")
    
    def _get_spotify_artist_genres(self, artist_name: str) -> List[str]:
        """Get genres from Spotify for an artist."""
        try:
            if not self.spotify_available:
                return []
            
            # Check cache first
            cached = self._get_cached_response('spotify', artist_name)
            if cached is not None:
                logger.debug(f"Using cached Spotify data for {artist_name}")
                return cached
            
            # Use the comprehensive genre data method
            data = self.spotify_client.extract_comprehensive_genre_data(artist_name)
            if data and 'spotify_genres' in data:
                genres = data['spotify_genres']
                # Cache the result
                self._cache_response('spotify', artist_name, genres)
                return genres
            
            return []
        except Exception as e:
            logger.warning(f"Error getting Spotify genres for {artist_name}: {e}")
            return []
    
    def _get_lastfm_artist_genres(self, artist_name: str) -> List[str]:
        """Get genres from Last.fm for an artist."""
        try:
            if not self.lastfm_available:
                return []
            
            # Check cache first
            cached = self._get_cached_response('lastfm', artist_name)
            if cached is not None:
                logger.debug(f"Using cached Last.fm data for {artist_name}")
                return cached
            
            # Use the comprehensive genre data method
            data = self.lastfm_client.extract_comprehensive_genre_data(artist_name)
            if data and 'top_genres' in data:
                genres = [genre['name'] for genre in data['top_genres']]
                # Cache the result
                self._cache_response('lastfm', artist_name, genres)
                return genres
            
            return []
        except Exception as e:
            logger.warning(f"Error getting Last.fm genres for {artist_name}: {e}")
            return []
    
    def _get_chartmetric_artist_genres(self, artist_name: str) -> List[str]:
        """Get genres from Chartmetric for an artist."""
        try:
            if not self.chartmetric_available:
                return []
            
            # Use the comprehensive genre data method
            data = self.chartmetric_client.extract_artist_genre_data(artist_name)
            if data and 'genres' in data:
                return data['genres']
            
            return []
        except Exception as e:
            logger.warning(f"Error getting Chartmetric genres for {artist_name}: {e}")
            return []
    
    def _get_genius_artist_genres(self, artist_name: str) -> List[str]:
        """Get genres from existing Genius data in database."""
        try:
            with self.db_manager.get_session() as session:
                # Get genres from songs by this artist
                query = session.query(Genres.genre_name).join(
                    SongGenres, Genres.genre_id == SongGenres.genre_id
                ).join(
                    Songs, SongGenres.song_id == Songs.song_id
                ).filter(
                    Songs.artist_name.ilike(f"%{artist_name}%")
                ).distinct()
                
                genres = [row[0] for row in query.all()]
                return genres
        except Exception as e:
            logger.warning(f"Error getting Genius genres for {artist_name}: {e}")
            return []
    
    def _apply_reasoning_engine(self, source_genres: Dict[str, List[str]], artist_name: str) -> GenreResult:
        """
        Apply reasoning engine to determine primary genre and secondary tags.
        
        Args:
            source_genres: Dictionary mapping source names to genre lists
            artist_name: Name of the artist being classified
            
        Returns:
            GenreResult with primary genre, secondary tags, and confidence
        """
        # Flatten all genres from all sources
        all_genres = []
        source_weights = []
        
        for source, genres in source_genres.items():
            weight = self.SOURCE_WEIGHTS.get(source, 0.1)
            for genre in genres:
                all_genres.append(genre.lower())
                source_weights.append(weight)
        
        if not all_genres:
            return GenreResult(
                primary_genre='other',
                secondary_tags=[],
                confidence_score=0.0,
                sources=[],
                reasoning="No genre data available from any source"
            )
        
        # Count genre occurrences with weights
        genre_scores = {}
        for genre, weight in zip(all_genres, source_weights):
            genre_scores[genre] = genre_scores.get(genre, 0) + weight
        
        # Map to primary genres
        primary_genre_scores = {}
        secondary_tags = []
        
        for genre, score in genre_scores.items():
            mapped_primary = self._map_to_primary_genre(genre)
            if mapped_primary:
                primary_genre_scores[mapped_primary] = primary_genre_scores.get(mapped_primary, 0) + score
            else:
                # Keep as secondary tag if not mappable to primary
                if genre not in secondary_tags:
                    secondary_tags.append(genre)
        
        # Determine primary genre
        if primary_genre_scores:
            primary_genre = max(primary_genre_scores, key=primary_genre_scores.get)
            confidence_score = min(primary_genre_scores[primary_genre] / len(source_genres), 1.0)
        else:
            primary_genre = 'other'
            confidence_score = 0.1
        
        # Build reasoning
        reasoning_parts = []
        for source, genres in source_genres.items():
            if genres:
                reasoning_parts.append(f"{source}: {', '.join(genres[:3])}")
        
        reasoning = f"Primary: {primary_genre} (confidence: {confidence_score:.2f}). Sources: {'; '.join(reasoning_parts)}"
        
        return GenreResult(
            primary_genre=primary_genre,
            secondary_tags=secondary_tags[:5],  # Limit to top 5 secondary tags
            confidence_score=confidence_score,
            sources=list(source_genres.keys()),
            reasoning=reasoning
        )
    
    
    def classify_song(self, song_name: str, artist_name: str) -> GenreResult:
        """
        Classify a song using artist inheritance and audio features.
        
        Args:
            song_name: Name of the song
            artist_name: Name of the artist
            
        Returns:
            GenreResult for the song
        """
        # First, try to get artist classification
        artist_result = self.classify_artist(artist_name)
        
        # Try to get song-specific genres from Spotify
        song_specific_genres = []
        if self.spotify_client:
            song_specific_genres = self._get_spotify_song_genres(song_name, artist_name)
        
        # If we have song-specific genres, use them; otherwise inherit from artist
        if song_specific_genres:
            # Apply reasoning engine to song-specific genres
            source_genres = {'spotify': song_specific_genres}
            result = self._apply_reasoning_engine(source_genres, f"{artist_name} - {song_name}")
            result.reasoning += f" (song-specific, inherited from artist: {artist_result.primary_genre})"
        else:
            # Inherit from artist with lower confidence
            result = GenreResult(
                primary_genre=artist_result.primary_genre,
                secondary_tags=artist_result.secondary_tags,
                confidence_score=artist_result.confidence_score * 0.8,  # Reduce confidence for inheritance
                sources=artist_result.sources,
                reasoning=f"Inherited from artist classification: {artist_result.reasoning}"
            )
        
        return result
    
    def _get_spotify_song_genres(self, song_name: str, artist_name: str) -> List[str]:
        """Get genres from Spotify for a specific song."""
        try:
            if not self.spotify_client:
                return []
            
            # Search for the song
            query = f"track:{song_name} artist:{artist_name}"
            results = self.spotify_client.search(query, type='track', limit=1)
            
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                # Get artist genres for this track
                artist_id = track['artists'][0]['id']
                artist_info = self.spotify_client.artist(artist_id)
                return artist_info.get('genres', [])
            
            return []
        except Exception as e:
            logger.warning(f"Error getting Spotify song genres for {song_name} by {artist_name}: {e}")
            return []
    
    def classify_creator(self, creator_name: str, creator_type: str) -> GenreResult:
        """
        Classify a producer or songwriter based on songs they've worked on.
        
        Args:
            creator_name: Name of the producer/songwriter
            creator_type: 'producer' or 'songwriter'
            
        Returns:
            GenreResult based on majority classification of their work
        """
        try:
            with self.db_manager.get_session() as session:
                # Get songs this creator has worked on
                from database.phase2_models import Credits, SongCredits, CreditRoles
                
                query = session.query(Songs.song_name, Songs.artist_name).join(
                    SongCredits, Songs.song_id == SongCredits.song_id
                ).join(
                    Credits, SongCredits.credit_id == Credits.credit_id
                ).join(
                    CreditRoles, SongCredits.role_id == CreditRoles.role_id
                ).filter(
                    Credits.credit_name.ilike(f"%{creator_name}%"),
                    CreditRoles.role_name.ilike(f"%{creator_type}%")
                ).limit(50)  # Limit to avoid too much processing
                
                songs = query.all()
                
                if not songs:
                    return GenreResult(
                        primary_genre='other',
                        secondary_tags=[],
                        confidence_score=0.0,
                        sources=[],
                        reasoning=f"No songs found for {creator_type} {creator_name}"
                    )
                
                # Classify each song and aggregate results
                genre_counts = {}
                total_songs = len(songs)
                
                for song_name, artist_name in songs:
                    song_result = self.classify_song(song_name, artist_name)
                    genre_counts[song_result.primary_genre] = genre_counts.get(song_result.primary_genre, 0) + 1
                
                # Determine majority genre
                if genre_counts:
                    primary_genre = max(genre_counts, key=genre_counts.get)
                    confidence_score = genre_counts[primary_genre] / total_songs
                else:
                    primary_genre = 'other'
                    confidence_score = 0.0
                
                reasoning = f"Based on {total_songs} songs: {primary_genre} ({genre_counts.get(primary_genre, 0)}/{total_songs})"
                
                return GenreResult(
                    primary_genre=primary_genre,
                    secondary_tags=[],
                    confidence_score=confidence_score,
                    sources=['database_analysis'],
                    reasoning=reasoning
                )
                
        except Exception as e:
            logger.error(f"Error classifying {creator_type} {creator_name}: {e}")
            return GenreResult(
                primary_genre='other',
                secondary_tags=[],
                confidence_score=0.0,
                sources=[],
                reasoning=f"Error during classification: {str(e)}"
            )


def main():
    """Main function for testing the genre classification system."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Genre Classification System')
    parser.add_argument('--artist', type=str, help='Classify an artist')
    parser.add_argument('--song', type=str, help='Classify a song')
    parser.add_argument('--artist-song', type=str, help='Artist name for song classification')
    parser.add_argument('--creator', type=str, help='Classify a producer/songwriter')
    parser.add_argument('--creator-type', type=str, choices=['producer', 'songwriter'], 
                       help='Type of creator to classify')
    parser.add_argument('--test', action='store_true', help='Run test classifications')
    
    args = parser.parse_args()
    
    # Initialize the system
    system = GenreClassificationSystem()
    
    if args.test:
        # Test with some well-known artists
        test_artists = ['Taylor Swift', 'Drake', 'The Beatles', 'Billie Eilish']
        
        for artist in test_artists:
            print(f"\n{'='*50}")
            print(f"Testing classification for: {artist}")
            print(f"{'='*50}")
            
            result = system.classify_artist(artist)
            print(f"Primary Genre: {result.primary_genre}")
            print(f"Secondary Tags: {', '.join(result.secondary_tags) if result.secondary_tags else 'None'}")
            print(f"Confidence: {result.confidence_score:.2f}")
            print(f"Crossover Indicators: {', '.join(result.crossover_indicators) if result.crossover_indicators else 'None'}")
            print(f"Sources: {', '.join(result.source_data.keys()) if result.source_data else 'None'}")
            print(f"A&R Insights: {len(result.a_and_r_insights)} insights generated")
            
            time.sleep(0.5)  # Rate limiting
    
    elif args.artist:
        result = system.classify_artist(args.artist)
        print(f"Artist: {args.artist}")
        print(f"Primary Genre: {result.primary_genre}")
        print(f"Secondary Tags: {', '.join(result.secondary_tags) if result.secondary_tags else 'None'}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Crossover Indicators: {', '.join(result.crossover_indicators) if result.crossover_indicators else 'None'}")
        print(f"Sources: {', '.join(result.source_data.keys()) if result.source_data else 'None'}")
        print(f"A&R Insights: {len(result.a_and_r_insights)} insights generated")
    
    elif args.song and args.artist_song:
        result = system.classify_song(args.song, args.artist_song)
        print(f"Song: {args.song} by {args.artist_song}")
        print(f"Primary Genre: {result.primary_genre}")
        print(f"Secondary Tags: {', '.join(result.secondary_tags)}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Sources: {', '.join(result.sources)}")
        print(f"Reasoning: {result.reasoning}")
    
    elif args.creator and args.creator_type:
        result = system.classify_creator(args.creator, args.creator_type)
        print(f"{args.creator_type.title()}: {args.creator}")
        print(f"Primary Genre: {result.primary_genre}")
        print(f"Secondary Tags: {', '.join(result.secondary_tags)}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Sources: {', '.join(result.sources)}")
        print(f"Reasoning: {result.reasoning}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
