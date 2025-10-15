#!/usr/bin/env python3
"""
Genre Processing Manager
Combines execution planning and batch processing functionality for Phase 3.
Includes: environment verification, database analysis, ARI-style batch processing, and checkpoint management.
"""

import os
import sys
import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import signal
import argparse
from sqlalchemy import func

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file."""
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load .env file
load_env_file()

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

from database.connection import get_database_manager
from database.models import Songs, Artists
from database.phase2_models import Genres, SongGenres
from genre_classification_system import GenreClassificationSystem, ArtistGenreProfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Statistics for batch processing."""
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_processed == 0:
            return 0.0
        return (self.successful / self.total_processed) * 100
    
    @property
    def processing_time(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def processing_rate(self) -> float:
        if self.processing_time > 0:
            return self.total_processed / (self.processing_time / 60)  # per minute
        return 0.0


class GenreProcessingManager:
    """Manages genre processing with execution planning and batch processing capabilities."""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self.genre_system = GenreClassificationSystem()
        self.stats = ProcessingStats()
        self.checkpoint_file = Path(__file__).parent / 'processing_checkpoint.json'
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    def verify_environment_setup(self) -> bool:
        """Verify that all required environment variables and APIs are configured."""
        print("🔍 VERIFYING ENVIRONMENT SETUP")
        print("=" * 50)
        
        required_vars = [
            'SPOTIFY_CLIENT_ID',
            'SPOTIFY_CLIENT_SECRET',
            'LASTFM_API_KEY',
            'GENIUS_ACCESS_TOKEN'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            print("Please set these variables in your .env file")
            return False
        
        print("✅ All required environment variables are set")
        
        # Test API connections
        print("\n🔌 TESTING API CONNECTIONS")
        print("-" * 30)
        
        # Test Spotify
        try:
            spotify_genres = self.genre_system._get_spotify_artist_genres("test")
            print("✅ Spotify API: Connected")
        except Exception as e:
            print(f"❌ Spotify API: {e}")
            return False
        
        # Test Last.fm
        try:
            lastfm_genres = self.genre_system._get_lastfm_artist_genres("test")
            print("✅ Last.fm API: Connected")
        except Exception as e:
            print(f"❌ Last.fm API: {e}")
            return False
        
        # Test Genius
        try:
            genius_genres = self.genre_system._get_genius_artist_genres("test")
            print("✅ Genius API: Connected")
        except Exception as e:
            print(f"❌ Genius API: {e}")
            return False
        
        print("\n✅ All API connections successful!")
        return True
    
    def analyze_database_state(self) -> Dict[str, Any]:
        """Analyze the current state of the database."""
        print("\n📊 ANALYZING DATABASE STATE")
        print("=" * 50)
        
        with self.db_manager.get_session() as session:
            # Get total songs
            total_songs = session.query(Songs).count()
            print(f"Total songs in database: {total_songs}")
            
            # Get songs with genres
            songs_with_genres = session.query(Songs).join(SongGenres).distinct().count()
            print(f"Songs with genre classifications: {songs_with_genres}")
            
            # Get genre distribution
            genre_dist = session.query(
                Genres.genre_name,
                func.count(SongGenres.song_id).label('count')
            ).join(SongGenres).group_by(Genres.genre_name).all()
            
            print(f"\nGenre distribution:")
            for genre, count in genre_dist:
                print(f"  {genre}: {count} songs")
            
            # Get songs from 2000
            songs_2000 = session.query(Songs).filter(
                Songs.first_chart_appearance.like('2000%')
            ).count()
            print(f"\nSongs from 2000: {songs_2000}")
            
            # Get songs from 2000 with genres
            songs_2000_with_genres = session.query(Songs).join(SongGenres).filter(
                Songs.first_chart_appearance.like('2000%')
            ).distinct().count()
            print(f"Songs from 2000 with genres: {songs_2000_with_genres}")
            
            return {
                'total_songs': total_songs,
                'songs_with_genres': songs_with_genres,
                'songs_2000': songs_2000,
                'songs_2000_with_genres': songs_2000_with_genres,
                'genre_distribution': dict(genre_dist)
            }
    
    def show_execution_plan(self):
        """Show the recommended execution plan."""
        print("\n📋 EXECUTION PLAN")
        print("=" * 50)
        
        print("1. Environment Setup:")
        print("   - Verify all API keys are configured")
        print("   - Test API connections")
        print("   - Check database connectivity")
        
        print("\n2. Database Analysis:")
        print("   - Analyze current genre coverage")
        print("   - Identify songs needing classification")
        print("   - Check for data quality issues")
        
        print("\n3. Batch Processing:")
        print("   - Process songs in batches for efficiency")
        print("   - Use checkpoint system for resumability")
        print("   - Monitor progress and handle errors")
        
        print("\n4. Verification:")
        print("   - Verify all songs are classified")
        print("   - Check data quality and consistency")
        print("   - Generate final statistics")
        
        print("\n5. A&R Insights:")
        print("   - Generate analytics and insights")
        print("   - Create reports for decision making")
        print("   - Export data for external use")
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load processing checkpoint if it exists."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        return None
    
    def save_checkpoint(self, checkpoint_data: Dict[str, Any]):
        """Save processing checkpoint."""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def clear_checkpoint(self):
        """Clear processing checkpoint."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
    
    def process_artists_batch(self, artists: List[str], batch_size: int = 10, year: str = None) -> ProcessingStats:
        """Process a batch of artists for genre classification."""
        print(f"\n🎵 PROCESSING BATCH OF {len(artists)} ARTISTS")
        print("=" * 50)
        
        self.stats.start_time = datetime.now()
        self.stats.total_processed = len(artists)
        
        for i, artist in enumerate(artists):
            if not self.running:
                logger.info("Processing stopped by user")
                break
            
            try:
                print(f"\n🎵 [{i+1}/{len(artists)}] Processing: {artist}")
                
                # Check if already classified (pass year to ensure ALL songs in year are classified)
                existing = self.genre_system._get_existing_classification(artist, year=year)
                if existing and existing.confidence_score >= 0.8:
                    print(f"   ⏭️  Skipped (already classified with high confidence)")
                    self.stats.skipped += 1
                    continue
                
                # Classify artist
                profile = self.genre_system.classify_artist(artist)
                
                if profile and profile.primary_genre:
                    print(f"   ✅ Classification: {profile.primary_genre} (confidence: {profile.confidence_score:.2f})")
                    print(f"   📊 Sources: {', '.join(profile.source_data.keys())}")
                    
                    # Save primary genre to database
                    self.genre_system.save_artist_classification(artist, profile, year=year)
                    print(f"   ✅ Saved primary genre to database")
                    
                    # Save subgenres to database (new!)
                    self.genre_system.save_artist_subgenres(artist, profile, year=year)
                    
                    self.stats.successful += 1
                else:
                    print(f"   ❌ Failed to classify")
                    self.stats.failed += 1
                
                # Save checkpoint every 10 artists
                if (i + 1) % 10 == 0:
                    checkpoint_data = {
                        'processed_artists': i + 1,
                        'total_artists': len(artists),
                        'successful': self.stats.successful,
                        'failed': self.stats.failed,
                        'skipped': self.stats.skipped,
                        'timestamp': datetime.now().isoformat()
                    }
                    self.save_checkpoint(checkpoint_data)
                    print(f"   💾 Checkpoint saved")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing artist {artist}: {e}")
                self.stats.failed += 1
        
        self.stats.end_time = datetime.now()
        return self.stats
    
    def process_year_songs(self, year: int, limit: Optional[int] = None):
        """Process all songs from a specific year for genre classification."""
        print(f"\n🎵 PROCESSING {year} SONGS FOR GENRE CLASSIFICATION")
        print("=" * 60)
        
        with self.db_manager.get_session() as session:
            # Get all songs from specified year
            query = session.query(Songs).filter(
                Songs.first_chart_appearance.like(f'{year}%')
            ).order_by(Songs.peak_position)
            
            if limit:
                query = query.limit(limit)
            
            songs = query.all()
            print(f"Found {len(songs)} songs from {year}")
            
            # Get unique artists
            artists = list(set(song.artist_name for song in songs))
            print(f"Found {len(artists)} unique artists")
            
            # Process artists in batches
            batch_size = 20
            for i in range(0, len(artists), batch_size):
                if not self.running:
                    break
                
                batch = artists[i:i + batch_size]
                print(f"\n📦 Processing batch {i//batch_size + 1}/{(len(artists) + batch_size - 1)//batch_size}")
                
                batch_stats = self.process_artists_batch(batch, batch_size, year=str(year))
                
                # Print progress
                total_processed = i + len(batch)
                print(f"\n📊 PROGRESS UPDATE [{total_processed}/{len(artists)}]")
                print(f"   ✅ Successful: {batch_stats.successful}")
                print(f"   ❌ Failed: {batch_stats.failed}")
                print(f"   ⏭️  Skipped: {batch_stats.skipped}")
                print(f"   🎵 Rate: {batch_stats.processing_rate:.1f} artists/min")
                
                if total_processed < len(artists):
                    remaining = len(artists) - total_processed
                    eta_minutes = remaining / batch_stats.processing_rate if batch_stats.processing_rate > 0 else 0
                    print(f"   ⏰ ETA: {eta_minutes:.1f} minutes")
        
        # Final statistics
        self.print_final_statistics()
    
    def print_final_statistics(self):
        """Print final processing statistics."""
        print("\n" + "=" * 70)
        print("📊 BATCH PROCESSING COMPLETE")
        print("=" * 70)
        
        if self.stats.start_time and self.stats.end_time:
            total_time = (self.stats.end_time - self.stats.start_time).total_seconds()
            print(f"⏰ Total time: {total_time/60:.1f} minutes")
            print(f"📊 Processing rate: {self.stats.processing_rate:.1f} artists/minute")
        
        print(f"📈 FINAL STATISTICS:")
        print(f"   • Total artists processed: {self.stats.total_processed}")
        print(f"   • Successfully classified: {self.stats.successful}")
        print(f"   • Failed classifications: {self.stats.failed}")
        print(f"   • Skipped (already classified): {self.stats.skipped}")
        
        # Get genre distribution
        with self.db_manager.get_session() as session:
            genre_dist = session.query(
                Genres.genre_name,
                func.count(SongGenres.song_id).label('count')
            ).join(SongGenres).group_by(Genres.genre_name).all()
            
            print(f"\n🎵 GENRE DISTRIBUTION:")
            for genre, count in sorted(genre_dist, key=lambda x: x[1], reverse=True):
                percentage = (count / self.stats.successful * 100) if self.stats.successful > 0 else 0
                print(f"   • {genre}: {count} songs ({percentage:.1f}%)")
        
        # Database verification
        with self.db_manager.get_session() as session:
            total_songs_with_genres = session.query(Songs).join(SongGenres).distinct().count()
            total_genres = session.query(Genres).count()
            songs_2000_with_genres = session.query(Songs).join(SongGenres).filter(
                Songs.first_chart_appearance.like('2000%')
            ).distinct().count()
            
            print(f"\n🔍 DATABASE VERIFICATION:")
            print(f"   • Total songs with genres: {total_songs_with_genres}")
            print(f"   • Total genres in database: {total_genres}")
            print(f"   • Songs from 2000 with genres: {songs_2000_with_genres}")
        
        print("\n" + "=" * 70)
        print("🎉 BATCH PROCESSING COMPLETED")
        print("=" * 70)
        
        # Clear checkpoint
        self.clear_checkpoint()


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Genre Processing Manager')
    parser.add_argument('--verify', action='store_true', help='Verify environment setup')
    parser.add_argument('--analyze', action='store_true', help='Analyze database state')
    parser.add_argument('--plan', action='store_true', help='Show execution plan')
    parser.add_argument('--year', type=int, help='Process songs from specific year (e.g., 2001, 2004)')
    parser.add_argument('--process-2000', action='store_true', help='Process all 2000 songs (deprecated: use --year 2000)')
    parser.add_argument('--limit', type=int, help='Limit number of songs to process')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    
    args = parser.parse_args()
    
    manager = GenreProcessingManager()
    
    if args.verify:
        success = manager.verify_environment_setup()
        if not success:
            sys.exit(1)
    
    if args.analyze:
        manager.analyze_database_state()
    
    if args.plan:
        manager.show_execution_plan()
    
    # Process year (new argument or backward compatible --process-2000)
    year_to_process = args.year if args.year else (2000 if args.process_2000 else None)
    
    if year_to_process:
        manager.process_year_songs(year=year_to_process, limit=args.limit)
    
    if not any([args.verify, args.analyze, args.plan, args.year, args.process_2000]):
        # Default: show help
        parser.print_help()


if __name__ == "__main__":
    main()
