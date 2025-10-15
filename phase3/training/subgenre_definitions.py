#!/usr/bin/env python3
"""
Subgenre Definitions for ML Training
Defines subgenres for each primary genre with Spotify seed genre names
"""

# Subgenres for ML model training
# Format: 'primary_genre': {'subgenre': 'spotify_seed_name'}

SUBGENRE_DEFINITIONS = {
    'country': {
        'country-pop': 'country',
        'traditional-country': 'classic country',
        'country-rock': 'country rock',
        'bluegrass': 'bluegrass',
        'americana': 'americana',
        'bro-country': 'country',  # 2010s trend
    },
    
    'pop': {
        'dance-pop': 'dance-pop',          # Use hyphenated Spotify seed
        'indie-pop': 'indie-pop',          # Use hyphenated Spotify seed
        'electropop': 'electropop',
        'synth-pop': 'synth-pop',          # Use hyphenated Spotify seed
        'teen-pop': 'pop',
        # NEW 2010s-2020s subgenres
        'alt-pop': 'alt-pop',              # Billie Eilish, Olivia Rodrigo - use hyphenated
        'bedroom-pop': 'indie-pop',        # Clairo - map to indie-pop (no bedroom-pop seed)
        'hyperpop': 'pop',                 # 100 gecs - map to pop (no hyperpop seed yet)
    },
    
    'hip-hop': {
        'trap': 'trap',
        'boom-bap': 'hip hop',
        'conscious-hip-hop': 'conscious hip hop',
        'drill': 'drill',
        'southern-hip-hop': 'southern hip hop',
        # NEW 2015-2025 subgenres (CRITICAL!)
        'melodic-rap': 'melodic rap',      # Rod Wave, Lil Durk, Polo G
        'emo-rap': 'emo rap',              # Juice WRLD, Lil Peep, XXXTentacion
        'rage-rap': 'rage',                # Playboi Carti, Ken Carson
        'soundcloud-rap': 'cloud rap',     # Lil Uzi Vert, early SoundCloud era
    },
    
    'r&b': {
        'contemporary-r&b': 'r&b',
        'neo-soul': 'neo soul',
        'funk': 'funk',
        'soul': 'soul',
        'gospel': 'gospel',
        # NEW 2010s-2020s subgenres
        'alternative-r&b': 'alternative r&b',  # The Weeknd, SZA, Frank Ocean
        'trap-soul': 'trap soul',              # Bryson Tiller, 6LACK, Summer Walker
    },
    
    'alternative': {
        'indie-rock': 'indie rock',
        'emo': 'emo',
        'grunge': 'grunge',
        'post-punk': 'post-punk',
        'indie': 'indie',
        'indie-folk': 'indie folk',  # Bon Iver, The Lumineers
    },
    
    'rock': {
        'hard-rock': 'hard rock',
        'classic-rock': 'classic rock',
        'punk-rock': 'punk rock',
        'metal': 'metal',
        'progressive-rock': 'progressive rock'
    },
    
    # Electronic (use EDM Classifier techniques)
    'electronic': {
        'house': 'house',
        'trance': 'trance',
        'dubstep': 'dubstep',
        'drum-and-bass': 'drum-and-bass',
        'techno': 'techno',
        # NEW 2010s-2020s subgenres
        'future-bass': 'future bass',      # Flume, Chainsmokers, Illenium
        'trap-edm': 'trap',                # RL Grime, Baauer
        'melodic-dubstep': 'melodic dubstep',  # Seven Lions
    },
    
    # Latin (grew massively in 2010s-2020s)
    'latin': {
        'reggaeton': 'reggaeton',
        'latin-pop': 'latin pop',
        'salsa': 'salsa',
        'bachata': 'bachata',
        # NEW 2015-2025 subgenres (CRITICAL!)
        'latin-trap': 'latin trap',        # Bad Bunny, Anuel AA (HUGE in 2020s!)
        'urbano-latino': 'urbano',         # Umbrella term for modern Latin urban
    },
    
    # NEW PRIMARY GENRE for 2018-2025
    'afrobeats': {
        'afro-pop': 'afrobeats',
        'afro-fusion': 'afrobeats',
        'amapiano': 'amapiano',            # South African style
        'afro-r&b': 'afrobeats',
    }
}

# Rule-based subgenres (no ML training needed)
# Used ONLY for low-volume genres without ML models
RULE_BASED_SUBGENRES = {
    'jazz': {
        'smooth-jazz': {'acousticness': (0.4, 0.8), 'energy': (0.3, 0.6)},
        'bebop': {'tempo': (200, 350), 'instrumentalness': (0.5, 1.0)},
        'jazz-fusion': {'energy': (0.6, 0.9), 'instrumentalness': (0.3, 0.8)}
    },
    
    'folk': {
        'folk-rock': {'energy': (0.5, 0.8), 'acousticness': (0.4, 0.7)},
        'singer-songwriter': {'acousticness': (0.6, 0.9), 'speechiness': (0.03, 0.15)},
        'americana': {'acousticness': (0.5, 0.8), 'valence': (0.4, 0.7)}
    }
    
    # NOTE: Electronic removed - now has ML model (per user request)
    # NOTE: Afrobeats removed - now has ML model (per user request)
    # NOTE: Latin removed - upgraded to ML model
    # NOTE: Other has no subgenres (catch-all category)
}

# Most important features per genre (for ML training)
GENRE_FEATURE_IMPORTANCE = {
    'country': ['acousticness', 'tempo', 'valence', 'danceability', 'energy'],
    'pop': ['danceability', 'energy', 'valence', 'tempo', 'loudness'],
    'hip-hop': ['speechiness', 'tempo', 'energy', 'danceability', 'loudness'],
    'r&b': ['energy', 'danceability', 'acousticness', 'valence', 'tempo'],
    'alternative': ['energy', 'acousticness', 'loudness', 'valence', 'instrumentalness'],
    'rock': ['energy', 'loudness', 'tempo', 'acousticness', 'instrumentalness'],
    'electronic': ['tempo', 'energy', 'danceability', 'loudness', 'duration_ms'],
    'latin': ['danceability', 'tempo', 'energy', 'speechiness', 'valence'],
    'afrobeats': ['danceability', 'tempo', 'energy', 'valence', 'instrumentalness'],
}

# Minimum songs needed for ML training
MIN_SONGS_FOR_ML = 25

# Training parameters
TRAINING_CONFIG = {
    'songs_per_subgenre': 800,  # Collect 800 songs per subgenre
    'polynomial_degree': 3,      # Feature engineering
    'test_size': 0.2,            # 80% train, 20% test
    'random_state': 42,
    'ensemble_models': ['rf', 'gb', 'xgb'],  # Random Forest, Gradient Boost, XGBoost
}

def get_ml_genres():
    """Get list of genres that should use ML models"""
    return list(SUBGENRE_DEFINITIONS.keys())

def get_rule_based_genres():
    """Get list of genres that should use rule-based classification"""
    return list(RULE_BASED_SUBGENRES.keys())

def get_subgenres_for_genre(genre: str):
    """Get list of subgenres for a specific genre"""
    if genre in SUBGENRE_DEFINITIONS:
        return list(SUBGENRE_DEFINITIONS[genre].keys())
    elif genre in RULE_BASED_SUBGENRES:
        return list(RULE_BASED_SUBGENRES[genre].keys())
    return []

if __name__ == "__main__":
    print("Subgenre Configuration Summary")
    print("=" * 80)
    print(f"\nML Models will be trained for: {len(SUBGENRE_DEFINITIONS)} genres")
    for genre, subgenres in SUBGENRE_DEFINITIONS.items():
        print(f"  {genre}: {len(subgenres)} subgenres")
    
    print(f"\nRule-based classification for: {len(RULE_BASED_SUBGENRES)} genres")
    for genre, subgenres in RULE_BASED_SUBGENRES.items():
        print(f"  {genre}: {len(subgenres)} subgenres")
