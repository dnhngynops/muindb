# Billboard Music Database - Phase 1: Core Database

This is Phase 1 of the Billboard Hot 100 music database project, containing the core database functionality and data processing.

## Overview

Phase 1 establishes the foundation of the Billboard music database with:
- Complete database schema for chart data
- Data processing and cleaning pipelines
- Billboard chart data from 2000-2025
- Pre-calculated statistics and analytics
- Database setup and management tools

## What's Included

### Database Schema
- **7 core tables**: songs, artists, weekly_charts, yearly_charts, chart_weeks, song_stats, artist_collaborations
- **Comprehensive indexing** for optimal performance
- **Pre-calculated statistics** for fast queries
- **Normalized design** to reduce redundancy
- **Note**: `weekly_charts` includes position history (chart_positions table removed as redundant)

### Data Processing
- **JSON data processing** from yearly Billboard files
- **Data cleaning and normalization**
- **Duplicate detection and removal**
- **Quality reporting and validation**

### Key Features
- 11,645 unique songs
- 5,107 unique artists
- 134,400 weekly chart entries
- Complete chart history from 2000-2025
- Pre-calculated yearly and song statistics

## Files Structure

```
phase1/
├── README.md                           # This file
├── DATABASE_SCHEMA.md                  # Complete schema documentation
├── schema.sql                          # SQL DDL for database creation
├── requirements.txt                    # Python dependencies
├── scripts/
│   ├── setup_database.py              # Database initialization
│   ├── process_billboard_data.py      # Main data processing script
│   ├── populate_missing_tables.py     # Table population utilities
│   └── quick_start.py                 # Quick setup and test
└── src/
    ├── database/
    │   ├── connection.py              # Database connection management
    │   └── models.py                  # SQLAlchemy models
    ├── processors/
    │   └── data_cleaner.py            # Data cleaning utilities
    └── utils/
        └── config.py                  # Configuration management
```

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up the database**:
   ```bash
   python scripts/setup_database.py
   ```

3. **Process Billboard data**:
   ```bash
   python scripts/process_billboard_data.py
   ```

4. **Quick test**:
   ```bash
   python scripts/quick_start.py
   ```

## Database Schema

The database includes 8 main tables:

### Core Tables
- **songs**: Master song catalog with lifetime statistics
- **artists**: Master artist catalog with career statistics  
- **weekly_charts**: Complete historical chart entries
- **yearly_charts**: Pre-calculated yearly summaries
- **chart_weeks**: Weekly chart metadata
- **song_stats**: Pre-calculated song statistics

### Utility Tables
- **artist_collaborations**: Multi-artist song tracking
- **Note**: Position history is tracked in `weekly_charts` table

## Key Statistics

- **Total Songs**: 11,645 unique songs
- **Total Artists**: 5,107 unique artists
- **Chart Entries**: 134,400 weekly entries
- **Date Range**: 2000-2025
- **Average Chart Run**: 11.7 weeks per song

## Example Queries

```sql
-- Find all #1 hits from 2020
SELECT s.song_name, s.artist_name, wc.chart_date
FROM songs s
JOIN weekly_charts wc ON s.song_id = wc.song_id
WHERE wc.current_position = 1 AND wc.year = 2020;

-- Get top 10 artists by #1 hits
SELECT artist_name, number_one_hits
FROM artists
ORDER BY number_one_hits DESC
LIMIT 10;

-- Find songs with longest chart runs
SELECT song_name, artist_name, total_weeks_on_chart
FROM songs
ORDER BY total_weeks_on_chart DESC
LIMIT 10;
```

## Next Steps

Phase 1 provides the foundation. To add genre and credits functionality, proceed to **Phase 2**.

---

**Phase 1 Status**: ✅ Complete  
**Last Updated**: 2024  
**Version**: 1.0.0