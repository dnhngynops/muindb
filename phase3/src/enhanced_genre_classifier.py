#!/usr/bin/env python3
"""
Enhanced Genre Classification System
Integrates ML models and rule-based classification with Phase 3's multi-source approach
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional, List
import logging
from dataclasses import dataclass

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from ml_subgenre_classifier import MLSubgenreClassifier
from api.spotify_genre_client import SpotifyGenreClient

logger = logging.getLogger(__name__)


@dataclass
class EnhancedGenreResult:
    """Result of enhanced genre classification"""
    primary_genre: str
    primary_confidence: float
    subgenre: Optional[str]
    subgenre_confidence: float
    classification_method: str  # 'ml', 'rules', or 'none'
    audio_features: Optional[Dict]
    sources: List[str]
    reasoning: str


class EnhancedGenreClassifier:
    """
    Enhanced genre classifier combining:
    1. Phase 3's multi-source primary genre classification
    2. ML models for subgenre classification (top 6 genres)
    3. Rule-based fallback for other genres
    """
    
    def __init__(self, multi_source_system=None):
        """
        Initialize enhanced classifier
        
        Args:
            multi_source_system: Phase 3's GenreClassificationSystem instance (optional)
        """
        # Initialize subgenre classifier (ML + rules)
        self.subgenre_classifier = MLSubgenreClassifier()
        
        # Initialize Spotify client for audio features
        try:
            self.spotify_client = SpotifyGenreClient()
            self.spotify_available = True
        except Exception as e:
            logger.warning(f"Spotify not available: {e}")
            self.spotify_client = None
            self.spotify_available = False
        
        # Store multi-source system reference (Phase 3)
        self.multi_source_system = multi_source_system
        
        logger.info("Enhanced genre classifier initialized")
        logger.info(f"  ML models loaded: {len(self.subgenre_classifier.get_available_models())}")
        logger.info(f"  Spotify available: {self.spotify_available}")
    
    def classify_song(self, song_name: str, artist_name: str, 
                     primary_genre: Optional[str] = None,
                     primary_confidence: Optional[float] = None) -> EnhancedGenreResult:
        """
        Classify song with primary genre and subgenre
        
        Args:
            song_name: Song title
            artist_name: Artist name
            primary_genre: Pre-determined primary genre (if None, use multi-source)
            primary_confidence: Confidence of primary genre
            
        Returns:
            EnhancedGenreResult with complete classification
        """
        sources = []
        reasoning_parts = []
        
        # STAGE 1: Get primary genre (if not provided)
        if primary_genre is None and self.multi_source_system:
            # Use Phase 3's multi-source classification
            multi_result = self.multi_source_system.classify_artist(artist_name)
            primary_genre = multi_result.primary_genre
            primary_confidence = multi_result.confidence_score
            sources = ['spotify', 'lastfm', 'genius']
            reasoning_parts.append(f"Primary genre '{primary_genre}' from multi-source APIs")
        elif primary_genre:
            sources.append('provided')
            reasoning_parts.append(f"Primary genre '{primary_genre}' provided")
        else:
            # No way to get primary genre
            return EnhancedGenreResult(
                primary_genre='unknown',
                primary_confidence=0.0,
                subgenre=None,
                subgenre_confidence=0.0,
                classification_method='none',
                audio_features=None,
                sources=[],
                reasoning="No primary genre available"
            )
        
        # STAGE 2: Get audio features
        audio_features = None
        if self.spotify_available:
            audio_features = self._get_audio_features(song_name, artist_name)
            if audio_features:
                sources.append('spotify_audio')
                reasoning_parts.append("Audio features collected from Spotify")
        
        if not audio_features:
            # No audio features, can't classify subgenre
            return EnhancedGenreResult(
                primary_genre=primary_genre,
                primary_confidence=primary_confidence,
                subgenre=None,
                subgenre_confidence=0.0,
                classification_method='none',
                audio_features=None,
                sources=sources,
                reasoning="; ".join(reasoning_parts) + "; No audio features available"
            )
        
        # STAGE 3: Classify subgenre
        classification = self.subgenre_classifier.classify(
            primary_genre, 
            audio_features,
            method='auto'  # Try ML first, fall back to rules
        )
        
        subgenre = classification['subgenre']
        subgenre_confidence = classification['confidence']
        method = classification['method']
        
        if subgenre:
            if method == 'ml':
                reasoning_parts.append(f"Subgenre '{subgenre}' classified using ML model (accuracy: {subgenre_confidence:.0%})")
            elif method == 'rules':
                reasoning_parts.append(f"Subgenre '{subgenre}' classified using rule-based matching (confidence: {subgenre_confidence:.0%})")
        else:
            reasoning_parts.append("No subgenre classification available")
        
        return EnhancedGenreResult(
            primary_genre=primary_genre,
            primary_confidence=primary_confidence,
            subgenre=subgenre,
            subgenre_confidence=subgenre_confidence,
            classification_method=method,
            audio_features=audio_features,
            sources=sources,
            reasoning="; ".join(reasoning_parts)
        )
    
    def _get_audio_features(self, song_name: str, artist_name: str) -> Optional[Dict]:
        """Get Spotify audio features for a song"""
        try:
            # Search for track
            query = f"track:{song_name} artist:{artist_name}"
            results = self.spotify_client.sp.search(q=query, type='track', limit=1)
            
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                track_id = track['id']
                
                # Get audio features
                features = self.spotify_client.sp.audio_features([track_id])
                if features and features[0]:
                    return features[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting audio features: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Get statistics about loaded models"""
        return {
            'ml_models_loaded': len(self.subgenre_classifier.get_available_models()),
            'ml_genres': self.subgenre_classifier.get_available_models(),
            'spotify_available': self.spotify_available
        }


# Convenience function
def create_enhanced_classifier(multi_source_system=None) -> EnhancedGenreClassifier:
    """Create and return an enhanced genre classifier"""
    return EnhancedGenreClassifier(multi_source_system)
