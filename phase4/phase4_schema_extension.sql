-- Phase 4 Schema Extension: Producer Management Tracking
-- Extends the existing Billboard database with producer management and A&R insights
-- Generated for Billboard Hot 100 Database Phase 4

-- =============================================
-- MANAGEMENT COMPANIES TABLES
-- =============================================

-- 1. Management Companies - Master catalog of management companies
CREATE TABLE management_companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name VARCHAR(255) NOT NULL UNIQUE,
    company_type VARCHAR(50) NOT NULL, -- 'management', 'label', 'publisher', 'agency'
    website VARCHAR(500),
    headquarters VARCHAR(255),
    founded_year INTEGER,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for management_companies table
CREATE INDEX idx_management_companies_name ON management_companies(company_name);
CREATE INDEX idx_management_companies_type ON management_companies(company_type);
CREATE INDEX idx_management_companies_active ON management_companies(is_active);

-- 2. Producer Management - Tracks which producers are under management
CREATE TABLE producer_management (
    management_id INTEGER PRIMARY KEY AUTOINCREMENT,
    producer_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    management_type VARCHAR(50) NOT NULL, -- 'exclusive', 'non-exclusive', 'former'
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT TRUE,
    notes TEXT,
    source VARCHAR(100) DEFAULT 'manual', -- 'manual', 'api', 'web_scrape'
    confidence_score DECIMAL(3,2) DEFAULT 1.0, -- 0.0 to 1.0 confidence in data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producer_id) REFERENCES credits(credit_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES management_companies(company_id) ON DELETE CASCADE,
    UNIQUE(producer_id, company_id, management_type)
);

-- Indexes for producer_management table
CREATE INDEX idx_producer_management_producer ON producer_management(producer_id);
CREATE INDEX idx_producer_management_company ON producer_management(company_id);
CREATE INDEX idx_producer_management_current ON producer_management(is_current);
CREATE INDEX idx_producer_management_type ON producer_management(management_type);

-- 3. Management Verification - Tracks verification attempts and results
CREATE TABLE management_verification (
    verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    producer_id INTEGER NOT NULL,
    company_id INTEGER,
    verification_methods TEXT, -- JSON array of methods: ['api', 'web_scrape', 'manual', 'social_media']
    verification_status VARCHAR(20) NOT NULL, -- 'verified', 'unverified', 'disputed', 'pending'
    verification_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    verification_notes TEXT, -- JSON array of notes
    source_urls TEXT, -- JSON array of URLs
    confidence_score DECIMAL(3,2) DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producer_id) REFERENCES credits(credit_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES management_companies(company_id) ON DELETE CASCADE
);

-- Indexes for management_verification table
CREATE INDEX idx_management_verification_producer ON management_verification(producer_id);
CREATE INDEX idx_management_verification_status ON management_verification(verification_status);
CREATE INDEX idx_management_verification_method ON management_verification(verification_method);

-- =============================================
-- A&R INSIGHTS TABLES
-- =============================================

-- 4. Producer Performance Metrics - Tracks producer success metrics
CREATE TABLE producer_performance_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    producer_id INTEGER NOT NULL,
    year INTEGER,
    total_songs INTEGER DEFAULT 0,
    number_one_hits INTEGER DEFAULT 0,
    top_10_hits INTEGER DEFAULT 0,
    top_40_hits INTEGER DEFAULT 0,
    total_weeks_on_chart INTEGER DEFAULT 0,
    average_peak_position DECIMAL(5,2),
    success_rate DECIMAL(5,2), -- percentage of songs that charted
    genre_diversity_score DECIMAL(3,2), -- how many different genres they work in
    collaboration_count INTEGER DEFAULT 0, -- how many different artists they work with
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producer_id) REFERENCES credits(credit_id) ON DELETE CASCADE,
    UNIQUE(producer_id, year)
);

-- Indexes for producer_performance_metrics table
CREATE INDEX idx_producer_performance_producer ON producer_performance_metrics(producer_id);
CREATE INDEX idx_producer_performance_year ON producer_performance_metrics(year);
CREATE INDEX idx_producer_performance_success ON producer_performance_metrics(success_rate);

-- 5. Management Effectiveness - Tracks how effective different management companies are
CREATE TABLE management_effectiveness (
    effectiveness_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER,
    total_producers INTEGER DEFAULT 0,
    active_producers INTEGER DEFAULT 0,
    total_hits INTEGER DEFAULT 0,
    number_one_hits INTEGER DEFAULT 0,
    average_success_rate DECIMAL(5,2),
    top_producer_id INTEGER, -- producer with most hits this year
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES management_companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (top_producer_id) REFERENCES credits(credit_id) ON DELETE CASCADE,
    UNIQUE(company_id, year)
);

-- Indexes for management_effectiveness table
CREATE INDEX idx_management_effectiveness_company ON management_effectiveness(company_id);
CREATE INDEX idx_management_effectiveness_year ON management_effectiveness(year);
CREATE INDEX idx_management_effectiveness_success ON management_effectiveness(average_success_rate);

-- =============================================
-- TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- =============================================

-- Trigger to update updated_at timestamp for management_companies table
CREATE TRIGGER update_management_companies_timestamp 
    AFTER UPDATE ON management_companies
    FOR EACH ROW
    BEGIN
        UPDATE management_companies SET updated_at = CURRENT_TIMESTAMP WHERE company_id = NEW.company_id;
    END;

-- Trigger to update updated_at timestamp for producer_management table
CREATE TRIGGER update_producer_management_timestamp 
    AFTER UPDATE ON producer_management
    FOR EACH ROW
    BEGIN
        UPDATE producer_management SET updated_at = CURRENT_TIMESTAMP WHERE management_id = NEW.management_id;
    END;

-- Trigger to update updated_at timestamp for producer_performance_metrics table
CREATE TRIGGER update_producer_performance_timestamp 
    AFTER UPDATE ON producer_performance_metrics
    FOR EACH ROW
    BEGIN
        UPDATE producer_performance_metrics SET updated_at = CURRENT_TIMESTAMP WHERE metric_id = NEW.metric_id;
    END;

-- Trigger to update updated_at timestamp for management_effectiveness table
CREATE TRIGGER update_management_effectiveness_timestamp 
    AFTER UPDATE ON management_effectiveness
    FOR EACH ROW
    BEGIN
        UPDATE management_effectiveness SET updated_at = CURRENT_TIMESTAMP WHERE effectiveness_id = NEW.effectiveness_id;
    END;

-- =============================================
-- VIEWS FOR COMMON QUERIES
-- =============================================

-- View for producers with their management information
CREATE VIEW producers_with_management AS
SELECT 
    c.credit_id,
    c.credit_name,
    c.normalized_name,
    mc.company_name,
    mc.company_type,
    pm.management_type,
    pm.start_date,
    pm.end_date,
    pm.is_current,
    pm.confidence_score,
    pm.source
FROM credits c
LEFT JOIN producer_management pm ON c.credit_id = pm.producer_id
LEFT JOIN management_companies mc ON pm.company_id = mc.company_id
WHERE c.credit_id IN (
    SELECT DISTINCT sc.credit_id 
    FROM song_credits sc 
    JOIN credit_roles cr ON sc.role_id = cr.role_id 
    WHERE cr.role_name = 'Producer'
);

-- View for management company effectiveness
CREATE VIEW management_effectiveness_summary AS
SELECT 
    mc.company_name,
    mc.company_type,
    COUNT(DISTINCT pm.producer_id) as total_producers,
    COUNT(DISTINCT CASE WHEN pm.is_current = 1 THEN pm.producer_id END) as active_producers,
    AVG(ppm.success_rate) as avg_success_rate,
    SUM(ppm.number_one_hits) as total_number_ones,
    SUM(ppm.top_10_hits) as total_top_10s
FROM management_companies mc
LEFT JOIN producer_management pm ON mc.company_id = pm.company_id
LEFT JOIN producer_performance_metrics ppm ON pm.producer_id = ppm.producer_id
GROUP BY mc.company_id, mc.company_name, mc.company_type;

-- View for top producers by management company
CREATE VIEW top_producers_by_management AS
SELECT 
    mc.company_name,
    c.credit_name as producer_name,
    ppm.total_songs,
    ppm.number_one_hits,
    ppm.top_10_hits,
    ppm.success_rate,
    pm.management_type,
    pm.is_current
FROM management_companies mc
JOIN producer_management pm ON mc.company_id = pm.company_id
JOIN credits c ON pm.producer_id = c.credit_id
JOIN producer_performance_metrics ppm ON c.credit_id = ppm.producer_id
WHERE pm.is_current = 1
ORDER BY mc.company_name, ppm.success_rate DESC;

-- =============================================
-- INITIAL DATA POPULATION
-- =============================================

-- Insert common management companies (major players in the industry)
INSERT INTO management_companies (company_name, company_type, headquarters, founded_year, description) VALUES
-- Major Management Companies
('Roc Nation', 'management', 'New York, NY', 2008, 'Full-service entertainment company founded by Jay-Z'),
('Scooter Braun Projects', 'management', 'Los Angeles, CA', 2007, 'Management company founded by Scooter Braun'),
('Red Light Management', 'management', 'Charlottesville, VA', 1991, 'Independent music management company'),
('Maverick Management', 'management', 'Los Angeles, CA', 1992, 'Management company founded by Madonna and Guy Oseary'),
('Full Stop Management', 'management', 'Los Angeles, CA', 2000, 'Management company founded by Irving Azoff'),
('The Azoff Company', 'management', 'Los Angeles, CA', 2019, 'Management company founded by Irving Azoff'),
('Maverick', 'management', 'Los Angeles, CA', 1992, 'Management and entertainment company'),
('Crush Music', 'management', 'New York, NY', 2010, 'Management company founded by Jonathan Daniel'),
('Salxco', 'management', 'Los Angeles, CA', 2000, 'Management company founded by Sal Slaiby'),
('The Weeknd XO', 'management', 'Toronto, Canada', 2011, 'Management company for The Weeknd and XO artists'),

-- Major Record Labels (also manage producers)
('Universal Music Group', 'label', 'Santa Monica, CA', 1934, 'Major record label and music corporation'),
('Sony Music Entertainment', 'label', 'New York, NY', 1929, 'Major record label and music corporation'),
('Warner Music Group', 'label', 'New York, NY', 1958, 'Major record label and music corporation'),
('Atlantic Records', 'label', 'New York, NY', 1947, 'Record label owned by Warner Music Group'),
('Interscope Records', 'label', 'Santa Monica, CA', 1990, 'Record label owned by Universal Music Group'),
('Republic Records', 'label', 'New York, NY', 1995, 'Record label owned by Universal Music Group'),
('Columbia Records', 'label', 'New York, NY', 1888, 'Record label owned by Sony Music Entertainment'),
('RCA Records', 'label', 'New York, NY', 1901, 'Record label owned by Sony Music Entertainment'),
('Capitol Records', 'label', 'Hollywood, CA', 1942, 'Record label owned by Universal Music Group'),
('Def Jam Recordings', 'label', 'New York, NY', 1984, 'Record label owned by Universal Music Group'),

-- Publishing Companies
('Sony/ATV Music Publishing', 'publisher', 'Nashville, TN', 1995, 'Music publishing company'),
('Universal Music Publishing Group', 'publisher', 'Santa Monica, CA', 2007, 'Music publishing company'),
('Warner Chappell Music', 'publisher', 'Los Angeles, CA', 1987, 'Music publishing company'),
('Kobalt Music', 'publisher', 'London, UK', 2000, 'Independent music publishing company'),
('BMG Rights Management', 'publisher', 'Berlin, Germany', 2008, 'Music publishing company'),

-- Independent/Unknown
('Independent', 'management', 'Various', NULL, 'Independent or self-managed producers'),
('Unknown', 'management', 'Unknown', NULL, 'Management status unknown or unverified');

-- =============================================
-- COMMON QUERY EXAMPLES
-- =============================================

-- Example: Find all producers under management
/*
SELECT c.credit_name, mc.company_name, pm.management_type, pm.is_current
FROM credits c
JOIN producer_management pm ON c.credit_id = pm.producer_id
JOIN management_companies mc ON pm.company_id = mc.company_id
WHERE pm.is_current = 1
ORDER BY mc.company_name, c.credit_name;
*/

-- Example: Find top performing producers by management company
/*
SELECT mc.company_name, c.credit_name, ppm.success_rate, ppm.number_one_hits
FROM management_companies mc
JOIN producer_management pm ON mc.company_id = pm.company_id
JOIN credits c ON pm.producer_id = c.credit_id
JOIN producer_performance_metrics ppm ON c.credit_id = ppm.producer_id
WHERE pm.is_current = 1
ORDER BY mc.company_name, ppm.success_rate DESC;
*/

-- Example: Find unmanaged producers with high success rates
/*
SELECT c.credit_name, ppm.success_rate, ppm.number_one_hits, ppm.total_songs
FROM credits c
JOIN producer_performance_metrics ppm ON c.credit_id = ppm.producer_id
LEFT JOIN producer_management pm ON c.credit_id = pm.producer_id AND pm.is_current = 1
WHERE pm.producer_id IS NULL
AND ppm.success_rate > 0.5
ORDER BY ppm.success_rate DESC;
*/
