#!/usr/bin/env python3
"""
Populate missing tables in the Billboard database.

This script populates the additional tables that weren't filled during initial processing:
- chart_weeks: Weekly chart metadata
- song_stats: Pre-calculated song statistics
- chart_positions: Position history tracking
- artist_collaborations: Artist collaboration tracking
"""

import sys
import os
import logging
import argparse
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
from decimal import Decimal

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

from database.connection import get_database_manager
from database.models import (
    Songs, Artists, WeeklyCharts, YearlyCharts, 
    ChartWeeks, SongStats, ChartPositions, ArtistCollaborations
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def populate_chart_weeks():
    """Populate the chart_weeks table with weekly chart metadata."""
    logger.info("Populating chart_weeks table...")
    
    manager = get_database_manager()
    
    with manager.get_session() as session:
        # Get all unique chart dates from weekly_charts
        chart_dates = session.query(WeeklyCharts.chart_date).distinct().order_by(WeeklyCharts.chart_date).all()
        
        logger.info(f"Found {len(chart_dates)} unique chart dates")
        
        for i, (chart_date,) in enumerate(chart_dates):
            # Get data for this chart date
            week_entries = session.query(WeeklyCharts).filter(
                WeeklyCharts.chart_date == chart_date
            ).all()
            
            if not week_entries:
                continue
            
            # Calculate week statistics
            total_entries = len(week_entries)
            new_entries = sum(1 for entry in week_entries if entry.is_new_entry)
            re_entries = total_entries - new_entries
            
            # Find number one song and artist
            number_one_entry = next((entry for entry in week_entries if entry.current_position == 1), None)
            number_one_song = number_one_entry.song.song_name if number_one_entry else None
            number_one_artist = number_one_entry.song.artist_name if number_one_entry else None
            
            # Calculate week number (approximate)
            year = chart_date.year
            week_number = chart_date.isocalendar()[1]  # ISO week number
            
            # Create ChartWeeks record
            chart_week = ChartWeeks(
                chart_date=chart_date,
                year=year,
                week_number=week_number,
                total_entries=total_entries,
                new_entries=new_entries,
                re_entries=re_entries,
                number_one_song=number_one_song,
                number_one_artist=number_one_artist
            )
            
            session.add(chart_week)
            
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1} chart weeks...")
        
        session.commit()
        logger.info(f"Created {len(chart_dates)} chart weeks records")


def populate_song_stats():
    """Populate the song_stats table with pre-calculated statistics."""
    logger.info("Populating song_stats table...")
    
    manager = get_database_manager()
    
    with manager.get_session() as session:
        # Get all songs
        songs = session.query(Songs).all()
        
        logger.info(f"Processing {len(songs)} songs for statistics")
        
        for i, song in enumerate(songs):
            # Get all weekly entries for this song
            weekly_entries = session.query(WeeklyCharts).filter(
                WeeklyCharts.song_id == song.song_id
            ).all()
            
            if not weekly_entries:
                continue
            
            # Calculate lifetime statistics
            positions = [entry.current_position for entry in weekly_entries]
            total_weeks = len(weekly_entries)
            peak_position = min(positions)
            weeks_at_number_one = sum(1 for pos in positions if pos == 1)
            weeks_in_top_10 = sum(1 for pos in positions if pos <= 10)
            weeks_in_top_40 = sum(1 for pos in positions if pos <= 40)
            average_position = sum(positions) / len(positions)
            
            # Create lifetime SongStats record
            song_stat = SongStats(
                song_id=song.song_id,
                year=None,  # Lifetime stats
                total_weeks=total_weeks,
                peak_position=peak_position,
                weeks_at_number_one=weeks_at_number_one,
                weeks_in_top_10=weeks_in_top_10,
                weeks_in_top_40=weeks_in_top_40,
                average_position=Decimal(str(round(average_position, 2)))
            )
            
            session.add(song_stat)
            
            # Also create yearly statistics
            yearly_entries = defaultdict(list)
            for entry in weekly_entries:
                yearly_entries[entry.year].append(entry)
            
            for year, year_entries in yearly_entries.items():
                year_positions = [entry.current_position for entry in year_entries]
                year_total_weeks = len(year_entries)
                year_peak_position = min(year_positions)
                year_weeks_at_number_one = sum(1 for pos in year_positions if pos == 1)
                year_weeks_in_top_10 = sum(1 for pos in year_positions if pos <= 10)
                year_weeks_in_top_40 = sum(1 for pos in year_positions if pos <= 40)
                year_average_position = sum(year_positions) / len(year_positions)
                
                year_song_stat = SongStats(
                    song_id=song.song_id,
                    year=year,
                    total_weeks=year_total_weeks,
                    peak_position=year_peak_position,
                    weeks_at_number_one=year_weeks_at_number_one,
                    weeks_in_top_10=year_weeks_in_top_10,
                    weeks_in_top_40=year_weeks_in_top_40,
                    average_position=Decimal(str(round(year_average_position, 2)))
                )
                
                session.add(year_song_stat)
            
            if (i + 1) % 1000 == 0:
                logger.info(f"Processed {i + 1} songs...")
        
        session.commit()
        logger.info("Created song statistics records")


def populate_chart_positions():
    """Populate the chart_positions table with position history."""
    logger.info("Populating chart_positions table...")
    
    manager = get_database_manager()
    
    with manager.get_session() as session:
        # Get all weekly chart entries
        weekly_entries = session.query(WeeklyCharts).order_by(
            WeeklyCharts.song_id, WeeklyCharts.chart_date
        ).all()
        
        logger.info(f"Processing {len(weekly_entries)} weekly entries for position history")
        
        for i, entry in enumerate(weekly_entries):
            # Calculate position change
            position_change = None
            if entry.last_week_position is not None:
                position_change = entry.current_position - entry.last_week_position
            
            # Create ChartPositions record
            chart_position = ChartPositions(
                song_id=entry.song_id,
                chart_date=entry.chart_date,
                position=entry.current_position,
                position_change=position_change,
                weeks_on_chart=entry.weeks_on_chart
            )
            
            session.add(chart_position)
            
            if (i + 1) % 10000 == 0:
                logger.info(f"Processed {i + 1} position records...")
        
        session.commit()
        logger.info(f"Created {len(weekly_entries)} chart position records")


def populate_artist_collaborations():
    """Populate the artist_collaborations table with collaboration data."""
    logger.info("Populating artist_collaborations table...")
    
    manager = get_database_manager()
    
    with manager.get_session() as session:
        # Get all songs
        songs = session.query(Songs).all()
        
        logger.info(f"Processing {len(songs)} songs for collaborations")
        
        for i, song in enumerate(songs):
            # Parse artist name for collaborations
            artist_name = song.artist_name
            
            # Common collaboration patterns
            if ' feat. ' in artist_name.lower():
                artists = artist_name.split(' feat. ')
                primary_artist = artists[0].strip()
                featured_artist = artists[1].strip()
                
                # Add primary artist
                collab1 = ArtistCollaborations(
                    song_id=song.song_id,
                    artist_name=primary_artist,
                    is_primary_artist=True,
                    is_featured_artist=False
                )
                session.add(collab1)
                
                # Add featured artist
                collab2 = ArtistCollaborations(
                    song_id=song.song_id,
                    artist_name=featured_artist,
                    is_primary_artist=False,
                    is_featured_artist=True
                )
                session.add(collab2)
                
            elif ' featuring ' in artist_name.lower():
                artists = artist_name.split(' featuring ')
                primary_artist = artists[0].strip()
                featured_artist = artists[1].strip()
                
                # Add primary artist
                collab1 = ArtistCollaborations(
                    song_id=song.song_id,
                    artist_name=primary_artist,
                    is_primary_artist=True,
                    is_featured_artist=False
                )
                session.add(collab1)
                
                # Add featured artist
                collab2 = ArtistCollaborations(
                    song_id=song.song_id,
                    artist_name=featured_artist,
                    is_primary_artist=False,
                    is_featured_artist=True
                )
                session.add(collab2)
                
            elif ' & ' in artist_name:
                artists = artist_name.split(' & ')
                for j, artist in enumerate(artists):
                    collab = ArtistCollaborations(
                        song_id=song.song_id,
                        artist_name=artist.strip(),
                        is_primary_artist=(j == 0),
                        is_featured_artist=(j > 0)
                    )
                    session.add(collab)
            
            else:
                # Single artist
                collab = ArtistCollaborations(
                    song_id=song.song_id,
                    artist_name=artist_name,
                    is_primary_artist=True,
                    is_featured_artist=False
                )
                session.add(collab)
            
            if (i + 1) % 1000 == 0:
                logger.info(f"Processed {i + 1} songs...")
        
        session.commit()
        logger.info("Created artist collaboration records")


def show_table_counts():
    """Show the current count of records in each table."""
    manager = get_database_manager()
    
    with manager.get_session() as session:
        tables = [
            ('songs', Songs),
            ('artists', Artists),
            ('weekly_charts', WeeklyCharts),
            ('yearly_charts', YearlyCharts),
            ('chart_weeks', ChartWeeks),
            ('song_stats', SongStats),
            ('chart_positions', ChartPositions),
            ('artist_collaborations', ArtistCollaborations)
        ]
        
        print("\n" + "="*50)
        print("CURRENT TABLE COUNTS")
        print("="*50)
        
        for table_name, model in tables:
            count = session.query(model).count()
            print(f"{table_name:20}: {count:>8,}")
        
        print("="*50)


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='Populate missing tables in Billboard database')
    parser.add_argument('--chart-weeks', action='store_true', help='Populate chart_weeks table')
    parser.add_argument('--song-stats', action='store_true', help='Populate song_stats table')
    parser.add_argument('--chart-positions', action='store_true', help='Populate chart_positions table')
    parser.add_argument('--artist-collaborations', action='store_true', help='Populate artist_collaborations table')
    parser.add_argument('--all', action='store_true', help='Populate all missing tables')
    parser.add_argument('--show-counts', action='store_true', help='Show current table counts')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.show_counts:
        show_table_counts()
        return
    
    if args.all or not any([args.chart_weeks, args.song_stats, args.chart_positions, args.artist_collaborations]):
        # Populate all tables by default
        logger.info("Populating all missing tables...")
        populate_chart_weeks()
        populate_song_stats()
        populate_chart_positions()
        populate_artist_collaborations()
    else:
        # Populate specific tables
        if args.chart_weeks:
            populate_chart_weeks()
        if args.song_stats:
            populate_song_stats()
        if args.chart_positions:
            populate_chart_positions()
        if args.artist_collaborations:
            populate_artist_collaborations()
    
    # Show final counts
    show_table_counts()
    logger.info("Table population completed successfully!")


if __name__ == '__main__':
    main()
