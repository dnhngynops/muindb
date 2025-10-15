#!/usr/bin/env python3
"""
Train ML Models for Subgenre Classification
Trains separate models for each primary genre using ensemble methods
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pickle
import argparse
from typing import Dict, Tuple
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import accuracy_score, classification_report

# Add src to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root / 'src'))

from subgenre_definitions import TRAINING_CONFIG, GENRE_FEATURE_IMPORTANCE

class SubgenreModelTrainer:
    """Train ML models for subgenre classification"""
    
    def __init__(self):
        self.polynomial_degree = TRAINING_CONFIG['polynomial_degree']
        self.test_size = TRAINING_CONFIG['test_size']
        self.random_state = TRAINING_CONFIG['random_state']
    
    def adjust_tempo(self, tempo):
        """Normalize tempo to 100-200 BPM range (from EDM Classifier)"""
        if tempo > 200:
            return tempo / 2
        elif tempo < 100:
            return tempo * 2
        return tempo
    
    def prepare_features(self, df: pd.DataFrame, primary_genre: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare features for training
        
        Args:
            df: DataFrame with audio features and subgenre labels
            primary_genre: Primary genre being trained
            
        Returns:
            (X_scaled, y) ready for training
        """
        # Select most important features for this genre
        feature_cols = GENRE_FEATURE_IMPORTANCE.get(
            primary_genre, 
            ['tempo', 'energy', 'loudness', 'danceability', 'duration_ms']
        )
        
        # Extract features
        X = df[feature_cols].copy()
        
        # Adjust tempo if it's a feature
        if 'tempo' in feature_cols:
            X['tempo'] = X['tempo'].apply(self.adjust_tempo)
        
        # Handle missing values
        X = X.fillna(X.mean())
        
        # Target variable
        y = df['subgenre'].values
        
        return X, y, feature_cols
    
    def train_genre_model(self, primary_genre: str, data_file: Path) -> Dict:
        """
        Train ML model for a specific genre
        
        Args:
            primary_genre: Primary genre to train model for
            data_file: Path to CSV with training data
            
        Returns:
            Dictionary with model and preprocessing objects
        """
        print(f"\n{'='*80}")
        print(f"TRAINING MODEL FOR: {primary_genre.upper()}")
        print(f"{'='*80}\n")
        
        # Load data
        print(f"Loading data from {data_file}...")
        df = pd.DataFrame(pd.read_csv(data_file))
        
        print(f"✓ Loaded {len(df)} songs")
        print(f"✓ Subgenres: {df['subgenre'].nunique()}")
        print("\nSubgenre distribution:")
        for subgenre, count in df['subgenre'].value_counts().items():
            print(f"  - {subgenre}: {count} songs")
        
        # Prepare features
        print("\nPreparing features...")
        X, y, feature_cols = self.prepare_features(df, primary_genre)
        print(f"✓ Using features: {', '.join(feature_cols)}")
        
        # Create polynomial features
        print(f"\nCreating polynomial features (degree {self.polynomial_degree})...")
        poly = PolynomialFeatures(degree=self.polynomial_degree, include_bias=False)
        X_poly = poly.fit_transform(X)
        print(f"✓ Engineered {X_poly.shape[1]} features from {len(feature_cols)} original features")
        
        # Scale features
        print("\nScaling features...")
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_poly)
        
        # Train/test split
        print("\nSplitting data...")
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, 
            test_size=self.test_size, 
            random_state=self.random_state,
            stratify=y
        )
        print(f"✓ Train set: {len(X_train)} songs")
        print(f"✓ Test set: {len(X_test)} songs")
        
        # Train models
        print("\n" + "-"*80)
        print("TRAINING MODELS")
        print("-"*80)
        
        # Random Forest
        print("\n1. Training Random Forest...")
        rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            random_state=self.random_state,
            n_jobs=-1
        )
        rf_model.fit(X_train, y_train)
        rf_train_acc = accuracy_score(y_train, rf_model.predict(X_train))
        rf_test_acc = accuracy_score(y_test, rf_model.predict(X_test))
        print(f"   Train accuracy: {rf_train_acc:.2%}")
        print(f"   Test accuracy: {rf_test_acc:.2%}")
        
        # Gradient Boosting
        print("\n2. Training Gradient Boosting...")
        gb_model = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.1,
            random_state=self.random_state
        )
        gb_model.fit(X_train, y_train)
        gb_train_acc = accuracy_score(y_train, gb_model.predict(X_train))
        gb_test_acc = accuracy_score(y_test, gb_model.predict(X_test))
        print(f"   Train accuracy: {gb_train_acc:.2%}")
        print(f"   Test accuracy: {gb_test_acc:.2%}")
        
        # XGBoost
        print("\n3. Training XGBoost...")
        xgb_model = XGBClassifier(
            n_estimators=200,
            learning_rate=0.1,
            random_state=self.random_state,
            eval_metric='mlogloss'
        )
        xgb_model.fit(X_train, y_train)
        xgb_train_acc = accuracy_score(y_train, xgb_model.predict(X_train))
        xgb_test_acc = accuracy_score(y_test, xgb_model.predict(X_test))
        print(f"   Train accuracy: {xgb_train_acc:.2%}")
        print(f"   Test accuracy: {xgb_test_acc:.2%}")
        
        # Ensemble (Voting Classifier)
        print("\n4. Creating Ensemble...")
        ensemble = VotingClassifier(
            estimators=[
                ('rf', rf_model),
                ('gb', gb_model),
                ('xgb', xgb_model)
            ],
            voting='soft'  # Use probabilities
        )
        ensemble.fit(X_train, y_train)
        ensemble_train_acc = accuracy_score(y_train, ensemble.predict(X_train))
        ensemble_test_acc = accuracy_score(y_test, ensemble.predict(X_test))
        print(f"   Train accuracy: {ensemble_train_acc:.2%}")
        print(f"   Test accuracy: {ensemble_test_acc:.2%}")
        
        # Best model summary
        print("\n" + "-"*80)
        print("MODEL COMPARISON")
        print("-"*80)
        models_comparison = [
            ('Random Forest', rf_test_acc),
            ('Gradient Boosting', gb_test_acc),
            ('XGBoost', xgb_test_acc),
            ('Ensemble', ensemble_test_acc)
        ]
        for name, acc in models_comparison:
            print(f"  {name:<20}: {acc:.2%}")
        
        best_model_name = max(models_comparison, key=lambda x: x[1])[0]
        print(f"\n✓ Best model: {best_model_name}")
        
        # Classification report for ensemble
        print("\n" + "-"*80)
        print("DETAILED METRICS (Ensemble on Test Set)")
        print("-"*80)
        y_pred = ensemble.predict(X_test)
        print(classification_report(y_test, y_pred, zero_division=0))
        
        # Package everything
        model_package = {
            'model': ensemble,
            'poly_transformer': poly,
            'scaler': scaler,
            'feature_cols': feature_cols,
            'subgenres': list(df['subgenre'].unique()),
            'primary_genre': primary_genre,
            'test_accuracy': ensemble_test_acc,
            'trained_date': pd.Timestamp.now().isoformat()
        }
        
        return model_package
    
    def save_model(self, model_package: Dict, primary_genre: str):
        """Save trained model package"""
        models_dir = project_root / 'models'
        models_dir.mkdir(exist_ok=True)
        
        model_file = models_dir / f'{primary_genre}_subgenre_model.pkl'
        
        with open(model_file, 'wb') as f:
            pickle.dump(model_package, f)
        
        print(f"\n{'='*80}")
        print(f"✅ MODEL SAVED: {model_file}")
        print(f"{'='*80}")
        print(f"  Subgenres: {len(model_package['subgenres'])}")
        print(f"  Test accuracy: {model_package['test_accuracy']:.2%}")
        print(f"  Features used: {len(model_package['feature_cols'])}")

def main():
    parser = argparse.ArgumentParser(description='Train ML models for subgenre classification')
    parser.add_argument('--genre', type=str, required=True,
                       choices=['country', 'pop', 'hip-hop', 'r&b', 'alternative', 'rock', 'electronic', 'all'],
                       help='Primary genre to train model for (or "all" for all genres)')
    
    args = parser.parse_args()
    
    trainer = SubgenreModelTrainer()
    
    # Determine which genres to train
    if args.genre == 'all':
        genres_to_train = ['country', 'pop', 'hip-hop', 'r&b', 'alternative', 'rock']
    else:
        genres_to_train = [args.genre]
    
    print("=" * 80)
    print("SUBGENRE MODEL TRAINING")
    print("=" * 80)
    print(f"\nGenres to train: {', '.join(genres_to_train)}")
    
    # Train each genre
    for primary_genre in genres_to_train:
        data_file = script_dir / 'data' / f'{primary_genre}_training_data.csv'
        
        if not data_file.exists():
            print(f"\n❌ No training data found for {primary_genre}")
            print(f"   Please run: python collect_training_data.py --genre {primary_genre}")
            continue
        
        try:
            model_package = trainer.train_genre_model(primary_genre, data_file)
            trainer.save_model(model_package, primary_genre)
        except Exception as e:
            print(f"\n❌ Error training model for {primary_genre}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "=" * 80)
    print("✅ MODEL TRAINING COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    main()
