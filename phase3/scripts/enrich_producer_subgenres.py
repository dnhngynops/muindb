#!/usr/bin/env python3
"""
Producer-Based Subgenre Enrichment Script

Uses Phase 2 producer credits to add song-specific subgenres based on
producer genre specialization patterns.

Usage:
    python enrich_producer_subgenres.py                 # All years
    python enrich_producer_subgenres.py --year 2000     # Specific year
    python enrich_producer_subgenres.py --year 2000-2003  # Year range
"""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from genre_classification_system import GenreClassificationSystem
import sqlite3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_stats(db_path: str, year: str = None):
    """Get statistics on producer-based subgenre enrichment."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    year_filter = f"AND strftime('%Y', s.first_chart_appearance) = '{year}'" if year else ""
    
    # Get enrichment stats
    cursor.execute(f"""
        SELECT 
            COUNT(DISTINCT s.song_id) as enriched_songs,
            COUNT(*) as subgenre_links
        FROM songs s
        JOIN song_subgenres ss ON s.song_id = ss.song_id
        WHERE ss.source = 'producer_specialization'
        {year_filter}
    """)
    
    enriched, links = cursor.fetchone()
    
    # Get total songs
    cursor.execute(f"""
        SELECT COUNT(DISTINCT s.song_id)
        FROM songs s
        WHERE 1=1 {year_filter}
    """)
    
    total = cursor.fetchone()[0]
    
    # Get top subgenres
    cursor.execute(f"""
        SELECT sub.subgenre_name, COUNT(*) as count
        FROM songs s
        JOIN song_subgenres ss ON s.song_id = ss.song_id
        JOIN subgenres sub ON ss.subgenre_id = sub.subgenre_id
        WHERE ss.source = 'producer_specialization'
        {year_filter}
        GROUP BY sub.subgenre_name
        ORDER BY count DESC
        LIMIT 5
    """)
    
    top_subgenres = cursor.fetchall()
    
    conn.close()
    
    return {
        'total_songs': total,
        'enriched_songs': enriched,
        'subgenre_links': links,
        'percentage': (enriched / total * 100) if total > 0 else 0,
        'top_subgenres': top_subgenres
    }


def main():
    parser = argparse.ArgumentParser(description='Enrich songs with producer-based subgenres')
    parser.add_argument('--year', type=str, help='Year or year range (e.g., 2000 or 2000-2003)')
    parser.add_argument('--db', type=str, 
                       default='../../../data/music_database.db',
                       help='Database path')
    
    args = parser.parse_args()
    
    print('='*80)
    print('🎵 PRODUCER-BASED SUBGENRE ENRICHMENT')
    print('='*80)
    
    classifier = GenreClassificationSystem()
    
    # Determine years to process
    if args.year:
        if '-' in args.year:
            start, end = args.year.split('-')
            years = [str(y) for y in range(int(start), int(end) + 1)]
        else:
            years = [args.year]
    else:
        years = [None]  # Process all years
    
    # Process each year
    for year in years:
        year_label = f"Year {year}" if year else "All years"
        print(f'\n\n📊 Processing: {year_label}')
        print('─'*80)
        
        # Get stats before
        stats_before = get_stats(args.db, year)
        print(f'\nBefore enrichment:')
        print(f'  • Songs with producer subgenres: {stats_before["enriched_songs"]} ({stats_before["percentage"]:.1f}%)')
        
        # Run enrichment
        print(f'\n🔄 Running enrichment...')
        classifier.enrich_with_producer_subgenres(year=year)
        
        # Get stats after
        stats_after = get_stats(args.db, year)
        print(f'\nAfter enrichment:')
        print(f'  • Songs enriched: {stats_after["enriched_songs"]} ({stats_after["percentage"]:.1f}%)')
        print(f'  • Subgenre links added: {stats_after["subgenre_links"]}')
        print(f'  • Improvement: +{stats_after["enriched_songs"] - stats_before["enriched_songs"]} songs')
        
        if stats_after['top_subgenres']:
            print(f'\n  🎯 Top subgenres added:')
            for subgenre, count in stats_after['top_subgenres']:
                print(f'     • {subgenre}: {count} assignments')
    
    print(f'\n\n{"="*80}')
    print('✅ ENRICHMENT COMPLETE!')
    print('='*80)
    print('''
Key Benefits:
  ✅ Song-specific hints based on producer style
  ✅ High confidence (0.85-0.95) from producer specialization
  ✅ Uses existing Phase 2 data (no new API calls)
  ✅ Complements API subgenres with production insight

Examples of Producer Signatures:
  • Max Martin → dance-pop, teen-pop (Britney, 'N Sync)
  • Timbaland → alternative-r&b, contemporary-r&b (Aaliyah, Missy)
  • Dr. Dre → west-coast-hip-hop, g-funk (Eminem, Snoop Dogg)
  • The Neptunes → alternative-hip-hop, pop-rap (Nelly, Clipse)
  • Byron Gallimore → contemporary-country, country-pop (Tim McGraw)
    ''')


if __name__ == '__main__':
    main()

