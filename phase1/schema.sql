-- Billboard Hot 100 Database Schema
-- SQL DDL for creating the complete database structure
-- Generated from SQLAlchemy models

-- =============================================
-- CORE TABLES
-- =============================================

-- 1. Songs - Master song catalog with lifetime statistics
CREATE TABLE songs (
    song_id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_name VARCHAR(255) NOT NULL,
    artist_name VARCHAR(255) NOT NULL,
    first_chart_appearance DATE,
    last_chart_appearance DATE,
    total_weeks_on_chart INTEGER NOT NULL DEFAULT 0,
    peak_position INTEGER NOT NULL,
    weeks_at_number_one INTEGER NOT NULL DEFAULT 0,
    weeks_in_top_10 INTEGER NOT NULL DEFAULT 0,
    weeks_in_top_40 INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for songs table
CREATE INDEX idx_songs_song_name ON songs(song_name);
CREATE INDEX idx_songs_artist_name ON songs(artist_name);
CREATE INDEX idx_songs_first_chart_appearance ON songs(first_chart_appearance);
CREATE INDEX idx_songs_last_chart_appearance ON songs(last_chart_appearance);
CREATE INDEX idx_songs_peak_position ON songs(peak_position);
CREATE UNIQUE INDEX idx_song_artist_unique ON songs(song_name, artist_name);
CREATE INDEX idx_song_weeks_on_chart ON songs(total_weeks_on_chart);

-- 2. Artists - Master artist catalog with career statistics
CREATE TABLE artists (
    artist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    artist_name VARCHAR(255) NOT NULL UNIQUE,
    first_chart_appearance DATE,
    last_chart_appearance DATE,
    total_songs INTEGER NOT NULL DEFAULT 0,
    total_weeks_on_chart INTEGER NOT NULL DEFAULT 0,
    number_one_hits INTEGER NOT NULL DEFAULT 0,
    top_10_hits INTEGER NOT NULL DEFAULT 0,
    top_40_hits INTEGER NOT NULL DEFAULT 0,
    peak_position INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for artists table
CREATE INDEX idx_artists_artist_name ON artists(artist_name);
CREATE INDEX idx_artists_first_chart_appearance ON artists(first_chart_appearance);
CREATE INDEX idx_artists_last_chart_appearance ON artists(last_chart_appearance);
CREATE INDEX idx_artists_peak_position ON artists(peak_position);

-- 3. Weekly Charts - Complete historical record
CREATE TABLE weekly_charts (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    chart_date DATE NOT NULL,
    year INTEGER NOT NULL,
    week_number INTEGER,
    current_position INTEGER NOT NULL,
    last_week_position INTEGER,
    peak_position INTEGER NOT NULL,
    weeks_on_chart INTEGER NOT NULL,
    position_change INTEGER,
    is_new_entry BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(song_id)
);

-- Indexes for weekly_charts table
CREATE INDEX idx_weekly_charts_song_id ON weekly_charts(song_id);
CREATE INDEX idx_weekly_charts_chart_date ON weekly_charts(chart_date);
CREATE INDEX idx_weekly_charts_year ON weekly_charts(year);
CREATE INDEX idx_weekly_charts_current_position ON weekly_charts(current_position);
CREATE INDEX idx_weekly_charts_date_position ON weekly_charts(chart_date, current_position);
CREATE INDEX idx_weekly_charts_year_position ON weekly_charts(year, current_position);
CREATE UNIQUE INDEX idx_weekly_charts_song_date ON weekly_charts(song_id, chart_date);

-- 4. Yearly Charts - Yearly chart summaries
CREATE TABLE yearly_charts (
    year_id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL UNIQUE,
    total_weeks INTEGER NOT NULL DEFAULT 0,
    total_unique_songs INTEGER NOT NULL DEFAULT 0,
    total_entries INTEGER NOT NULL DEFAULT 0,
    number_one_songs INTEGER NOT NULL DEFAULT 0,
    most_weeks_at_number_one INTEGER NOT NULL DEFAULT 0,
    longest_staying_song VARCHAR(255),
    longest_staying_weeks INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for yearly_charts table
CREATE INDEX idx_yearly_charts_year ON yearly_charts(year);

-- 5. Chart Weeks - Weekly chart metadata
CREATE TABLE chart_weeks (
    week_id INTEGER PRIMARY KEY AUTOINCREMENT,
    chart_date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    week_number INTEGER,
    total_entries INTEGER NOT NULL DEFAULT 100,
    new_entries INTEGER NOT NULL DEFAULT 0,
    re_entries INTEGER NOT NULL DEFAULT 0,
    number_one_song VARCHAR(255),
    number_one_artist VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for chart_weeks table
CREATE INDEX idx_chart_weeks_chart_date ON chart_weeks(chart_date);
CREATE INDEX idx_chart_weeks_year ON chart_weeks(year);

-- 6. Song Stats - Pre-calculated song statistics
CREATE TABLE song_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    year INTEGER,
    total_weeks INTEGER NOT NULL DEFAULT 0,
    peak_position INTEGER NOT NULL,
    weeks_at_number_one INTEGER NOT NULL DEFAULT 0,
    weeks_in_top_10 INTEGER NOT NULL DEFAULT 0,
    weeks_in_top_40 INTEGER NOT NULL DEFAULT 0,
    average_position DECIMAL(5,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(song_id)
);

-- Indexes for song_stats table
CREATE INDEX idx_song_stats_song_id ON song_stats(song_id);
CREATE INDEX idx_song_stats_year ON song_stats(year);
CREATE INDEX idx_song_stats_peak_position ON song_stats(peak_position);
CREATE UNIQUE INDEX idx_song_stats_song_year ON song_stats(song_id, year);

-- =============================================
-- UTILITY TABLES
-- =============================================

-- 7. Chart Positions - Position history
CREATE TABLE chart_positions (
    position_id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    chart_date DATE NOT NULL,
    position INTEGER NOT NULL,
    position_change INTEGER,
    weeks_on_chart INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(song_id)
);

-- Indexes for chart_positions table
CREATE INDEX idx_chart_positions_song_id ON chart_positions(song_id);
CREATE INDEX idx_chart_positions_chart_date ON chart_positions(chart_date);
CREATE INDEX idx_chart_positions_position ON chart_positions(position);
CREATE INDEX idx_chart_positions_song_date ON chart_positions(song_id, chart_date);

-- 8. Artist Collaborations - Artist collaborations
CREATE TABLE artist_collaborations (
    collaboration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    artist_name VARCHAR(255) NOT NULL,
    is_primary_artist BOOLEAN NOT NULL DEFAULT TRUE,
    is_featured_artist BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(song_id)
);

-- Indexes for artist_collaborations table
CREATE INDEX idx_artist_collaborations_song_id ON artist_collaborations(song_id);
CREATE INDEX idx_artist_collaborations_artist_name ON artist_collaborations(artist_name);

-- =============================================
-- TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- =============================================

-- Trigger to update updated_at timestamp for songs table
CREATE TRIGGER update_songs_timestamp 
    AFTER UPDATE ON songs
    FOR EACH ROW
    BEGIN
        UPDATE songs SET updated_at = CURRENT_TIMESTAMP WHERE song_id = NEW.song_id;
    END;

-- Trigger to update updated_at timestamp for artists table
CREATE TRIGGER update_artists_timestamp 
    AFTER UPDATE ON artists
    FOR EACH ROW
    BEGIN
        UPDATE artists SET updated_at = CURRENT_TIMESTAMP WHERE artist_id = NEW.artist_id;
    END;

-- =============================================
-- VIEWS FOR COMMON QUERIES
-- =============================================

-- View for current week's top 10
CREATE VIEW current_top_10 AS
SELECT 
    s.song_name,
    s.artist_name,
    wc.current_position,
    wc.weeks_on_chart,
    wc.position_change
FROM songs s
JOIN weekly_charts wc ON s.song_id = wc.song_id
WHERE wc.chart_date = (
    SELECT MAX(chart_date) FROM weekly_charts
)
AND wc.current_position <= 10
ORDER BY wc.current_position;

-- View for all-time number one hits
CREATE VIEW number_one_hits AS
SELECT 
    s.song_name,
    s.artist_name,
    s.weeks_at_number_one,
    s.total_weeks_on_chart,
    s.first_chart_appearance,
    s.last_chart_appearance
FROM songs s
WHERE s.peak_position = 1
ORDER BY s.weeks_at_number_one DESC, s.total_weeks_on_chart DESC;

-- View for artist career summaries
CREATE VIEW artist_career_summary AS
SELECT 
    a.artist_name,
    a.total_songs,
    a.number_one_hits,
    a.top_10_hits,
    a.top_40_hits,
    a.total_weeks_on_chart,
    a.first_chart_appearance,
    a.last_chart_appearance,
    a.peak_position
FROM artists a
ORDER BY a.number_one_hits DESC, a.total_songs DESC;

-- View for yearly chart leaders
CREATE VIEW yearly_leaders AS
SELECT 
    yc.year,
    yc.total_unique_songs,
    yc.number_one_songs,
    yc.longest_staying_song,
    yc.longest_staying_weeks,
    yc.most_weeks_at_number_one
FROM yearly_charts yc
ORDER BY yc.year DESC;

-- =============================================
-- COMMON QUERY EXAMPLES
-- =============================================

-- Example: Find all #1 hits from a specific year
/*
SELECT s.song_name, s.artist_name, wc.chart_date
FROM songs s
JOIN weekly_charts wc ON s.song_id = wc.song_id
WHERE wc.current_position = 1 AND wc.year = 2020
ORDER BY wc.chart_date;
*/

-- Example: Get top 10 artists by number of #1 hits
/*
SELECT artist_name, number_one_hits, total_songs
FROM artists
ORDER BY number_one_hits DESC, total_songs DESC
LIMIT 10;
*/

-- Example: Find songs with longest chart runs
/*
SELECT song_name, artist_name, total_weeks_on_chart, peak_position
FROM songs
ORDER BY total_weeks_on_chart DESC
LIMIT 20;
*/

-- Example: Get weekly chart statistics for a year
/*
SELECT 
    year,
    COUNT(DISTINCT song_id) as unique_songs,
    COUNT(*) as total_entries,
    AVG(current_position) as avg_position
FROM weekly_charts
WHERE year = 2020
GROUP BY year;
*/

-- Example: Find songs that spent most weeks at #1
/*
SELECT song_name, artist_name, weeks_at_number_one
FROM songs
WHERE weeks_at_number_one > 0
ORDER BY weeks_at_number_one DESC
LIMIT 10;
*/

-- =============================================
-- CONSTANTS AND REFERENCE DATA
-- =============================================

-- Chart position constants
-- CHART_SIZE = 100
-- TOP_10 = 10  
-- TOP_40 = 40
-- NUMBER_ONE = 1

-- Performance categories
-- number_one: Position 1
-- top_10: Positions 1-10
-- top_40: Positions 1-40
-- top_100: Positions 1-100

-- Time periods
-- 2000s: 2000-2009
-- 2010s: 2010-2019
-- 2020s: 2020-2029
