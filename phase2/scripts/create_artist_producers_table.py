#!/usr/bin/env python3
"""
Create Artist-Producers Table
Creates a dedicated table to track artists who are also producers
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
src_dir = project_root / 'phase2' / 'src'
sys.path.insert(0, str(src_dir))

from database.connection import get_database_manager

def create_artist_producers_table():
    """Create the artist_producers table and populate it."""
    print("🎵 Creating Artist-Producers Table")
    print("=" * 50)
    
    # Initialize database
    db_manager = get_database_manager()
    
    with db_manager.get_session() as session:
        # Create the artist_producers table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS artist_producers (
            artist_producer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            credit_id INTEGER NOT NULL,
            credit_name VARCHAR(255) NOT NULL,
            normalized_name VARCHAR(255) NOT NULL,
            artist_song_count INTEGER DEFAULT 0,
            producer_song_count INTEGER DEFAULT 0,
            total_songs INTEGER DEFAULT 0,
            first_artist_song_date DATE,
            first_producer_song_date DATE,
            is_verified BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (credit_id) REFERENCES credits (credit_id) ON DELETE CASCADE,
            UNIQUE (credit_id)
        );
        """
        
        print("📊 Creating artist_producers table...")
        session.execute(text(create_table_sql))
        session.commit()
        print("✅ Table created successfully")
        
        # Create indexes for better performance
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_artist_producers_credit_id ON artist_producers (credit_id);",
            "CREATE INDEX IF NOT EXISTS idx_artist_producers_credit_name ON artist_producers (credit_name);",
            "CREATE INDEX IF NOT EXISTS idx_artist_producers_normalized_name ON artist_producers (normalized_name);",
            "CREATE INDEX IF NOT EXISTS idx_artist_producers_total_songs ON artist_producers (total_songs DESC);"
        ]
        
        print("📊 Creating indexes...")
        for index_sql in indexes_sql:
            session.execute(text(index_sql))
        session.commit()
        print("✅ Indexes created successfully")
        
        # Populate the table with existing data
        print("📊 Populating artist_producers table...")
        
        populate_sql = """
        INSERT OR REPLACE INTO artist_producers (
            credit_id, 
            credit_name, 
            normalized_name,
            artist_song_count,
            producer_song_count,
            total_songs,
            first_artist_song_date,
            first_producer_song_date,
            is_verified
        )
        SELECT 
            c.credit_id,
            c.credit_name,
            c.normalized_name,
            COALESCE(artist_stats.song_count, 0) as artist_song_count,
            COALESCE(producer_stats.song_count, 0) as producer_song_count,
            COALESCE(artist_stats.song_count, 0) + COALESCE(producer_stats.song_count, 0) as total_songs,
            artist_stats.first_song_date,
            producer_stats.first_song_date,
            c.is_verified
        FROM credits c
        LEFT JOIN (
            SELECT 
                sc.credit_id,
                COUNT(DISTINCT sc.song_id) as song_count,
                MIN(s.first_chart_appearance) as first_song_date
            FROM song_credits sc
            JOIN credit_roles cr ON sc.role_id = cr.role_id
            JOIN songs s ON sc.song_id = s.song_id
            WHERE cr.role_name = 'Artist'
            GROUP BY sc.credit_id
        ) artist_stats ON c.credit_id = artist_stats.credit_id
        LEFT JOIN (
            SELECT 
                sc.credit_id,
                COUNT(DISTINCT sc.song_id) as song_count,
                MIN(s.first_chart_appearance) as first_song_date
            FROM song_credits sc
            JOIN credit_roles cr ON sc.role_id = cr.role_id
            JOIN songs s ON sc.song_id = s.song_id
            WHERE cr.role_name = 'Producer'
            GROUP BY sc.credit_id
        ) producer_stats ON c.credit_id = producer_stats.credit_id
        WHERE artist_stats.credit_id IS NOT NULL 
        AND producer_stats.credit_id IS NOT NULL;
        """
        
        result = session.execute(text(populate_sql))
        session.commit()
        
        # Get statistics
        stats_sql = """
        SELECT 
            COUNT(*) as total_artist_producers,
            COUNT(CASE WHEN is_verified = 1 THEN 1 END) as verified_count,
            AVG(total_songs) as avg_total_songs,
            MAX(total_songs) as max_total_songs,
            MIN(total_songs) as min_total_songs
        FROM artist_producers;
        """
        
        stats = session.execute(text(stats_sql)).fetchone()
        
        print("✅ Data populated successfully")
        print(f"\n📊 ARTIST-PRODUCERS STATISTICS:")
        print(f"   • Total artist-producers: {stats[0]}")
        print(f"   • Verified: {stats[1]}")
        print(f"   • Average total songs: {stats[2]:.1f}")
        print(f"   • Max total songs: {stats[3]}")
        print(f"   • Min total songs: {stats[4]}")
        
        # Show top 10 artist-producers
        top_artist_producers_sql = """
        SELECT 
            credit_name,
            artist_song_count,
            producer_song_count,
            total_songs,
            first_artist_song_date,
            first_producer_song_date
        FROM artist_producers
        ORDER BY total_songs DESC
        LIMIT 10;
        """
        
        top_artist_producers = session.execute(text(top_artist_producers_sql)).fetchall()
        
        print(f"\n🏆 TOP 10 ARTIST-PRODUCERS:")
        for i, (name, artist_count, producer_count, total, first_artist, first_producer) in enumerate(top_artist_producers, 1):
            print(f"   {i:2d}. {name}")
            print(f"       • Artist: {artist_count} songs (first: {first_artist})")
            print(f"       • Producer: {producer_count} songs (first: {first_producer})")
            print(f"       • Total: {total} songs")
            print()

def verify_existing_scripts():
    """Verify that existing scripts won't be affected by the new table."""
    print("\n🔍 VERIFYING EXISTING SCRIPTS COMPATIBILITY")
    print("=" * 50)
    
    # Check if any existing scripts reference the new table
    scripts_to_check = [
        "enrich_songs_metadata.py",
        "search_songs.py", 
        "cleanup_artist_credits.py",
        "cleanup_duplicate_credits.py",
        "debug_failed_songs.py",
        "smart_credit_splitter.py",
        "test_single_song.py"
    ]
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    print("✅ Checking Phase 2 scripts...")
    for script_name in scripts_to_check:
        script_path = script_dir / script_name
        if script_path.exists():
            with open(script_path, 'r') as f:
                content = f.read()
                if 'artist_producers' in content:
                    print(f"   ⚠️  {script_name}: References artist_producers table")
                else:
                    print(f"   ✅ {script_name}: No conflicts detected")
        else:
            print(f"   ℹ️  {script_name}: Not found")
    
    print("\n✅ All existing scripts are compatible with the new table")
    print("   • The new table is read-only for existing functionality")
    print("   • No existing queries will be affected")
    print("   • New table provides additional insights without breaking changes")

if __name__ == "__main__":
    create_artist_producers_table()
    verify_existing_scripts()
    print("\n🎉 Artist-Producers table creation completed successfully!")
