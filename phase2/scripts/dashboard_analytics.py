#!/usr/bin/env python3
"""
Dashboard Analytics
Combines artist-producer analysis and progress monitoring for Phase 2.
Provides comprehensive analytics and monitoring for dashboard display.
"""

import sys
import time
from pathlib import Path
from sqlalchemy import func, text

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

from database.connection import get_database_manager
from database.models import Songs
from database.phase2_models import Credits, SongCredits, CreditRoles, SongGeniusMetadata
from sqlalchemy import extract

def analyze_artist_producers():
    """Analyze the artist_producers data."""
    print("🎵 Artist-Producers Analysis")
    print("=" * 50)
    
    # Initialize database
    db_manager = get_database_manager()
    
    with db_manager.get_session() as session:
        # Overall statistics
        print("\n📊 OVERALL STATISTICS")
        print("-" * 30)
        
        stats_sql = """
        SELECT 
            COUNT(*) as total_artist_producers,
            COUNT(CASE WHEN is_verified = 1 THEN 1 END) as verified_count,
            AVG(artist_song_count) as avg_artist_songs,
            AVG(producer_song_count) as avg_producer_songs,
            AVG(total_songs) as avg_total_songs,
            MAX(total_songs) as max_total_songs,
            MIN(total_songs) as min_total_songs
        FROM artist_producers;
        """
        
        stats = session.execute(text(stats_sql)).fetchone()
        
        print(f"Total artist-producers: {stats[0]}")
        print(f"Verified: {stats[1]}")
        print(f"Average artist songs: {stats[2]:.1f}")
        print(f"Average producer songs: {stats[3]:.1f}")
        print(f"Average total songs: {stats[4]:.1f}")
        print(f"Max total songs: {stats[5]}")
        print(f"Min total songs: {stats[6]}")
        
        # Top artist-producers by total songs
        print("\n🏆 TOP 15 ARTIST-PRODUCERS BY TOTAL SONGS")
        print("-" * 50)
        
        top_sql = """
        SELECT 
            credit_name,
            artist_song_count,
            producer_song_count,
            total_songs,
            first_artist_song_date,
            first_producer_song_date
        FROM artist_producers
        ORDER BY total_songs DESC, credit_name
        LIMIT 15;
        """
        
        top_artist_producers = session.execute(text(top_sql)).fetchall()
        
        for i, (name, artist_count, producer_count, total, first_artist, first_producer) in enumerate(top_artist_producers, 1):
            print(f"{i:2d}. {name}")
            print(f"    • Artist: {artist_count} songs (first: {first_artist})")
            print(f"    • Producer: {producer_count} songs (first: {first_producer})")
            print(f"    • Total: {total} songs")
            print()
        
        # Artists who are primarily producers
        print("\n🎛️ ARTISTS WHO ARE PRIMARILY PRODUCERS")
        print("-" * 50)
        
        primarily_producer_sql = """
        SELECT 
            credit_name,
            artist_song_count,
            producer_song_count,
            total_songs,
            ROUND(producer_song_count * 100.0 / total_songs, 1) as producer_percentage
        FROM artist_producers
        WHERE producer_song_count > artist_song_count
        ORDER BY producer_percentage DESC, total_songs DESC
        LIMIT 10;
        """
        
        primarily_producers = session.execute(text(primarily_producer_sql)).fetchall()
        
        for i, (name, artist_count, producer_count, total, producer_pct) in enumerate(primarily_producers, 1):
            print(f"{i:2d}. {name}")
            print(f"    • Artist: {artist_count} songs")
            print(f"    • Producer: {producer_count} songs ({producer_pct}%)")
            print(f"    • Total: {total} songs")
            print()
        
        # Artists who are primarily artists
        print("\n🎤 ARTISTS WHO ARE PRIMARILY PERFORMERS")
        print("-" * 50)
        
        primarily_artist_sql = """
        SELECT 
            credit_name,
            artist_song_count,
            producer_song_count,
            total_songs,
            ROUND(artist_song_count * 100.0 / total_songs, 1) as artist_percentage
        FROM artist_producers
        WHERE artist_song_count > producer_song_count
        ORDER BY artist_percentage DESC, total_songs DESC
        LIMIT 10;
        """
        
        primarily_artists = session.execute(text(primarily_artist_sql)).fetchall()
        
        for i, (name, artist_count, producer_count, total, artist_pct) in enumerate(primarily_artists, 1):
            print(f"{i:2d}. {name}")
            print(f"    • Artist: {artist_count} songs ({artist_pct}%)")
            print(f"    • Producer: {producer_count} songs")
            print(f"    • Total: {total} songs")
            print()
        
        # Balanced artist-producers (similar counts)
        print("\n⚖️ BALANCED ARTIST-PRODUCERS")
        print("-" * 50)
        
        balanced_sql = """
        SELECT 
            credit_name,
            artist_song_count,
            producer_song_count,
            total_songs,
            ABS(artist_song_count - producer_song_count) as difference
        FROM artist_producers
        WHERE ABS(artist_song_count - producer_song_count) <= 1
        ORDER BY total_songs DESC
        LIMIT 10;
        """
        
        balanced = session.execute(text(balanced_sql)).fetchall()
        
        for i, (name, artist_count, producer_count, total, diff) in enumerate(balanced, 1):
            print(f"{i:2d}. {name}")
            print(f"    • Artist: {artist_count} songs")
            print(f"    • Producer: {producer_count} songs")
            print(f"    • Total: {total} songs (difference: {diff})")
            print()
        
        # Genre analysis (if we have genre data)
        print("\n🎭 GENRE ANALYSIS OF ARTIST-PRODUCERS")
        print("-" * 50)
        
        # This would require joining with genre data from Phase 3
        # For now, we'll just show the basic info
        print("Note: Genre analysis requires Phase 3 genre data")
        print("This analysis will be available after running Phase 3 genre classification")

def search_artist_producer(name):
    """Search for a specific artist-producer."""
    print(f"\n🔍 SEARCHING FOR: {name}")
    print("-" * 30)
    
    db_manager = get_database_manager()
    
    with db_manager.get_session() as session:
        search_sql = """
        SELECT 
            credit_name,
            normalized_name,
            artist_song_count,
            producer_song_count,
            total_songs,
            first_artist_song_date,
            first_producer_song_date,
            is_verified
        FROM artist_producers
        WHERE credit_name LIKE :name OR normalized_name LIKE :name
        ORDER BY total_songs DESC;
        """
        
        results = session.execute(text(search_sql), {"name": f"%{name}%"}).fetchall()
        
        if results:
            for name, normalized, artist_count, producer_count, total, first_artist, first_producer, verified in results:
                print(f"Name: {name}")
                print(f"Normalized: {normalized}")
                print(f"Artist songs: {artist_count} (first: {first_artist})")
                print(f"Producer songs: {producer_count} (first: {first_producer})")
                print(f"Total songs: {total}")
                print(f"Verified: {'Yes' if verified else 'No'}")
                print()
        else:
            print(f"No artist-producer found matching '{name}'")

def monitor_progress():
    """Monitor the enrichment progress for 2000 songs."""
    
    print("📊 PHASE 2 ENRICHMENT PROGRESS MONITOR")
    print("=" * 50)
    print("Monitoring 2000 Billboard enrichment process...")
    print()
    
    db_manager = get_database_manager()
    
    with db_manager.get_session() as session:
        # Get total songs from 2000
        total_songs = session.query(Songs).filter(
            extract('year', Songs.first_chart_appearance) == 2000
        ).count()
        
        # Get songs with credits
        songs_with_credits = session.query(Songs).join(SongCredits).filter(
            extract('year', Songs.first_chart_appearance) == 2000
        ).distinct().count()
        
        # Get songs with genius metadata
        songs_with_metadata = session.query(Songs).join(SongGeniusMetadata).filter(
            extract('year', Songs.first_chart_appearance) == 2000
        ).distinct().count()
        
        # Calculate percentages
        credits_percentage = (songs_with_credits / total_songs) * 100 if total_songs > 0 else 0
        metadata_percentage = (songs_with_metadata / total_songs) * 100 if total_songs > 0 else 0
        
        print(f"📈 ENRICHMENT PROGRESS:")
        print(f"   • Total 2000 songs: {total_songs}")
        print(f"   • Songs with credits: {songs_with_credits} ({credits_percentage:.1f}%)")
        print(f"   • Songs with metadata: {songs_with_metadata} ({metadata_percentage:.1f}%)")
        print()
        
        # Get recent activity (last 10 songs processed)
        recent_songs = session.query(Songs).join(SongCredits).filter(
            extract('year', Songs.first_chart_appearance) == 2000
        ).order_by(SongCredits.created_at.desc()).limit(10).all()
        
        if recent_songs:
            print("🕒 RECENT ACTIVITY (Last 10 songs with credits):")
            for song in recent_songs:
                print(f"   • {song.song_name} by {song.artist_name}")
            print()
        
        # Get credits statistics
        total_credits = session.query(Credits).count()
        total_song_credits = session.query(SongCredits).count()
        
        print(f"📊 CREDITS STATISTICS:")
        print(f"   • Total unique credits: {total_credits}")
        print(f"   • Total song-credit relationships: {total_song_credits}")
        print()
        
        # Get top credited people
        top_credits = session.query(
            Credits.credit_name,
            func.count(SongCredits.song_id).label('song_count')
        ).join(SongCredits).group_by(Credits.credit_name).order_by(
            func.count(SongCredits.song_id).desc()
        ).limit(10).all()
        
        if top_credits:
            print("🏆 TOP 10 MOST CREDITED PEOPLE:")
            for i, (name, count) in enumerate(top_credits, 1):
                print(f"   {i:2d}. {name}: {count} songs")
            print()
        
        # Overall status
        if credits_percentage >= 90:
            status = "✅ EXCELLENT"
        elif credits_percentage >= 70:
            status = "🟡 GOOD"
        elif credits_percentage >= 50:
            status = "🟠 MODERATE"
        else:
            status = "🔴 NEEDS WORK"
        
        print(f"🎯 OVERALL STATUS: {status}")
        print(f"   Credits coverage: {credits_percentage:.1f}%")
        print(f"   Metadata coverage: {metadata_percentage:.1f}%")

def run_dashboard_analytics():
    """Run all dashboard analytics and monitoring."""
    print("📊 DASHBOARD ANALYTICS")
    print("=" * 50)
    print("Running comprehensive analytics and monitoring...")
    print()
    
    # Run progress monitoring
    monitor_progress()
    print()
    
    # Run artist-producer analysis
    analyze_artist_producers()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Dashboard Analytics for Phase 2')
    parser.add_argument('--monitor', action='store_true', help='Monitor progress only')
    parser.add_argument('--analyze', action='store_true', help='Analyze artist-producers only')
    parser.add_argument('--search', '-s', help='Search for specific artist-producer')
    parser.add_argument('--all', action='store_true', help='Run all analytics (default)')
    
    args = parser.parse_args()
    
    if args.monitor:
        monitor_progress()
    elif args.analyze:
        analyze_artist_producers()
    elif args.search:
        search_artist_producer(args.search)
    else:
        # Default: run all analytics
        run_dashboard_analytics()
