#!/usr/bin/env python3
"""
Cleanup Script: Remove Genre-Level Terms from Subgenres

This script identifies and removes subgenres that are actually genre-level terms
(e.g., "soul", "funk", "blues") and consolidates them to prevent semantic duplicates.

Problem: When extracting detailed genres from APIs, genre-level terms like "soul"
were being saved as subgenres under multiple parent genres (r&b, pop, rock, etc.).

Solution: Remove these genre-level subgenres and keep only true subgenres like
"neo soul", "nu metal", "teen-pop", etc.
"""

import sys
import sqlite3
from pathlib import Path

# Genre-level terms that should NOT be subgenres
GENRE_LEVEL_TERMS = {
    'soul', 'blues', 'funk', 'disco', 'gospel', 'reggae',
    'punk', 'metal', 'indie', 'dance', 'edm', 'house',
    'techno', 'trance', 'dubstep', 'r&b', 'rnb',
    'rap', 'hip hop', 'hip-hop', 'country', 'folk',
    'rock', 'pop', 'jazz', 'classical', 'latin',
    'electronic', 'alternative', 'other', 'ska',
    'ambient', 'dub', 'industrial', 'grunge'
}


def analyze_problem(conn):
    """Analyze the extent of the problem."""
    cursor = conn.cursor()
    
    print('='*80)
    print('🔍 ANALYZING SUBGENRE DUPLICATES')
    print('='*80)
    
    # Find genre-level terms in subgenres
    placeholders = ','.join(['?' for _ in GENRE_LEVEL_TERMS])
    cursor.execute(f"""
        SELECT s.subgenre_name, COUNT(DISTINCT s.parent_genre_id) as parent_count,
               COUNT(DISTINCT ss.song_id) as song_count
        FROM subgenres s
        LEFT JOIN song_subgenres ss ON s.subgenre_id = ss.subgenre_id
        WHERE s.subgenre_name IN ({placeholders})
        GROUP BY s.subgenre_name
        ORDER BY parent_count DESC, song_count DESC
    """, tuple(GENRE_LEVEL_TERMS))
    
    problem_subgenres = cursor.fetchall()
    
    if problem_subgenres:
        print(f'\n❌ Found {len(problem_subgenres)} genre-level terms stored as subgenres:\n')
        
        total_song_links = 0
        for subgenre, parent_count, song_count in problem_subgenres:
            print(f'  • "{subgenre}": {parent_count} parent genres, {song_count} songs')
            total_song_links += song_count
        
        print(f'\n  Total problematic song-subgenre links: {total_song_links}')
        
        # Count total subgenres
        cursor.execute("SELECT COUNT(*) FROM subgenres")
        total_subgenres = cursor.fetchone()[0]
        
        cursor.execute(f"""
            SELECT COUNT(DISTINCT subgenre_id)
            FROM subgenres
            WHERE subgenre_name IN ({placeholders})
        """, tuple(GENRE_LEVEL_TERMS))
        
        bad_subgenre_count = cursor.fetchone()[0]
        
        print(f'\n  Subgenre records to remove: {bad_subgenre_count}/{total_subgenres}')
        
        return len(problem_subgenres), total_song_links
    else:
        print('\n✅ No genre-level terms found in subgenres!')
        return 0, 0


def cleanup_subgenres(conn, dry_run=True):
    """Remove genre-level terms from subgenres."""
    cursor = conn.cursor()
    
    print('\n' + '='*80)
    if dry_run:
        print('🧪 DRY RUN: Showing what would be removed')
    else:
        print('🧹 CLEANING UP: Removing genre-level subgenres')
    print('='*80)
    
    # Get all subgenre IDs that need to be removed
    placeholders = ','.join(['?' for _ in GENRE_LEVEL_TERMS])
    cursor.execute(f"""
        SELECT subgenre_id, subgenre_name, parent_genre_id
        FROM subgenres
        WHERE subgenre_name IN ({placeholders})
    """, tuple(GENRE_LEVEL_TERMS))
    
    to_remove = cursor.fetchall()
    
    if not to_remove:
        print('\n✅ Nothing to remove!')
        return 0
    
    print(f'\nWill remove {len(to_remove)} subgenre records:')
    
    # Group by name for display
    by_name = {}
    for sid, name, parent_id in to_remove:
        if name not in by_name:
            by_name[name] = []
        by_name[name].append((sid, parent_id))
    
    for name, records in sorted(by_name.items()):
        print(f'\n  "{name}": {len(records)} records')
        for sid, parent_id in records[:3]:  # Show first 3
            cursor.execute("SELECT genre_name FROM genres WHERE genre_id = ?", (parent_id,))
            parent = cursor.fetchone()
            parent_name = parent[0] if parent else "Unknown"
            print(f'    - ID {sid} under {parent_name}')
        if len(records) > 3:
            print(f'    ... and {len(records) - 3} more')
    
    if not dry_run:
        # Delete song_subgenres links first (foreign key)
        subgenre_ids = [sid for sid, _, _ in to_remove]
        placeholders = ','.join(['?' for _ in subgenre_ids])
        
        cursor.execute(f"""
            DELETE FROM song_subgenres
            WHERE subgenre_id IN ({placeholders})
        """, tuple(subgenre_ids))
        
        links_deleted = cursor.rowcount
        print(f'\n  Deleted {links_deleted} song-subgenre links')
        
        # Delete subgenres
        cursor.execute(f"""
            DELETE FROM subgenres
            WHERE subgenre_id IN ({placeholders})
        """, tuple(subgenre_ids))
        
        subgenres_deleted = cursor.rowcount
        print(f'  Deleted {subgenres_deleted} subgenre records')
        
        conn.commit()
        print('\n✅ Cleanup complete!')
        
        return subgenres_deleted
    else:
        print(f'\n⚠️  DRY RUN: No changes made. Run with --execute to perform cleanup.')
        return 0


def show_statistics(conn):
    """Show before/after statistics."""
    cursor = conn.cursor()
    
    print('\n' + '='*80)
    print('📊 CURRENT STATISTICS')
    print('='*80)
    
    # Total subgenres
    cursor.execute("SELECT COUNT(*) FROM subgenres")
    total = cursor.fetchone()[0]
    
    # Unique subgenre names
    cursor.execute("SELECT COUNT(DISTINCT subgenre_name) FROM subgenres")
    unique_names = cursor.fetchone()[0]
    
    # Subgenres with multiple parents
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT subgenre_name
            FROM subgenres
            GROUP BY subgenre_name
            HAVING COUNT(DISTINCT parent_genre_id) > 1
        )
    """)
    multi_parent = cursor.fetchone()[0]
    
    # Total song-subgenre links
    cursor.execute("SELECT COUNT(*) FROM song_subgenres")
    total_links = cursor.fetchone()[0]
    
    print(f'\n  Total subgenre records: {total}')
    print(f'  Unique subgenre names: {unique_names}')
    print(f'  Subgenres across multiple parents: {multi_parent}')
    print(f'  Total song-subgenre links: {total_links}')


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup genre-level terms from subgenres')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually perform the cleanup (default is dry-run)')
    parser.add_argument('--db', type=str,
                       default='../../../data/music_database.db',
                       help='Database path')
    
    args = parser.parse_args()
    
    db_path = Path(__file__).parent / args.db
    
    if not db_path.exists():
        print(f'❌ Database not found: {db_path}')
        return 1
    
    print('='*80)
    print('🧹 SUBGENRE CLEANUP UTILITY')
    print('='*80)
    print(f'\nDatabase: {db_path}')
    print(f'Mode: {"EXECUTE" if args.execute else "DRY RUN"}')
    
    conn = sqlite3.connect(db_path)
    
    try:
        # Show current state
        show_statistics(conn)
        
        # Analyze the problem
        problem_count, song_count = analyze_problem(conn)
        
        if problem_count > 0:
            # Clean up
            cleanup_subgenres(conn, dry_run=not args.execute)
            
            if args.execute:
                # Show updated stats
                show_statistics(conn)
        
        print('\n' + '='*80)
        print('✅ ANALYSIS COMPLETE')
        print('='*80)
        
        if not args.execute and problem_count > 0:
            print('\nTo perform the cleanup, run:')
            print('  python cleanup_duplicate_subgenres.py --execute')
        
    finally:
        conn.close()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

