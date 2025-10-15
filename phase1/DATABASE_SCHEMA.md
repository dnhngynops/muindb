# Billboard Hot 100 Database Schema

This document describes the database schema for the Billboard Hot 100 music database, containing chart data from 2000 to present.

## Overview

The database is designed with a normalized structure optimized for analysis and queries. It consists of 7 main tables that store chart data, song information, artist details, and pre-calculated statistics.

**Note**: This document describes Phase 1 tables. The `chart_positions` table was removed in October 2025 as it was 100% redundant with `weekly_charts`.

## Core Tables

### 1. `songs` - Master Song Catalog

Deduplicated songs with lifetime statistics across all chart appearances.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `song_id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for each song |
| `song_name` | VARCHAR(255) | NOT NULL, INDEXED | Name of the song |
| `artist_name` | VARCHAR(255) | NOT NULL, INDEXED | Primary artist name |
| `first_chart_appearance` | DATE | NULLABLE, INDEXED | Date of first chart appearance |
| `last_chart_appearance` | DATE | NULLABLE, INDEXED | Date of last chart appearance |
| `total_weeks_on_chart` | INTEGER | NOT NULL, DEFAULT 0 | Total weeks on chart across all appearances |
| `peak_position` | INTEGER | NOT NULL, INDEXED | Best position achieved |
| `weeks_at_number_one` | INTEGER | NOT NULL, DEFAULT 0 | Total weeks at #1 position |
| `weeks_in_top_10` | INTEGER | NOT NULL, DEFAULT 0 | Total weeks in top 10 |
| `weeks_in_top_40` | INTEGER | NOT NULL, DEFAULT 0 | Total weeks in top 40 |
| `created_at` | DATETIME | DEFAULT NOW() | Record creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW(), ON UPDATE NOW() | Record update timestamp |

**Indexes:**
- `idx_song_artist_unique` (song_name, artist_name) - UNIQUE
- `idx_song_peak_position` (peak_position)
- `idx_song_weeks_on_chart` (total_weeks_on_chart)

### 2. `artists` - Master Artist Catalog

Deduplicated artists with career statistics across all their chart appearances.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `artist_id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for each artist |
| `artist_name` | VARCHAR(255) | NOT NULL, UNIQUE, INDEXED | Artist name |
| `first_chart_appearance` | DATE | NULLABLE, INDEXED | Date of first chart appearance |
| `last_chart_appearance` | DATE | NULLABLE, INDEXED | Date of last chart appearance |
| `total_songs` | INTEGER | NOT NULL, DEFAULT 0 | Total number of songs on chart |
| `total_weeks_on_chart` | INTEGER | NOT NULL, DEFAULT 0 | Total weeks on chart across all songs |
| `number_one_hits` | INTEGER | NOT NULL, DEFAULT 0 | Number of #1 hits |
| `top_10_hits` | INTEGER | NOT NULL, DEFAULT 0 | Number of top 10 hits |
| `top_40_hits` | INTEGER | NOT NULL, DEFAULT 0 | Number of top 40 hits |
| `peak_position` | INTEGER | NULLABLE, INDEXED | Best position achieved by any song |
| `created_at` | DATETIME | DEFAULT NOW() | Record creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW(), ON UPDATE NOW() | Record update timestamp |

### 3. `weekly_charts` - Complete Historical Record

All weekly chart entries with complete historical data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `entry_id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for each chart entry |
| `song_id` | INTEGER | FOREIGN KEY, NOT NULL, INDEXED | Reference to songs table |
| `chart_date` | DATE | NOT NULL, INDEXED | Date of the chart |
| `year` | INTEGER | NOT NULL, INDEXED | Year of the chart |
| `week_number` | INTEGER | NULLABLE | Week number within the year |
| `current_position` | INTEGER | NOT NULL, INDEXED | Current week's position |
| `last_week_position` | INTEGER | NULLABLE | Previous week's position |
| `peak_position` | INTEGER | NOT NULL | Peak position achieved |
| `weeks_on_chart` | INTEGER | NOT NULL | Consecutive weeks on chart |
| `position_change` | INTEGER | NULLABLE | Change from last week |
| `is_new_entry` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether this is a new entry |
| `created_at` | DATETIME | DEFAULT NOW() | Record creation timestamp |

**Indexes:**
- `idx_weekly_charts_date_position` (chart_date, current_position)
- `idx_weekly_charts_year_position` (year, current_position)
- `idx_weekly_charts_song_date` (song_id, chart_date) - UNIQUE
- `idx_weekly_charts_position` (current_position)

### 4. `yearly_charts` - Yearly Chart Summaries

Pre-calculated yearly statistics and summaries.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `year_id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `year` | INTEGER | NOT NULL, UNIQUE, INDEXED | Year |
| `total_weeks` | INTEGER | NOT NULL, DEFAULT 0 | Total weeks in the year |
| `total_unique_songs` | INTEGER | NOT NULL, DEFAULT 0 | Unique songs that charted |
| `total_entries` | INTEGER | NOT NULL, DEFAULT 0 | Total chart entries |
| `number_one_songs` | INTEGER | NOT NULL, DEFAULT 0 | Number of different #1 songs |
| `most_weeks_at_number_one` | INTEGER | NOT NULL, DEFAULT 0 | Most weeks any song spent at #1 |
| `longest_staying_song` | VARCHAR(255) | NULLABLE | Song with longest chart run |
| `longest_staying_weeks` | INTEGER | NULLABLE | Weeks for longest staying song |
| `created_at` | DATETIME | DEFAULT NOW() | Record creation timestamp |

### 5. `chart_weeks` - Weekly Chart Metadata

Metadata about each weekly chart including number one songs and statistics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `week_id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `chart_date` | DATE | NOT NULL, UNIQUE, INDEXED | Date of the chart |
| `year` | INTEGER | NOT NULL, INDEXED | Year of the chart |
| `week_number` | INTEGER | NULLABLE | Week number within the year |
| `total_entries` | INTEGER | NOT NULL, DEFAULT 100 | Total entries in chart |
| `new_entries` | INTEGER | NOT NULL, DEFAULT 0 | New entries this week |
| `re_entries` | INTEGER | NOT NULL, DEFAULT 0 | Re-entries this week |
| `number_one_song` | VARCHAR(255) | NULLABLE | Song at #1 position |
| `number_one_artist` | VARCHAR(255) | NULLABLE | Artist of #1 song |
| `created_at` | DATETIME | DEFAULT NOW() | Record creation timestamp |

### 6. `song_stats` - Pre-calculated Song Statistics

Performance statistics for songs by year, optimized for fast queries.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `stat_id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `song_id` | INTEGER | FOREIGN KEY, NOT NULL, INDEXED | Reference to songs table |
| `year` | INTEGER | NULLABLE, INDEXED | Year (NULL for lifetime stats) |
| `total_weeks` | INTEGER | NOT NULL, DEFAULT 0 | Total weeks on chart |
| `peak_position` | INTEGER | NOT NULL | Peak position achieved |
| `weeks_at_number_one` | INTEGER | NOT NULL, DEFAULT 0 | Weeks at #1 position |
| `weeks_in_top_10` | INTEGER | NOT NULL, DEFAULT 0 | Weeks in top 10 |
| `weeks_in_top_40` | INTEGER | NOT NULL, DEFAULT 0 | Weeks in top 40 |
| `average_position` | DECIMAL(5,2) | NULLABLE | Average position |
| `created_at` | DATETIME | DEFAULT NOW() | Record creation timestamp |

**Indexes:**
- `idx_song_stats_song_year` (song_id, year) - UNIQUE
- `idx_song_stats_year` (year)
- `idx_song_stats_peak_position` (peak_position)

## Utility Tables

### 7. `artist_collaborations` - Artist Collaborations

Tracks songs with multiple artists for analyzing collaboration patterns.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `collaboration_id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `song_id` | INTEGER | FOREIGN KEY, NOT NULL, INDEXED | Reference to songs table |
| `artist_name` | VARCHAR(255) | NOT NULL, INDEXED | Artist name |
| `is_primary_artist` | BOOLEAN | NOT NULL, DEFAULT TRUE | Whether this is the primary artist |
| `is_featured_artist` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether this is a featured artist |
| `created_at` | DATETIME | DEFAULT NOW() | Record creation timestamp |

**Indexes:**
- `idx_artist_collaborations_song` (song_id)
- `idx_artist_collaborations_artist` (artist_name)

## Relationships

### Foreign Key Relationships

1. **weekly_charts.song_id** → **songs.song_id**
2. **song_stats.song_id** → **songs.song_id**
3. **artist_collaborations.song_id** → **songs.song_id**

**Note**: Position history is tracked in `weekly_charts` (includes `current_position`, `last_week_position`, `position_change`)

### SQLAlchemy Relationships

- `Songs.weekly_entries` → `WeeklyCharts` (one-to-many)
- `Songs.song_stats` → `SongStats` (one-to-many)
- `WeeklyCharts.song` → `Songs` (many-to-one)
- `SongStats.song` → `Songs` (many-to-one)

## Constants

The schema includes predefined constants for common chart analysis:

### Chart Positions
- `CHART_SIZE = 100` - Total positions in Hot 100
- `TOP_10 = 10` - Top 10 threshold
- `TOP_40 = 40` - Top 40 threshold
- `NUMBER_ONE = 1` - Number one position

### Performance Categories
- `number_one`: Position 1
- `top_10`: Positions 1-10
- `top_40`: Positions 1-40
- `top_100`: Positions 1-100

### Time Periods
- `2000s`: 2000-2009
- `2010s`: 2010-2019
- `2020s`: 2020-2029

## Design Principles

1. **Normalization**: Data is normalized to reduce redundancy while maintaining query performance
2. **Indexing**: Strategic indexes on frequently queried columns
3. **Pre-calculated Statistics**: Yearly and song statistics are pre-calculated for fast analysis
4. **Flexibility**: Schema supports both detailed weekly analysis and high-level summaries
5. **Extensibility**: Additional utility tables can be added for specific analysis needs

## Usage Examples

### Common Queries

```sql
-- Find all #1 hits from 2020
SELECT s.song_name, s.artist_name, wc.chart_date
FROM songs s
JOIN weekly_charts wc ON s.song_id = wc.song_id
WHERE wc.current_position = 1 AND wc.year = 2020;

-- Get artist with most #1 hits
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

This schema provides a comprehensive foundation for analyzing Billboard Hot 100 data with optimized performance for common analytical queries.
