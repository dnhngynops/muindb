#!/usr/bin/env python3
"""
Billboard data processing script.

This script processes yearly JSON data files and loads them into the database
using the new comprehensive schema.
"""

import sys
import os
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

from database.connection import get_database_manager, bulk_insert_weekly_charts
from database.models import Songs, Artists, WeeklyCharts, YearlyCharts, ChartWeeks, SongStats
from processors.data_cleaner import DataCleaner
from utils.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_yearly_json_files(data_dir: str = None) -> List[Dict[str, Any]]:
    """
    Load all yearly JSON files from the data directory.
    
    Args:
        data_dir: Directory containing yearly JSON files
        
    Returns:
        List of all chart entries from all years
    """
    if data_dir is None:
        data_dir = os.path.join(project_root, 'data', 'raw')
    
    all_entries = []
    processed_years = 0
    
    logger.info(f"Loading yearly JSON files from {data_dir}")
    
    # Find all billboard_*.json files
    json_files = [f for f in os.listdir(data_dir) if f.startswith('billboard_') and f.endswith('.json')]
    json_files.sort()  # Process in chronological order
    
    if not json_files:
        logger.error(f"No billboard JSON files found in {data_dir}")
        return []
    
    logger.info(f"Found {len(json_files)} yearly JSON files")
    
    for json_file in json_files:
        file_path = os.path.join(data_dir, json_file)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                year_data = json.load(f)
            
            # Extract all entries from all weeks in this year
            year_entries = []
            for week_date, week_data in year_data.get('weeks', {}).items():
                year_entries.extend(week_data.get('entries', []))
            
            all_entries.extend(year_entries)
            processed_years += 1
            
            logger.info(f"✓ {json_file}: {len(year_entries)} entries")
            
        except Exception as e:
            logger.error(f"Error loading {json_file}: {e}")
            continue
    
    logger.info(f"Loaded {len(all_entries)} total entries from {processed_years} years")
    return all_entries


def create_songs_catalog(entries: List[Dict[str, Any]]) -> Dict[Tuple[str, str], int]:
    """
    Create the songs catalog and return song_id mapping.
    
    Args:
        entries: List of all chart entries
        
    Returns:
        Dictionary mapping (song_name, artist_name) to song_id
    """
    logger.info("Creating songs catalog...")
    
    # Get unique song/artist combinations
    unique_songs = set()
    for entry in entries:
        song_key = (entry['song_name'], entry['artist_name'])
        unique_songs.add(song_key)
    
    logger.info(f"Found {len(unique_songs)} unique songs")
    
    # Create Songs records
    manager = get_database_manager()
    song_id_mapping = {}
    
    with manager.get_session() as session:
        for i, (song_name, artist_name) in enumerate(unique_songs):
            # Calculate lifetime statistics for this song
            song_entries = [e for e in entries if e['song_name'] == song_name and e['artist_name'] == artist_name]
            
            if not song_entries:
                continue
            
            # Calculate statistics
            first_appearance = min(e['chart_date'] for e in song_entries)
            last_appearance = max(e['chart_date'] for e in song_entries)
            peak_position = min(e['peak_position'] for e in song_entries)
            total_weeks = max(e['weeks_on_chart'] for e in song_entries)
            
            # Count weeks at different positions
            weeks_at_number_one = sum(1 for e in song_entries if e['current_position'] == 1)
            weeks_in_top_10 = sum(1 for e in song_entries if e['current_position'] <= 10)
            weeks_in_top_40 = sum(1 for e in song_entries if e['current_position'] <= 40)
            
            # Create Songs record
            song = Songs(
                song_name=song_name,
                artist_name=artist_name,
                first_chart_appearance=first_appearance,
                last_chart_appearance=last_appearance,
                total_weeks_on_chart=total_weeks,
                peak_position=peak_position,
                weeks_at_number_one=weeks_at_number_one,
                weeks_in_top_10=weeks_in_top_10,
                weeks_in_top_40=weeks_in_top_40
            )
            
            session.add(song)
            session.flush()  # Get the song_id
            
            song_id_mapping[(song_name, artist_name)] = song.song_id
            
            if (i + 1) % 1000 == 0:
                logger.info(f"Processed {i + 1} songs...")
        
        session.commit()
        logger.info(f"Created {len(song_id_mapping)} songs in database")
    
    return song_id_mapping


def create_artists_catalog(entries: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Create the artists catalog and return artist_id mapping.
    
    Args:
        entries: List of all chart entries
        
    Returns:
        Dictionary mapping artist_name to artist_id
    """
    logger.info("Creating artists catalog...")
    
    # Get unique artists
    unique_artists = set()
    for entry in entries:
        unique_artists.add(entry['artist_name'])
    
    logger.info(f"Found {len(unique_artists)} unique artists")
    
    # Create Artists records
    manager = get_database_manager()
    artist_id_mapping = {}
    
    with manager.get_session() as session:
        for i, artist_name in enumerate(unique_artists):
            # Calculate career statistics for this artist
            artist_entries = [e for e in entries if e['artist_name'] == artist_name]
            
            if not artist_entries:
                continue
            
            # Calculate statistics
            first_appearance = min(e['chart_date'] for e in artist_entries)
            last_appearance = max(e['chart_date'] for e in artist_entries)
            total_songs = len(set(e['song_name'] for e in artist_entries))
            total_weeks = len(artist_entries)
            
            # Count hits
            number_one_hits = len(set(e['song_name'] for e in artist_entries if e['current_position'] == 1))
            top_10_hits = len(set(e['song_name'] for e in artist_entries if e['current_position'] <= 10))
            top_40_hits = len(set(e['song_name'] for e in artist_entries if e['current_position'] <= 40))
            
            peak_position = min(e['current_position'] for e in artist_entries)
            
            # Create Artists record
            artist = Artists(
                artist_name=artist_name,
                first_chart_appearance=first_appearance,
                last_chart_appearance=last_appearance,
                total_songs=total_songs,
                total_weeks_on_chart=total_weeks,
                number_one_hits=number_one_hits,
                top_10_hits=top_10_hits,
                top_40_hits=top_40_hits,
                peak_position=peak_position
            )
            
            session.add(artist)
            session.flush()  # Get the artist_id
            
            artist_id_mapping[artist_name] = artist.artist_id
            
            if (i + 1) % 1000 == 0:
                logger.info(f"Processed {i + 1} artists...")
        
        session.commit()
        logger.info(f"Created {len(artist_id_mapping)} artists in database")
    
    return artist_id_mapping


def create_weekly_charts(entries: List[Dict[str, Any]], song_id_mapping: Dict[Tuple[str, str], int]):
    """
    Create weekly charts entries.
    
    Args:
        entries: List of all chart entries
        song_id_mapping: Dictionary mapping (song_name, artist_name) to song_id
    """
    logger.info("Creating weekly charts entries...")
    
    manager = get_database_manager()
    
    with manager.get_session() as session:
        for i, entry in enumerate(entries):
            song_key = (entry['song_name'], entry['artist_name'])
            song_id = song_id_mapping.get(song_key)
            
            if not song_id:
                logger.warning(f"Song not found in catalog: {song_key}")
                continue
            
            # Calculate position change
            position_change = None
            if entry.get('last_week_position') is not None:
                position_change = entry['current_position'] - entry['last_week_position']
            
            # Determine if it's a new entry
            is_new_entry = entry.get('last_week_position') is None
            
            # Create WeeklyCharts record
            weekly_chart = WeeklyCharts(
                song_id=song_id,
                chart_date=entry['chart_date'],
                year=entry['year'],
                week_number=None,  # Could be calculated if needed
                current_position=entry['current_position'],
                last_week_position=entry.get('last_week_position'),
                peak_position=entry['peak_position'],
                weeks_on_chart=entry['weeks_on_chart'],
                position_change=position_change,
                is_new_entry=is_new_entry
            )
            
            session.add(weekly_chart)
            
            if (i + 1) % 10000 == 0:
                logger.info(f"Processed {i + 1} weekly entries...")
        
        session.commit()
        logger.info(f"Created {len(entries)} weekly chart entries")


def create_yearly_charts(entries: List[Dict[str, Any]]):
    """
    Create yearly charts summaries.
    
    Args:
        entries: List of all chart entries
    """
    logger.info("Creating yearly charts summaries...")
    
    # Group entries by year
    yearly_data = defaultdict(list)
    for entry in entries:
        yearly_data[entry['year']].append(entry)
    
    manager = get_database_manager()
    
    with manager.get_session() as session:
        for year, year_entries in yearly_data.items():
            # Calculate yearly statistics
            unique_songs = len(set((e['song_name'], e['artist_name']) for e in year_entries))
            total_entries = len(year_entries)
            
            # Count number one songs
            number_one_songs = len(set(e['song_name'] for e in year_entries if e['current_position'] == 1))
            
            # Find longest staying song
            song_weeks = defaultdict(int)
            for entry in year_entries:
                song_key = (entry['song_name'], entry['artist_name'])
                song_weeks[song_key] = max(song_weeks[song_key], entry['weeks_on_chart'])
            
            if song_weeks:
                longest_song_key, longest_weeks = max(song_weeks.items(), key=lambda x: x[1])
                longest_song_name = longest_song_key[0]
            else:
                longest_song_name = None
                longest_weeks = 0
            
            # Count weeks at number one
            weeks_at_number_one = sum(1 for e in year_entries if e['current_position'] == 1)
            
            # Create YearlyCharts record
            yearly_chart = YearlyCharts(
                year=year,
                total_weeks=len(set(e['chart_date'] for e in year_entries)),
                total_unique_songs=unique_songs,
                total_entries=total_entries,
                number_one_songs=number_one_songs,
                most_weeks_at_number_one=weeks_at_number_one,
                longest_staying_song=longest_song_name,
                longest_staying_weeks=longest_weeks
            )
            
            session.add(yearly_chart)
            logger.info(f"Created yearly chart for {year}: {unique_songs} songs, {total_entries} entries")
        
        session.commit()
        logger.info(f"Created {len(yearly_data)} yearly chart summaries")


def process_data(data_dir: str = None, clean_data: bool = True, batch_size: int = 1000):
    """
    Process Billboard JSON data and load it into the database.
    
    Args:
        data_dir: Directory containing yearly JSON files
        clean_data: Whether to clean and normalize data
        batch_size: Batch size for database insertion
    """
    try:
        # Get configuration
        config = get_config()
        config.ensure_directories()
        
        if data_dir is None:
            data_dir = os.path.join(project_root, 'data', 'raw')
        
        if not os.path.exists(data_dir):
            logger.error(f"Data directory not found: {data_dir}")
            return False
        
        # Initialize processors
        data_cleaner = DataCleaner()
        db_manager = get_database_manager()
        
        # Test database connection
        if not db_manager.test_connection():
            logger.error("Database connection failed")
            return False
        
        # Load all yearly JSON files
        logger.info("Loading yearly JSON files...")
        all_entries = load_yearly_json_files(data_dir)
        
        if not all_entries:
            logger.error("No entries were loaded from JSON files")
            return False
        
        logger.info(f"Loaded {len(all_entries)} entries from yearly JSON files")
        
        # Clean data if requested
        if clean_data:
            logger.info("Cleaning and normalizing data...")
            cleaned_entries = data_cleaner.clean_billboard_entries(all_entries)
            if not cleaned_entries:
                logger.error("No entries remained after cleaning")
                return False
            
            logger.info(f"Cleaned data: {len(cleaned_entries)} entries")
            
            # Generate quality report
            quality_report = data_cleaner.generate_quality_report(cleaned_entries)
            logger.info("Data Quality Report:")
            logger.info(f"  Total entries: {quality_report['total_entries']:,}")
            logger.info(f"  Unique artists: {quality_report['artists_count']:,}")
            logger.info(f"  Unique songs: {quality_report['songs_count']:,}")
            logger.info(f"  New entries: {quality_report['new_entries']:,}")
            logger.info(f"  Missing last week data: {quality_report['missing_last_week']:,}")
            logger.info(f"  Potential duplicates: {quality_report['duplicates']}")
            
            entries_to_process = cleaned_entries
        else:
            entries_to_process = all_entries
        
        # Process data into database
        logger.info("Processing data into database...")
        
        # Step 1: Create songs catalog
        song_id_mapping = create_songs_catalog(entries_to_process)
        
        # Step 2: Create artists catalog
        artist_id_mapping = create_artists_catalog(entries_to_process)
        
        # Step 3: Create weekly charts
        create_weekly_charts(entries_to_process, song_id_mapping)
        
        # Step 4: Create yearly charts
        create_yearly_charts(entries_to_process)
        
        # Show final database info
        db_info = db_manager.get_database_info()
        logger.info("Database updated successfully!")
        logger.info(f"Total songs: {db_info['songs']:,}")
        logger.info(f"Total artists: {db_info['artists']:,}")
        logger.info(f"Total weekly entries: {db_info['weekly_charts']:,}")
        logger.info(f"Total yearly summaries: {db_info['yearly_charts']:,}")
        
        return True
        
    except Exception as e:
        logger.error(f"Data processing failed: {e}")
        return False


def clear_database():
    """Clear all data from the database."""
    try:
        logger.warning("This will delete all data from the database!")
        response = input("Are you sure you want to clear the database? (yes/no): ")
        
        if response.lower() != 'yes':
            logger.info("Database clear cancelled")
            return False
        
        db_manager = get_database_manager()
        
        # Clear all tables
        with db_manager.get_session() as session:
            session.execute("DELETE FROM weekly_charts")
            session.execute("DELETE FROM yearly_charts")
            session.execute("DELETE FROM chart_weeks")
            session.execute("DELETE FROM song_stats")
            session.execute("DELETE FROM songs")
            session.execute("DELETE FROM artists")
        
        logger.info("Database cleared successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database clear failed: {e}")
        return False


def show_processing_stats():
    """Show processing statistics."""
    try:
        db_manager = get_database_manager()
        info = db_manager.get_database_info()
        
        print("\n" + "="*50)
        print("BILLBOARD DATA PROCESSING STATS")
        print("="*50)
        print(f"Total Songs: {info['songs']:,}")
        print(f"Total Artists: {info['artists']:,}")
        print(f"Total Weekly Entries: {info['weekly_charts']:,}")
        print(f"Total Yearly Summaries: {info['yearly_charts']:,}")
        print(f"Total Chart Weeks: {info['chart_weeks']:,}")
        print(f"Total Song Stats: {info['song_stats']:,}")
        
        if info['date_range']['earliest']:
            print(f"Date Range: {info['date_range']['earliest']} to {info['date_range']['latest']}")
        else:
            print("Date Range: No data")
        
        print("="*50)
        
    except Exception as e:
        logger.error(f"Failed to get processing stats: {e}")


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='Process Billboard Hot 100 Data')
    parser.add_argument('--data-dir', type=str, default=None,
                       help='Directory containing yearly JSON files (default: data/raw)')
    parser.add_argument('--no-clean', action='store_true',
                       help='Skip data cleaning and normalization')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for database insertion (default: 1000)')
    parser.add_argument('--clear', action='store_true',
                       help='Clear all data from the database')
    parser.add_argument('--stats', action='store_true',
                       help='Show processing statistics')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.clear:
        success = clear_database()
    elif args.stats:
        show_processing_stats()
        success = True
    else:
        clean_data = not args.no_clean
        success = process_data(args.data_dir, clean_data, args.batch_size)
    
    if success:
        logger.info("Operation completed successfully")
        sys.exit(0)
    else:
        logger.error("Operation failed")
        sys.exit(1)


if __name__ == '__main__':
    main()