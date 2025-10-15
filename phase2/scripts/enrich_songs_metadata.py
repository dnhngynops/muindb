#!/usr/bin/env python3
"""
Song Metadata Enrichment Script (Genius API)
High-performance script with batch processing and optimized database operations.
"""

import sys
import os
import time
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
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
from database.models import Songs
from database.phase2_models import Genres, SongGenres, Credits, SongCredits, CreditRoles, SongGeniusMetadata
from api.genius_client import GeniusService
from api.enhanced_genius_client import EnhancedGeniusService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SongMetadataEnricher:
    """High-performance song metadata enricher with batch processing."""
    
    def __init__(self, genius_access_token: str = None, max_workers: int = 3, use_enhanced_search: bool = True, force: bool = False):
        # Use enhanced Genius service with ARI-style search matching
        if use_enhanced_search:
            self.genius_service = EnhancedGeniusService(genius_access_token)
            logger.info("Using enhanced Genius search with ARI-style matching")
        else:
            self.genius_service = GeniusService(genius_access_token)
            logger.info("Using standard Genius search")
        
        self.db_manager = get_database_manager()
        self.max_workers = max_workers
        self.force = force
        self._credit_cache = {}
        self._role_cache = {}
        self._lock = threading.Lock()
        
        # Initialize role mappings
        self.role_mappings = {
            'artist': 'Artist',
            'featured artist': 'Featured Artist',
            'writer': 'Writer',
            'producer': 'Producer',
            'co-writer': 'Co-Writer',
            'co-producer': 'Co-Producer',
            'arranger': 'Arranger',
            'engineer': 'Engineer',
            'mixer': 'Mixer',
            'mastering engineer': 'Mastering Engineer',
            'vocalist': 'Vocalist',
            'backing vocalist': 'Backing Vocalist',
            'instrumentalist': 'Instrumentalist'
        }
    
    def initialize_credit_roles(self):
        """Initialize credit roles in the database."""
        roles_data = [
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
            ('Instrumentalist', 'performance', 'Instrumental performer')
        ]
        
        with self.db_manager.get_session() as session:
            existing_roles = session.query(CreditRoles).count()
            if existing_roles > 0:
                logger.info(f"Credit roles already initialized ({existing_roles} roles)")
                return
            
            for role_name, category, description in roles_data:
                role = CreditRoles(
                    role_name=role_name,
                    role_category=category,
                    description=description
                )
                session.add(role)
            
            session.commit()
            logger.info(f"Initialized {len(roles_data)} credit roles")
    
    def _preload_caches(self):
        """Pre-load credit and role caches for faster lookups."""
        logger.info("Pre-loading caches...")
        
        with self.db_manager.get_session() as session:
            # Load all credits
            credits = session.query(Credits).all()
            for credit in credits:
                self._credit_cache[credit.normalized_name] = credit.credit_id
            
            # Load all roles
            roles = session.query(CreditRoles).all()
            for role in roles:
                self._role_cache[role.role_name] = role.role_id
        
        logger.info(f"Loaded {len(self._credit_cache)} credits and {len(self._role_cache)} roles into cache")
    
    def get_or_create_credit(self, credit_name: str, normalized_name: str, 
                           genius_id: int = None, session=None) -> int:
        """Get or create a credit and return its ID (with caching)."""
        # Check cache first
        if normalized_name in self._credit_cache:
            return self._credit_cache[normalized_name]
        
        # Check if credit exists by normalized name
        existing_credit = session.query(Credits).filter(
            Credits.normalized_name == normalized_name
        ).first()
        
        if existing_credit:
            self._credit_cache[normalized_name] = existing_credit.credit_id
            return existing_credit.credit_id
        
        # Create new credit
        credit = Credits(
            credit_name=credit_name,
            normalized_name=normalized_name,
            genius_id=genius_id
        )
        session.add(credit)
        session.flush()
        
        # Update cache
        self._credit_cache[normalized_name] = credit.credit_id
        return credit.credit_id
    
    def get_role_id(self, role_name: str, session) -> Optional[int]:
        """Get role ID by role name (with caching)."""
        if role_name in self._role_cache:
            return self._role_cache[role_name]
        
        role = session.query(CreditRoles).filter(CreditRoles.role_name == role_name).first()
        if role:
            self._role_cache[role_name] = role.role_id
            return role.role_id
        return None
    
    def normalize_credit_name(self, name: str) -> str:
        """Normalize credit name for matching."""
        # Remove common suffixes and normalize
        name = name.strip()
        
        # Remove "feat." and similar
        if ' feat.' in name.lower():
            name = name.split(' feat.')[0]
        
        # Remove "featuring" and similar
        if ' featuring' in name.lower():
            name = name.split(' featuring')[0]
        
        # Remove "&" and replace with "and"
        name = name.replace(' & ', ' and ')
        
        # Convert to lowercase for consistent matching
        return name.strip().lower()
    
    def enrich_song_metadata_data(self, song_data: Dict) -> Dict:
        """Enrich a single song with metadata from Genius API."""
        logger.info(f"Enriching: {song_data['song_name']} by {song_data['artist_name']}")
        
        # Get metadata from Genius API
        genius_metadata = self.genius_service.get_song_metadata(
            song_data['song_name'], song_data['artist_name']
        )
        
        return {
            'credits': genius_metadata.get('credits', []),
            'metadata': genius_metadata.get('metadata', {}),
            'genius_id': genius_metadata.get('genius_id'),
            'error': genius_metadata.get('error')
        }
    
    def _process_song_batch(self, songs_data: List[Dict]) -> Dict:
        """Process a batch of songs with optimized database operations."""
        results = {
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        # Collect all metadata first
        enriched_data = []
        for song_data in songs_data:
            try:
                metadata = self.enrich_song_metadata_data(song_data)
                if metadata.get('error'):
                    logger.warning(f"Failed to get metadata for {song_data['song_name']}: {metadata['error']}")
                    results['failed'] += 1
                    results['errors'].append(f"API error for {song_data['song_name']}: {metadata['error']}")
                    continue
                
                enriched_data.append((song_data, metadata))
                
            except Exception as e:
                logger.error(f"Error enriching {song_data['song_name']}: {e}")
                results['failed'] += 1
                results['errors'].append(f"Error enriching {song_data['song_name']}: {str(e)}")
        
        # Save metadata individually to avoid session poisoning
        if enriched_data:
            for song_data, metadata in enriched_data:
                try:
                    # Use a fresh session for each song to avoid cascade failures
                    with self.db_manager.get_session() as session:
                        if self._save_song_metadata_batch(song_data, metadata, session):
                            session.commit()
                            results['successful'] += 1
                            logger.debug(f"Successfully saved: {song_data['song_name']}")
                        else:
                            session.rollback()
                            results['failed'] += 1
                            results['errors'].append(f"Failed to save metadata for {song_data['song_name']}")
                except Exception as e:
                    logger.error(f"Error saving {song_data['song_name']}: {e}")
                    results['failed'] += 1
                    results['errors'].append(f"Save error for {song_data['song_name']}: {str(e)}")
        
        return results
    
    def _save_song_metadata_batch(self, song_data: Dict, metadata: Dict, session) -> bool:
        """Save metadata to database using batch operations."""
        try:
            credits_added = 0
            credits_skipped = 0
            
            # Pre-load existing credits for this song to avoid isolation issues
            existing_credits_set = set()
            existing_credits = session.query(SongCredits).filter(
                SongCredits.song_id == song_data['song_id']
            ).all()
            for sc in existing_credits:
                existing_credits_set.add((sc.credit_id, sc.role_id))
            
            # Save credits
            for credit_data in metadata['credits']:
                normalized_name = self.normalize_credit_name(credit_data['name'])
                credit_id = self.get_or_create_credit(
                    credit_data['name'],
                    normalized_name,
                    credit_data.get('id'),
                    session
                )
                
                # Determine role
                role_name = self.role_mappings.get(credit_data.get('role', '').lower(), 'Writer')
                role_id = self.get_role_id(role_name, session)
                
                if role_id:
                    # Check if song-credit relationship already exists (using pre-loaded set)
                    if (credit_id, role_id) not in existing_credits_set:
                        song_credit = SongCredits(
                            song_id=song_data['song_id'],
                            credit_id=credit_id,
                            role_id=role_id,
                            is_primary=credit_data.get('is_primary', False),
                            source=credit_data.get('source', 'genius')
                        )
                        session.add(song_credit)
                        credits_added += 1
                        # Add to set so we don't try to add it again in this batch
                        existing_credits_set.add((credit_id, role_id))
                    else:
                        credits_skipped += 1
            
            # Log credit statistics
            if credits_skipped > 0:
                logger.debug(f"{song_data['song_name']}: Added {credits_added} credits, skipped {credits_skipped} duplicates")
            elif credits_added > 0:
                logger.debug(f"{song_data['song_name']}: Added {credits_added} credits")
            
            # Save Genius metadata
            if metadata.get('genius_id') and metadata.get('metadata'):
                genius_meta = metadata['metadata']
                existing_meta = session.query(SongGeniusMetadata).filter(
                    SongGeniusMetadata.song_id == song_data['song_id']
                ).first()
                
                if not existing_meta:
                    description = genius_meta.get('description', '')
                    if isinstance(description, dict):
                        description = description.get('plain', '') or str(description)
                    elif not isinstance(description, str):
                        description = str(description)
                    
                    song_genius_meta = SongGeniusMetadata(
                        song_id=song_data['song_id'],
                        genius_id=metadata['genius_id'],
                        genius_url=genius_meta.get('url'),
                        release_date=genius_meta.get('release_date'),
                        lyrics_state=genius_meta.get('lyrics_state'),
                        pyongs_count=genius_meta.get('pyongs_count', 0),
                        hot=genius_meta.get('hot', False),
                        description=description
                    )
                    session.add(song_genius_meta)
                else:
                    # If force=True, update existing metadata with new data
                    if self.force:
                        description = genius_meta.get('description', '')
                        if isinstance(description, dict):
                            description = description.get('plain', '') or str(description)
                        elif not isinstance(description, str):
                            description = str(description)
                        
                        existing_meta.genius_id = metadata['genius_id']
                        existing_meta.genius_url = genius_meta.get('url')
                        existing_meta.release_date = genius_meta.get('release_date')
                        existing_meta.lyrics_state = genius_meta.get('lyrics_state')
                        existing_meta.pyongs_count = genius_meta.get('pyongs_count', 0)
                        existing_meta.hot = genius_meta.get('hot', False)
                        existing_meta.description = description
                        logger.debug(f"{song_data['song_name']}: Updating existing metadata with new Genius data")
                    else:
                        logger.debug(f"{song_data['song_name']}: Genius metadata already exists, skipping")
            
            # Flush to catch any constraint violations before commit
            session.flush()
            return True
                
        except Exception as e:
            logger.error(f"Failed to save metadata for {song_data['song_name']}: {e}")
            session.rollback()
            return False
    
    def enrich_songs_batch_data(self, songs_data: List[Dict], batch_size: int = 20, 
                               delay_between_batches: float = 0.2) -> Dict:
        """Enrich a batch of songs with optimized processing."""
        results = {
            'total': len(songs_data),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        # Pre-load caches
        self._preload_caches()
        
        # Pre-load existence data for all songs
        logger.info("Pre-loading existence data...")
        song_ids = [song['song_id'] for song in songs_data]
        
        with self.db_manager.get_session() as session:
            # Get all existing credits and metadata in one query
            existing_credits = set(session.query(SongCredits.song_id).filter(
                SongCredits.song_id.in_(song_ids)
            ).all())
            existing_credits = {row[0] for row in existing_credits}
            
            existing_metadata = set(session.query(SongGeniusMetadata.song_id).filter(
                SongGeniusMetadata.song_id.in_(song_ids)
            ).all())
            existing_metadata = {row[0] for row in existing_metadata}
        
        # Filter out songs that already have metadata (unless force=True)
        songs_to_process = []
        for song_data in songs_data:
            song_id = song_data['song_id']
            if not self.force and (song_id in existing_credits or song_id in existing_metadata):
                logger.info(f"Song {song_data['song_name']} already has metadata, skipping")
                results['successful'] += 1
            else:
                if self.force and (song_id in existing_credits or song_id in existing_metadata):
                    logger.info(f"Song {song_data['song_name']} will be re-enriched (force=True)")
                songs_to_process.append(song_data)
        
        logger.info(f"Processing {len(songs_to_process)} songs (skipped {len(songs_data) - len(songs_to_process)} already enriched)")
        
        # Process songs in batches
        for batch_start in range(0, len(songs_to_process), batch_size):
            batch_end = min(batch_start + batch_size, len(songs_to_process))
            batch_songs = songs_to_process[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_start//batch_size + 1}: songs {batch_start + 1}-{batch_end}")
            
            # Process batch
            batch_results = self._process_song_batch(batch_songs)
            
            # Update results
            results['successful'] += batch_results['successful']
            results['failed'] += batch_results['failed']
            results['errors'].extend(batch_results['errors'])
            
            # Add delay between batches
            if batch_end < len(songs_to_process):
                time.sleep(delay_between_batches)
        
        return results
    
    def enrich_songs_by_year(self, year: int, limit: int = 50) -> Dict:
        """Enrich songs from a specific year."""
        logger.info(f"Enriching songs from {year} (limit: {limit})")
        
        with self.db_manager.get_session() as session:
            from sqlalchemy import extract
            songs = session.query(Songs).filter(
                extract('year', Songs.first_chart_appearance) == year
            ).order_by(Songs.peak_position).limit(limit).all()
            
            # Convert to list of dictionaries to avoid session issues
            songs_data = []
            for song in songs:
                songs_data.append({
                    'song_id': song.song_id,
                    'song_name': song.song_name,
                    'artist_name': song.artist_name
                })
        
        return self.enrich_songs_batch_data(songs_data)


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='High-performance song enrichment with Genius API')
    parser.add_argument('--limit', type=int, default=100,
                       help='Number of songs to process (default: 100)')
    parser.add_argument('--year', type=int, default=None,
                       help='Process songs from specific year only')
    parser.add_argument('--genius-token', type=str, default=None,
                       help='Genius API access token')
    parser.add_argument('--init-roles', action='store_true',
                       help='Initialize credit roles only')
    parser.add_argument('--batch-size', type=int, default=20,
                       help='Batch size for processing (default: 20)')
    parser.add_argument('--delay', type=float, default=0.2,
                       help='Delay between batches in seconds (default: 0.2)')
    parser.add_argument('--enhanced-search', action='store_true', default=True,
                       help='Use enhanced Genius search with ARI-style matching (default: True)')
    parser.add_argument('--no-enhanced-search', action='store_false', dest='enhanced_search',
                       help='Disable enhanced search and use standard Genius search')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--force', action='store_true',
                       help='Force re-enrichment even if metadata exists (useful for fixing wrong Genius pages)')

    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get Genius token from environment if not provided
    genius_token = args.genius_token or os.getenv('GENIUS_ACCESS_TOKEN')
    if not genius_token and not args.init_roles:
        logger.error("Genius API access token is required. Set GENIUS_ACCESS_TOKEN environment variable or use --genius-token")
        sys.exit(1)
    
    # Initialize enricher with enhanced search option
    enricher = SongMetadataEnricher(genius_token, use_enhanced_search=args.enhanced_search, force=args.force)
    
    # Initialize credit roles if requested
    if args.init_roles:
        enricher.initialize_credit_roles()
        logger.info("Credit roles initialized")
        return
    
    # Process songs
    if args.year:
        results = enricher.enrich_songs_by_year(args.year, args.limit)
    else:
        logger.error("Year is required for optimized processing")
        sys.exit(1)
    
    # Print results
    print("\n" + "="*50)
    print("SONG METADATA ENRICHMENT RESULTS")
    print("="*50)
    print(f"Total songs processed: {results['total']}")
    print(f"Successfully enriched: {results['successful']}")
    print(f"Failed: {results['failed']}")
    
    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors'][:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(results['errors']) > 10:
            print(f"  ... and {len(results['errors']) - 10} more errors")
    
    print("="*50)


if __name__ == '__main__':
    main()

