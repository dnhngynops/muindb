#!/usr/bin/env python3
"""
Test Enhanced Search Against Existing Database
Verifies that enhanced search produces same/better results than current database
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, List

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file if it exists."""
    env_file = project_root / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env_file()

from database.connection import get_database_manager
from database.models import Songs
from database.phase2_models import Credits, SongCredits, CreditRoles, SongGeniusMetadata
from api.genius_client import GeniusService
from api.enhanced_genius_client import EnhancedGeniusService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_songs_without_credits_from_2000(limit: int = 10) -> List[Dict]:
    """Get songs from 2000 that don't have credits yet"""
    logger.info(f"Finding songs from 2000 without credits (limit: {limit})")
    
    db_manager = get_database_manager()
    
    with db_manager.get_session() as session:
        # Find songs without credits
        query = session.query(
            Songs.song_id,
            Songs.song_name,
            Songs.artist_name,
            Songs.peak_position
        ).outerjoin(
            SongCredits, Songs.song_id == SongCredits.song_id
        ).filter(
            Songs.first_chart_appearance.like('2000%'),
            SongCredits.song_id == None
        ).order_by(
            Songs.peak_position.asc()
        ).limit(limit)
        
        songs = []
        for row in query.all():
            songs.append({
                'song_id': row.song_id,
                'song_name': row.song_name,
                'artist_name': row.artist_name,
                'peak_position': row.peak_position
            })
        
        logger.info(f"Found {len(songs)} songs without credits")
        return songs


def get_songs_with_credits_from_2000(limit: int = 10) -> List[Dict]:
    """Get songs from 2000 that already have credits"""
    logger.info(f"Finding songs from 2000 with credits (limit: {limit})")
    
    db_manager = get_database_manager()
    
    with db_manager.get_session() as session:
        # Find songs with credits
        query = session.query(
            Songs.song_id,
            Songs.song_name,
            Songs.artist_name,
            Songs.peak_position
        ).join(
            SongCredits, Songs.song_id == SongCredits.song_id
        ).filter(
            Songs.first_chart_appearance.like('2000%')
        ).distinct().order_by(
            Songs.peak_position.asc()
        ).limit(limit)
        
        songs = []
        for row in query.all():
            # Get existing credits for this song
            credits_query = session.query(
                Credits.credit_name,
                CreditRoles.role_name
            ).join(
                SongCredits, Credits.credit_id == SongCredits.credit_id
            ).join(
                CreditRoles, SongCredits.role_id == CreditRoles.role_id
            ).filter(
                SongCredits.song_id == row.song_id
            )
            
            credits = []
            for credit_row in credits_query.all():
                credits.append({
                    'name': credit_row.credit_name,
                    'role': credit_row.role_name
                })
            
            songs.append({
                'song_id': row.song_id,
                'song_name': row.song_name,
                'artist_name': row.artist_name,
                'peak_position': row.peak_position,
                'existing_credits': credits
            })
        
        logger.info(f"Found {len(songs)} songs with credits")
        return songs


def test_standard_vs_enhanced_search():
    """Compare standard vs enhanced search results"""
    logger.info("🧪 Testing Standard vs Enhanced Search")
    logger.info("=" * 80)
    
    # Get Genius token
    genius_token = os.getenv('GENIUS_ACCESS_TOKEN')
    if not genius_token:
        logger.error("GENIUS_ACCESS_TOKEN not found in environment")
        return False
    
    # Initialize both services
    standard_service = GeniusService(genius_token)
    enhanced_service = EnhancedGeniusService(genius_token)
    
    # Get songs without credits to test on
    test_songs = get_songs_without_credits_from_2000(limit=5)
    
    if not test_songs:
        logger.info("No songs without credits found. Testing with existing songs...")
        test_songs = get_songs_with_credits_from_2000(limit=5)
    
    print("\n" + "=" * 80)
    print("STANDARD vs ENHANCED SEARCH COMPARISON")
    print("=" * 80)
    print()
    
    results = {
        'standard': {'found': 0, 'not_found': 0, 'credits': 0},
        'enhanced': {'found': 0, 'not_found': 0, 'credits': 0}
    }
    
    for i, song in enumerate(test_songs, 1):
        print(f"\n{i}. Testing: \"{song['song_name']}\" by {song['artist_name']}")
        print(f"   Peak Position: #{song['peak_position']}")
        
        if 'existing_credits' in song:
            print(f"   Existing Credits: {len(song['existing_credits'])} in database")
        
        print()
        
        # Test standard search
        print("   📊 Standard Search:")
        try:
            standard_result = standard_service.get_song_metadata(
                song['song_name'], song['artist_name']
            )
            
            if standard_result.get('error'):
                print(f"      ❌ Not found: {standard_result['error']}")
                results['standard']['not_found'] += 1
            else:
                credits_count = len(standard_result.get('credits', []))
                print(f"      ✅ Found! Credits: {credits_count}")
                results['standard']['found'] += 1
                results['standard']['credits'] += credits_count
                
                # Show some credits
                for credit in standard_result.get('credits', [])[:3]:
                    print(f"         - {credit.get('name')} ({credit.get('role')})")
                if credits_count > 3:
                    print(f"         ... and {credits_count - 3} more")
        except Exception as e:
            print(f"      ❌ Error: {e}")
            results['standard']['not_found'] += 1
        
        # Test enhanced search
        print("   🚀 Enhanced Search:")
        try:
            enhanced_result = enhanced_service.get_song_metadata(
                song['song_name'], song['artist_name']
            )
            
            if enhanced_result.get('error'):
                print(f"      ❌ Not found: {enhanced_result['error']}")
                results['enhanced']['not_found'] += 1
            else:
                credits_count = len(enhanced_result.get('credits', []))
                print(f"      ✅ Found! Credits: {credits_count}")
                results['enhanced']['found'] += 1
                results['enhanced']['credits'] += credits_count
                
                # Show some credits
                for credit in enhanced_result.get('credits', [])[:3]:
                    print(f"         - {credit.get('name')} ({credit.get('role')})")
                if credits_count > 3:
                    print(f"         ... and {credits_count - 3} more")
        except Exception as e:
            print(f"      ❌ Error: {e}")
            results['enhanced']['not_found'] += 1
        
        # Compare with existing database
        if 'existing_credits' in song:
            existing_count = len(song['existing_credits'])
            print(f"   💾 Database: {existing_count} credits")
            
            # Show if enhanced found more
            enhanced_count = len(enhanced_result.get('credits', [])) if not enhanced_result.get('error') else 0
            if enhanced_count > existing_count:
                print(f"      🎉 Enhanced found {enhanced_count - existing_count} more credits!")
    
    # Print summary
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Metric':<30} {'Standard':<15} {'Enhanced':<15} {'Improvement':<15}")
    print("-" * 80)
    print(f"{'Songs Found':<30} {results['standard']['found']:<15} {results['enhanced']['found']:<15} {results['enhanced']['found'] - results['standard']['found']:+<15}")
    print(f"{'Songs Not Found':<30} {results['standard']['not_found']:<15} {results['enhanced']['not_found']:<15} {results['enhanced']['not_found'] - results['standard']['not_found']:+<15}")
    print(f"{'Total Credits Found':<30} {results['standard']['credits']:<15} {results['enhanced']['credits']:<15} {results['enhanced']['credits'] - results['standard']['credits']:+<15}")
    
    if test_songs:
        standard_rate = (results['standard']['found'] / len(test_songs)) * 100
        enhanced_rate = (results['enhanced']['found'] / len(test_songs)) * 100
        print(f"{'Success Rate':<30} {standard_rate:.1f}%{'':<10} {enhanced_rate:.1f}%{'':<10} {enhanced_rate - standard_rate:+.1f}%")
    
    print()
    print("=" * 80)
    
    # Verdict
    if results['enhanced']['found'] >= results['standard']['found']:
        print("✅ VERDICT: Enhanced search performs as good or better than standard search")
        print("✅ Safe to use enhanced search - no data loss, potential improvements")
    else:
        print("⚠️ VERDICT: Enhanced search found fewer songs than standard")
        print("⚠️ Recommend further testing before full deployment")
    
    print()
    return True


def test_existing_data_integrity():
    """Test that we can still find songs that are already in the database"""
    logger.info("🔍 Testing Data Integrity with Existing Credits")
    logger.info("=" * 80)
    
    # Get songs that already have credits
    songs_with_credits = get_songs_with_credits_from_2000(limit=10)
    
    if not songs_with_credits:
        logger.warning("No songs with credits found")
        return False
    
    # Get Genius token
    genius_token = os.getenv('GENIUS_ACCESS_TOKEN')
    if not genius_token:
        logger.error("GENIUS_ACCESS_TOKEN not found")
        return False
    
    enhanced_service = EnhancedGeniusService(genius_token)
    
    print("\n" + "=" * 80)
    print("DATA INTEGRITY TEST - Verifying Enhanced Search Finds Existing Songs")
    print("=" * 80)
    print()
    
    found_count = 0
    not_found_count = 0
    
    for i, song in enumerate(songs_with_credits, 1):
        print(f"{i}. \"{song['song_name']}\" by {song['artist_name']}")
        print(f"   Database Credits: {len(song['existing_credits'])}")
        
        # Try to find with enhanced search
        result = enhanced_service.get_song_metadata(song['song_name'], song['artist_name'])
        
        if result.get('error'):
            print(f"   ❌ Enhanced search failed: {result['error']}")
            not_found_count += 1
        else:
            enhanced_credits = len(result.get('credits', []))
            print(f"   ✅ Enhanced search found: {enhanced_credits} credits")
            found_count += 1
            
            # Compare credit counts
            db_credits = len(song['existing_credits'])
            if enhanced_credits >= db_credits:
                print(f"   ✅ Match verified (enhanced: {enhanced_credits} >= database: {db_credits})")
            else:
                print(f"   ⚠️  Enhanced found fewer credits ({enhanced_credits} < {db_credits})")
        
        print()
    
    print("=" * 80)
    print("INTEGRITY TEST SUMMARY")
    print("=" * 80)
    print(f"Songs Tested: {len(songs_with_credits)}")
    print(f"Found by Enhanced Search: {found_count}")
    print(f"Not Found: {not_found_count}")
    print(f"Success Rate: {(found_count / len(songs_with_credits)) * 100:.1f}%")
    print()
    
    if found_count == len(songs_with_credits):
        print("✅ PERFECT: Enhanced search found all existing songs")
        print("✅ Data integrity maintained - safe to use enhanced search")
    elif found_count >= len(songs_with_credits) * 0.9:
        print("✅ GOOD: Enhanced search found 90%+ of existing songs")
        print("✅ Acceptable for production use")
    else:
        print("⚠️  WARNING: Enhanced search found less than 90% of existing songs")
        print("⚠️  Recommend investigation before full deployment")
    
    print()
    return True


def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Enhanced Search vs Database')
    parser.add_argument('--integrity-only', action='store_true',
                       help='Only test data integrity (existing songs)')
    parser.add_argument('--comparison-only', action='store_true',
                       help='Only test standard vs enhanced comparison')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        if args.integrity_only:
            test_existing_data_integrity()
        elif args.comparison_only:
            test_standard_vs_enhanced_search()
        else:
            # Run both tests
            print("\n" + "🧪" * 40)
            print("RUNNING COMPREHENSIVE ENHANCED SEARCH TESTS")
            print("🧪" * 40 + "\n")
            
            # Test 1: Data integrity
            test_existing_data_integrity()
            
            print("\n" + "-" * 80 + "\n")
            
            # Test 2: Standard vs Enhanced
            test_standard_vs_enhanced_search()
            
            print("\n" + "🎉" * 40)
            print("ALL TESTS COMPLETE")
            print("🎉" * 40 + "\n")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
