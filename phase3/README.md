# Phase 3: Multi-Source Genre Classification

This phase focuses on comprehensive genre classification using multiple data sources with A&R-grade precision.

## Overview

Phase 3 builds upon Phase 2 (credit enrichment) by adding multi-source genre classification to songs in the Billboard database. It integrates data from Spotify, Last.fm, Chartmetric, and Genius to provide industry-standard genre tagging with confidence scoring and A&R insights.

## Features

- **Multi-Source API Integration**: Spotify (algorithmic), Last.fm (community), Chartmetric (industry), Genius (database)
- **Weighted Genre Classification**: Source-weighted confidence scoring (Spotify 40%, Last.fm 30%, Chartmetric 20%, Genius 10%)
- **A&R-Grade Analytics**: Market positioning, crossover potential, commercial viability analysis
- **11 Primary Genres**: Pop, Hip-hop, Rock, Alternative, Country, Electronic, R&B, Latin, Folk, Jazz, Other
- **166 API-Based Subgenres**: Detailed genre tags (neo soul, nu metal, post-grunge, etc.) with automatic filtering of generic terms
- **Producer-Based Subgenre Enrichment**: Uses Phase 2 credits to add subgenres based on producer specialization patterns (180 producers mapped)
- **Producer/Songwriter Genre Analysis**: Genre classification based on catalog analysis
- **Subgenre Duplicate Prevention**: Validates and filters genre-level terms to maintain clean subgenre data
- **Database Optimization**: Unified genre tables with confidence scoring and source tracking

## Database Schema

### Database Tables

Phase 3 **enhances Phase 2's existing genre tables** with multi-source data and adds subgenre support:
- `genres` (Phase 2): Master genre catalog - 11 primary genres
- `song_genres` (Phase 2): Song-genre relationships - enriched with confidence scores
- `subgenres` (NEW): 166 detailed subgenres (neo soul, nu metal, etc.) with parent genre relationships
- `song_subgenres` (NEW): Song-subgenre assignments with confidence, source tracking, and ranking
- `artist_producers`: Artist-producer tracking (41 identified)

**Coverage (October 13, 2025)**:
- Primary genres: 1,004 songs (years 2000-2002, 100% each year)
- Subgenres: 307 songs across years 2000-2001 (44% avg coverage)
- Producer associations: 841 producers total, 689 with genre tags (82%)

**Note**: Phase 3 writes multi-source genre data (Spotify, Last.fm, Chartmetric) to the existing Phase 2 genre tables rather than creating separate Spotify-specific tables. This provides a unified genre classification system with both primary genres and detailed subgenres.

## Setup

1. **Environment Variables**: Set up API credentials in `.env` file:
   ```
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   GENIUS_ACCESS_TOKEN=your_genius_token
   LASTFM_API_KEY=your_lastfm_key (optional, fallback available)
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure APIs** (interactive helper):
   ```bash
   python configure_apis.py
   ```

## Usage

### Genre Classification
```bash
# Test classification system
cd phase3
python scripts/genre_classification_system.py --test

# Process batch of artists from 2000
python scripts/genre_processing_manager.py --year 2000 --limit 10

# Classify individual song
python scripts/song_classification_manager.py --song "Song Name" --artist "Artist Name"
```

### Analytics and Insights
```bash
# Generate A&R insights for artists
python scripts/ar_insights_analyzer.py --artist "Artist Name"

# Analyze producer/songwriter genres
python scripts/producer_songwriter_genre_system.py --producer "Producer Name"
```

### Subgenre Enrichment (NEW)
```bash
# Enrich with producer-based subgenres
cd phase3/scripts

# Enrich specific year
python enrich_producer_subgenres.py --year 2000

# Enrich year range
python enrich_producer_subgenres.py --year 2000-2003

# Check for subgenre duplicates (dry run)
python cleanup_duplicate_subgenres.py --db ../../data/music_database.db

# Clean up duplicates (execute)
python cleanup_duplicate_subgenres.py --db ../../data/music_database.db --execute
```

## Scripts

### Core Classification:
- `genre_classification_system.py`: Core multi-source classification engine (Spotify, Last.fm, Chartmetric, Genius) with subgenre extraction
- `genre_processing_manager.py`: Batch processing manager with execution planning
- `song_classification_manager.py`: Song-level classification with audio features
- `ar_insights_analyzer.py`: A&R analytics and market insights
- `producer_songwriter_genre_system.py`: Producer/songwriter genre analysis

### Subgenre Enrichment (NEW):
- `enrich_producer_subgenres.py`: Add subgenres based on producer specialization patterns using Phase 2 credits
- `cleanup_duplicate_subgenres.py`: Utility to identify and remove genre-level terms incorrectly stored as subgenres

### Source Files:
- `src/api/producer_genre_patterns.py`: Producer genre specialization mappings and era-based subgenre definitions

## Current Status (October 13, 2025)

- **Phase 2 Prerequisites**: ✅ Complete (100% credits for 2000, 98.3% for 2001)
- **Multi-Source APIs**: ✅ Working (Spotify, Last.fm, Genius)
- **Genre Classification**: ✅ Years 2000-2002 (1,004 songs, 100% coverage each year)
- **Subgenre System**: ✅ Operational (166 subgenres, 44% coverage for 2000-2001)
- **A&R Analytics**: ✅ Fully functional
- **Genre Distribution (2000)**: Country (94), Hip-hop (82), Pop (80), R&B (59), Alternative (31), Rock (25), Other (15), Latin (13), Jazz (7), Electronic (6), Folk (1)
- **Genre Distribution (2001)**: Hip-Hop (77), Country (59), R&B (54), Pop (46), Rock (29), Alternative (19), Other (9), Latin (5), Electronic (5), Jazz (4), Folk (1)
- **Data Quality**: ✅ Clean (166 subgenres, no duplicates, no orphaned records)

## Next Steps

1. Expand genre classification to all years (2001-2025)
2. Integrate Chartmetric API for industry data (optional, paid)
3. Build dashboard for genre analytics visualization
4. Add machine learning-based genre prediction

## Technical Notes

- Uses WAL mode for better SQLite concurrency
- Implements exponential backoff for database retries
- Handles API rate limiting with configurable delays
- Maintains genre cache for performance
