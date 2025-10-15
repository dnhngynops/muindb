-- Phase 2 Schema Extension: Genre and Credits (Genius API)
-- Extends the existing Billboard database with genre and credits information from Genius API
-- Generated for Billboard Hot 100 Database Phase 2

-- =============================================
-- GENRE TABLES
-- =============================================

-- 1. Genres - Master genre catalog with hierarchical structure
CREATE TABLE genres (
    genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
    genre_name VARCHAR(100) NOT NULL UNIQUE,
    parent_genre_id INTEGER,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_genre_id) REFERENCES genres(genre_id)
);

-- Indexes for genres table
CREATE INDEX idx_genres_genre_name ON genres(genre_name);
CREATE INDEX idx_genres_parent_genre_id ON genres(parent_genre_id);

-- 2. Song Genres - Many-to-many relationship between songs and genres
CREATE TABLE song_genres (
    song_genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    confidence_score DECIMAL(3,2) DEFAULT 1.0, -- 0.0 to 1.0 confidence in genre assignment
    source VARCHAR(50) DEFAULT 'genius', -- genius, manual, etc.
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(genre_id) ON DELETE CASCADE,
    UNIQUE(song_id, genre_id)
);

-- Indexes for song_genres table
CREATE INDEX idx_song_genres_song_id ON song_genres(song_id);
CREATE INDEX idx_song_genres_genre_id ON song_genres(genre_id);
CREATE INDEX idx_song_genres_confidence ON song_genres(confidence_score);

-- =============================================
-- CREDITS TABLES
-- =============================================

-- 3. Credit Roles - Types of credits (writer, producer, etc.)
CREATE TABLE credit_roles (
    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    role_category VARCHAR(30) NOT NULL, -- creative, technical, performance, etc.
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for credit_roles table
CREATE INDEX idx_credit_roles_role_name ON credit_roles(role_name);
CREATE INDEX idx_credit_roles_category ON credit_roles(role_category);

-- 4. Credits - Master credits catalog (people who worked on songs)
CREATE TABLE credits (
    credit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    credit_name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL, -- For matching variations
    genius_id INTEGER, -- Genius Artist ID
    is_verified BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for credits table
CREATE INDEX idx_credits_credit_name ON credits(credit_name);
CREATE INDEX idx_credits_normalized_name ON credits(normalized_name);
CREATE INDEX idx_credits_genius_id ON credits(genius_id);
CREATE UNIQUE INDEX idx_credits_name_normalized ON credits(normalized_name);

-- 5. Song Credits - Many-to-many relationship between songs and credits with roles
CREATE TABLE song_credits (
    song_credit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    credit_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE, -- True if this is the main artist
    source VARCHAR(50) DEFAULT 'genius', -- genius, manual, etc.
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE,
    FOREIGN KEY (credit_id) REFERENCES credits(credit_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES credit_roles(role_id) ON DELETE CASCADE,
    UNIQUE(song_id, credit_id, role_id)
);

-- Indexes for song_credits table
CREATE INDEX idx_song_credits_song_id ON song_credits(song_id);
CREATE INDEX idx_song_credits_credit_id ON song_credits(credit_id);
CREATE INDEX idx_song_credits_role_id ON song_credits(role_id);
CREATE INDEX idx_song_credits_is_primary ON song_credits(is_primary);

-- =============================================
-- GENIUS API METADATA TABLES
-- =============================================

-- 6. Song Genius Metadata - Store Genius API metadata for songs
CREATE TABLE song_genius_metadata (
    metadata_id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    genius_id INTEGER NOT NULL UNIQUE,
    genius_url VARCHAR(500),
    release_date VARCHAR(50),
    lyrics_state VARCHAR(20),
    pyongs_count INTEGER DEFAULT 0,
    hot BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- Indexes for song_genius_metadata table
CREATE INDEX idx_song_genius_metadata_song_id ON song_genius_metadata(song_id);
CREATE INDEX idx_song_genius_metadata_genius_id ON song_genius_metadata(genius_id);

-- =============================================
-- TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- =============================================

-- Trigger to update updated_at timestamp for genres table
CREATE TRIGGER update_genres_timestamp 
    AFTER UPDATE ON genres
    FOR EACH ROW
    BEGIN
        UPDATE genres SET updated_at = CURRENT_TIMESTAMP WHERE genre_id = NEW.genre_id;
    END;

-- Trigger to update updated_at timestamp for credits table
CREATE TRIGGER update_credits_timestamp 
    AFTER UPDATE ON credits
    FOR EACH ROW
    BEGIN
        UPDATE credits SET updated_at = CURRENT_TIMESTAMP WHERE credit_id = NEW.credit_id;
    END;

-- Trigger to update updated_at timestamp for song_genius_metadata table
CREATE TRIGGER update_song_genius_metadata_timestamp 
    AFTER UPDATE ON song_genius_metadata
    FOR EACH ROW
    BEGIN
        UPDATE song_genius_metadata SET updated_at = CURRENT_TIMESTAMP WHERE metadata_id = NEW.metadata_id;
    END;

-- =============================================
-- VIEWS FOR COMMON QUERIES
-- =============================================

-- View for songs with their genres
CREATE VIEW songs_with_genres AS
SELECT 
    s.song_id,
    s.song_name,
    s.artist_name,
    s.peak_position,
    s.total_weeks_on_chart,
    GROUP_CONCAT(g.genre_name, ', ') as genres,
    GROUP_CONCAT(sg.confidence_score, ', ') as genre_confidence
FROM songs s
LEFT JOIN song_genres sg ON s.song_id = sg.song_id
LEFT JOIN genres g ON sg.genre_id = g.genre_id
GROUP BY s.song_id, s.song_name, s.artist_name, s.peak_position, s.total_weeks_on_chart;

-- View for songs with their credits
CREATE VIEW songs_with_credits AS
SELECT 
    s.song_id,
    s.song_name,
    s.artist_name,
    s.peak_position,
    s.total_weeks_on_chart,
    GROUP_CONCAT(
        CASE 
            WHEN sc.is_primary = 1 THEN c.credit_name || ' (Artist)'
            ELSE c.credit_name || ' (' || cr.role_name || ')'
        END, 
        ', '
    ) as credits
FROM songs s
LEFT JOIN song_credits sc ON s.song_id = sc.song_id
LEFT JOIN credits c ON sc.credit_id = c.credit_id
LEFT JOIN credit_roles cr ON sc.role_id = cr.role_id
GROUP BY s.song_id, s.song_name, s.artist_name, s.peak_position, s.total_weeks_on_chart;

-- View for comprehensive song information
CREATE VIEW songs_complete AS
SELECT 
    s.song_id,
    s.song_name,
    s.artist_name,
    s.peak_position,
    s.total_weeks_on_chart,
    s.weeks_at_number_one,
    s.first_chart_appearance,
    s.last_chart_appearance,
    sgm.genius_id,
    sgm.genius_url,
    sgm.release_date,
    sgm.pyongs_count,
    sgm.hot,
    GROUP_CONCAT(DISTINCT g.genre_name, ', ') as genres,
    GROUP_CONCAT(DISTINCT 
        CASE 
            WHEN sc.is_primary = 1 THEN c.credit_name || ' (Artist)'
            ELSE c.credit_name || ' (' || cr.role_name || ')'
        END, 
        ', '
    ) as credits
FROM songs s
LEFT JOIN song_genius_metadata sgm ON s.song_id = sgm.song_id
LEFT JOIN song_genres sg ON s.song_id = sg.song_id
LEFT JOIN genres g ON sg.genre_id = g.genre_id
LEFT JOIN song_credits sc ON s.song_id = sc.song_id
LEFT JOIN credits c ON sc.credit_id = c.credit_id
LEFT JOIN credit_roles cr ON sc.role_id = cr.role_id
GROUP BY s.song_id, s.song_name, s.artist_name, s.peak_position, 
         s.total_weeks_on_chart, s.weeks_at_number_one, 
         s.first_chart_appearance, s.last_chart_appearance,
         sgm.genius_id, sgm.genius_url, sgm.release_date, 
         sgm.pyongs_count, sgm.hot;

-- =============================================
-- INITIAL DATA POPULATION
-- =============================================

-- Insert common credit roles
INSERT INTO credit_roles (role_name, role_category, description) VALUES
('Artist', 'performance', 'Main performing artist'),
('Featured Artist', 'performance', 'Featured performer'),
('Writer', 'creative', 'Songwriter/composer'),
('Producer', 'technical', 'Record producer'),
('Co-Writer', 'creative', 'Co-songwriter'),
('Co-Producer', 'technical', 'Co-producer'),
('Arranger', 'creative', 'Music arranger'),
('Engineer', 'technical', 'Recording engineer'),
('Mixer', 'technical', 'Mixing engineer'),
('Mastering Engineer', 'technical', 'Mastering engineer'),
('Vocalist', 'performance', 'Lead vocalist'),
('Backing Vocalist', 'performance', 'Backing vocalist'),
('Instrumentalist', 'performance', 'Instrumental performer');

-- Insert common genres (hierarchical structure)
INSERT INTO genres (genre_name, parent_genre_id, description) VALUES
-- Main categories
('Pop', NULL, 'Popular music'),
('Hip Hop', NULL, 'Hip-hop and rap music'),
('R&B', NULL, 'Rhythm and blues'),
('Rock', NULL, 'Rock music'),
('Country', NULL, 'Country music'),
('Electronic', NULL, 'Electronic music'),
('Jazz', NULL, 'Jazz music'),
('Classical', NULL, 'Classical music'),
('Alternative', NULL, 'Alternative music'),
('Indie', NULL, 'Independent music'),

-- Pop subgenres
('Pop Rock', 1, 'Pop rock music'),
('Dance Pop', 1, 'Dance-oriented pop'),
('Teen Pop', 1, 'Teen-oriented pop'),
('Adult Contemporary', 1, 'Adult contemporary pop'),

-- Hip Hop subgenres
('Trap', 2, 'Trap music'),
('Drill', 2, 'Drill music'),
('Conscious Hip Hop', 2, 'Conscious hip-hop'),
('Gangsta Rap', 2, 'Gangsta rap'),

-- R&B subgenres
('Contemporary R&B', 3, 'Contemporary R&B'),
('Soul', 3, 'Soul music'),
('Neo-Soul', 3, 'Neo-soul'),

-- Rock subgenres
('Alternative Rock', 4, 'Alternative rock'),
('Indie Rock', 4, 'Independent rock'),
('Pop Rock', 4, 'Pop rock'),
('Soft Rock', 4, 'Soft rock'),
('Hard Rock', 4, 'Hard rock'),

-- Electronic subgenres
('EDM', 6, 'Electronic dance music'),
('House', 6, 'House music'),
('Techno', 6, 'Techno music'),
('Trance', 6, 'Trance music'),

-- Country subgenres
('Country Pop', 5, 'Country pop'),
('Country Rock', 5, 'Country rock'),
('Bluegrass', 5, 'Bluegrass music');

-- =============================================
-- COMMON QUERY EXAMPLES
-- =============================================

-- Example: Find all songs in a specific genre
/*
SELECT s.song_name, s.artist_name, s.peak_position, g.genre_name
FROM songs s
JOIN song_genres sg ON s.song_id = sg.song_id
JOIN genres g ON sg.genre_id = g.genre_id
WHERE g.genre_name = 'Pop'
ORDER BY s.peak_position;
*/

-- Example: Find all songs by a specific writer
/*
SELECT s.song_name, s.artist_name, s.peak_position, c.credit_name, cr.role_name
FROM songs s
JOIN song_credits sc ON s.song_id = sc.song_id
JOIN credits c ON sc.credit_id = c.credit_id
JOIN credit_roles cr ON sc.role_id = cr.role_id
WHERE c.credit_name LIKE '%Max Martin%' AND cr.role_name = 'Writer'
ORDER BY s.peak_position;
*/

-- Example: Find songs with both genre and credits information
/*
SELECT s.song_name, s.artist_name, s.peak_position, 
       GROUP_CONCAT(DISTINCT g.genre_name) as genres,
       GROUP_CONCAT(DISTINCT c.credit_name || ' (' || cr.role_name || ')') as credits
FROM songs s
LEFT JOIN song_genres sg ON s.song_id = sg.song_id
LEFT JOIN genres g ON sg.genre_id = g.genre_id
LEFT JOIN song_credits sc ON s.song_id = sc.song_id
LEFT JOIN credits c ON sc.credit_id = c.credit_id
LEFT JOIN credit_roles cr ON sc.role_id = cr.role_id
WHERE s.song_name LIKE '%Shape of You%'
GROUP BY s.song_id, s.song_name, s.artist_name, s.peak_position;
*/

-- Example: Get genre distribution statistics
/*
SELECT g.genre_name, COUNT(sg.song_id) as song_count, 
       AVG(s.peak_position) as avg_peak_position
FROM genres g
LEFT JOIN song_genres sg ON g.genre_id = sg.genre_id
LEFT JOIN songs s ON sg.song_id = s.song_id
GROUP BY g.genre_id, g.genre_name
HAVING song_count > 0
ORDER BY song_count DESC;
*/

-- Example: Find songs with Genius metadata
/*
SELECT s.song_name, s.artist_name, sgm.genius_url, sgm.pyongs_count, sgm.hot
FROM songs s
JOIN song_genius_metadata sgm ON s.song_id = sgm.song_id
WHERE sgm.hot = 1
ORDER BY sgm.pyongs_count DESC;
*/