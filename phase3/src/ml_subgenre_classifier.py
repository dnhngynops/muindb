#!/usr/bin/env python3
"""
ML-Based Subgenre Classifier
Loads trained models and classifies songs into subgenres
"""

import os
import sys
from pathlib import Path
import pickle
import numpy as np
from typing import Dict, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)

# Add training directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'training'))

try:
    from subgenre_definitions import RULE_BASED_SUBGENRES
except ImportError:
    logger.warning("Could not import subgenre_definitions")
    RULE_BASED_SUBGENRES = {}


class MLSubgenreClassifier:
    """
    Classify songs into subgenres using trained ML models
    Falls back to rule-based classification when ML model unavailable
    """
    
    def __init__(self):
        self.models = {}
        self.models_dir = project_root / 'models'
        self._load_all_models()
    
    def _load_all_models(self):
        """Load all available trained models"""
        if not self.models_dir.exists():
            logger.warning(f"Models directory not found: {self.models_dir}")
            return
        
        model_files = list(self.models_dir.glob('*_subgenre_model.pkl'))
        
        for model_file in model_files:
            primary_genre = model_file.stem.replace('_subgenre_model', '')
            try:
                with open(model_file, 'rb') as f:
                    self.models[primary_genre] = pickle.load(f)
                logger.info(f"Loaded model for {primary_genre}")
            except Exception as e:
                logger.error(f"Failed to load model for {primary_genre}: {e}")
        
        if self.models:
            logger.info(f"Loaded {len(self.models)} ML models: {', '.join(self.models.keys())}")
        else:
            logger.warning("No ML models loaded - will use rule-based classification only")
    
    def classify_with_ml(self, primary_genre: str, audio_features: Dict) -> Tuple[Optional[str], float]:
        """
        Classify song into subgenre using ML model
        
        Args:
            primary_genre: Primary genre (e.g., 'hip-hop')
            audio_features: Spotify audio features dictionary
            
        Returns:
            (subgenre, confidence) or (None, 0.0) if classification fails
        """
        if primary_genre not in self.models:
            logger.debug(f"No ML model available for {primary_genre}")
            return (None, 0.0)
        
        try:
            model_package = self.models[primary_genre]
            
            # Extract required features
            feature_cols = model_package['feature_cols']
            features = []
            for col in feature_cols:
                value = audio_features.get(col, 0)
                
                # Handle tempo adjustment
                if col == 'tempo':
                    if value > 200:
                        value = value / 2
                    elif value < 100:
                        value = value * 2
                
                features.append(value)
            
            # Transform features (polynomial + scaling)
            features_array = np.array([features])
            features_poly = model_package['poly_transformer'].transform(features_array)
            features_scaled = model_package['scaler'].transform(features_poly)
            
            # Predict
            model = model_package['model']
            prediction = model.predict(features_scaled)[0]
            probabilities = model.predict_proba(features_scaled)[0]
            confidence = max(probabilities)
            
            logger.debug(f"ML prediction for {primary_genre}: {prediction} (confidence: {confidence:.2f})")
            
            return (prediction, confidence)
            
        except Exception as e:
            logger.error(f"Error in ML classification for {primary_genre}: {e}")
            return (None, 0.0)
    
    def classify_with_rules(self, primary_genre: str, audio_features: Dict) -> Tuple[Optional[str], float]:
        """
        Classify song into subgenre using rule-based matching
        
        Args:
            primary_genre: Primary genre
            audio_features: Spotify audio features dictionary
            
        Returns:
            (subgenre, confidence) or (None, 0.0) if no match
        """
        if primary_genre not in RULE_BASED_SUBGENRES:
            return (None, 0.0)
        
        subgenre_profiles = RULE_BASED_SUBGENRES[primary_genre]
        best_match = None
        best_score = 0.0
        
        for subgenre, profile in subgenre_profiles.items():
            score = self._calculate_profile_match(audio_features, profile)
            if score > best_score:
                best_score = score
                best_match = subgenre
        
        # Only return if confidence is high enough
        if best_score >= 0.6:
            logger.debug(f"Rule-based match for {primary_genre}: {best_match} (score: {best_score:.2f})")
            return (best_match, best_score)
        
        return (None, best_score)
    
    def _calculate_profile_match(self, audio_features: Dict, profile: Dict) -> float:
        """
        Calculate how well audio features match a profile
        
        Args:
            audio_features: Spotify audio features
            profile: Dictionary of feature ranges
            
        Returns:
            Match score 0.0 to 1.0
        """
        matches = 0
        total = 0
        
        for feature, range_tuple in profile.items():
            if feature in audio_features:
                total += 1
                value = audio_features[feature]
                min_val, max_val = range_tuple
                
                if min_val <= value <= max_val:
                    matches += 1
                else:
                    # Partial credit for being close
                    if min_val <= value <= max_val * 1.2 or min_val * 0.8 <= value <= max_val:
                        matches += 0.5
        
        return matches / total if total > 0 else 0.0
    
    def classify(self, primary_genre: str, audio_features: Dict, 
                method: str = 'auto') -> Dict:
        """
        Classify song into subgenre using best available method
        
        Args:
            primary_genre: Primary genre from Phase 3
            audio_features: Spotify audio features
            method: 'ml', 'rules', or 'auto' (use ML if available, else rules)
            
        Returns:
            Dictionary with classification results
        """
        result = {
            'subgenre': None,
            'confidence': 0.0,
            'method': None,
            'primary_genre': primary_genre
        }
        
        # Try ML first if available and method allows
        if method in ['ml', 'auto']:
            subgenre, confidence = self.classify_with_ml(primary_genre, audio_features)
            if subgenre:
                result['subgenre'] = subgenre
                result['confidence'] = confidence
                result['method'] = 'ml'
                return result
        
        # Fall back to rules if ML not available or failed
        if method in ['rules', 'auto']:
            subgenre, confidence = self.classify_with_rules(primary_genre, audio_features)
            if subgenre:
                result['subgenre'] = subgenre
                result['confidence'] = confidence
                result['method'] = 'rules'
                return result
        
        # No classification possible
        result['method'] = 'none'
        return result
    
    def get_available_models(self) -> List[str]:
        """Get list of primary genres with available ML models"""
        return list(self.models.keys())
    
    def get_model_info(self, primary_genre: str) -> Optional[Dict]:
        """Get information about a loaded model"""
        if primary_genre not in self.models:
            return None
        
        package = self.models[primary_genre]
        return {
            'primary_genre': package['primary_genre'],
            'subgenres': package['subgenres'],
            'test_accuracy': package['test_accuracy'],
            'features_used': package['feature_cols'],
            'trained_date': package.get('trained_date', 'Unknown')
        }


# Convenience function
def create_subgenre_classifier() -> MLSubgenreClassifier:
    """Create and return a subgenre classifier instance"""
    return MLSubgenreClassifier()
