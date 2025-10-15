"""
Database connection and operations module.

This module handles database connections, session management, and common database operations.
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator, Optional, List, Dict, Any
from datetime import date, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    Base, Songs, Artists, WeeklyCharts, YearlyCharts, 
    ChartWeeks, SongStats, ChartPositions, ArtistCollaborations
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, database_path: str = None):
        """
        Initialize the database manager.
        
        Args:
            database_path: Path to the SQLite database file. If None, uses default path.
        """
        if database_path is None:
            # Default to data/music_database.db in the project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            database_path = os.path.join(project_root, 'data', 'music_database.db')
        
        self.database_path = database_path
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the SQLAlchemy engine and session factory."""
        try:
            # Ensure the data directory exists
            os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
            
            # Create engine with SQLite-specific configurations
            self.engine = create_engine(
                f"sqlite:///{self.database_path}",
                echo=False,  # Set to True for SQL query logging
                pool_pre_ping=True,
                connect_args={
                    "check_same_thread": False,  # Allow multi-threading
                    "timeout": 30  # 30 second timeout
                }
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info(f"Database engine initialized: {self.database_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables. Use with caution!"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        
        Yields:
            SQLAlchemy session object
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """
        Get a database session directly (without context manager).
        
        Returns:
            SQLAlchemy session object
            
        Note:
            Remember to close the session when done!
        """
        return self.SessionLocal()
    
    def test_connection(self) -> bool:
        """
        Test the database connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get information about the database.
        
        Returns:
            Dictionary containing database information
        """
        try:
            with self.get_session() as session:
                # Get table counts
                songs_count = session.query(Songs).count()
                artists_count = session.query(Artists).count()
                weekly_charts_count = session.query(WeeklyCharts).count()
                yearly_charts_count = session.query(YearlyCharts).count()
                chart_weeks_count = session.query(ChartWeeks).count()
                song_stats_count = session.query(SongStats).count()
                
                # Get date range
                min_date_result = session.query(WeeklyCharts.chart_date).order_by(WeeklyCharts.chart_date.asc()).first()
                max_date_result = session.query(WeeklyCharts.chart_date).order_by(WeeklyCharts.chart_date.desc()).first()
                
                min_date = min_date_result[0] if min_date_result else None
                max_date = max_date_result[0] if max_date_result else None
                
                return {
                    "database_path": self.database_path,
                    "songs": songs_count,
                    "artists": artists_count,
                    "weekly_charts": weekly_charts_count,
                    "yearly_charts": yearly_charts_count,
                    "chart_weeks": chart_weeks_count,
                    "song_stats": song_stats_count,
                    "date_range": {
                        "earliest": min_date.isoformat() if min_date else None,
                        "latest": max_date.isoformat() if max_date else None
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}


# Global database manager instance
db_manager = DatabaseManager()


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    return db_manager


def reset_database_manager(database_path: str = None):
    """Reset the global database manager with a new path."""
    global db_manager
    db_manager = DatabaseManager(database_path)


# Convenience functions for common operations
def bulk_insert_weekly_charts(entries: List[Dict[str, Any]], batch_size: int = 1000):
    """
    Bulk insert weekly chart entries for better performance.
    
    Args:
        entries: List of dictionaries containing entry data
        batch_size: Number of entries to insert per batch
    """
    manager = get_database_manager()
    
    try:
        with manager.get_session() as session:
            for i in range(0, len(entries), batch_size):
                batch = entries[i:i + batch_size]
                weekly_objects = []
                
                for entry_data in batch:
                    # Calculate position change
                    position_change = None
                    if entry_data.get('last_week_position') is not None:
                        position_change = entry_data['current_position'] - entry_data['last_week_position']
                    
                    # Determine if it's a new entry
                    is_new_entry = entry_data.get('last_week_position') is None
                    
                    weekly_obj = WeeklyCharts(
                        song_id=entry_data['song_id'],  # This will need to be resolved
                        chart_date=entry_data['chart_date'],
                        year=entry_data['year'],
                        week_number=entry_data.get('week_number'),
                        current_position=entry_data['current_position'],
                        last_week_position=entry_data.get('last_week_position'),
                        peak_position=entry_data['peak_position'],
                        weeks_on_chart=entry_data['weeks_on_chart'],
                        position_change=position_change,
                        is_new_entry=is_new_entry
                    )
                    weekly_objects.append(weekly_obj)
                
                session.bulk_save_objects(weekly_objects)
                logger.info(f"Inserted batch {i//batch_size + 1}: {len(weekly_objects)} entries")
            
            logger.info(f"Successfully inserted {len(entries)} weekly chart entries")
            
    except Exception as e:
        logger.error(f"Failed to bulk insert weekly chart entries: {e}")
        raise


def get_chart_entries_by_date(chart_date: date) -> List[WeeklyCharts]:
    """
    Get all chart entries for a specific date.
    
    Args:
        chart_date: The chart date to query
        
    Returns:
        List of WeeklyCharts objects
    """
    manager = get_database_manager()
    
    try:
        with manager.get_session() as session:
            entries = session.query(WeeklyCharts).filter(
                WeeklyCharts.chart_date == chart_date
            ).order_by(WeeklyCharts.current_position).all()
            
            return entries
    except Exception as e:
        logger.error(f"Failed to get chart entries for date {chart_date}: {e}")
        raise


def get_songs_by_artist(artist_name: str, limit: int = 100) -> List[Songs]:
    """
    Get songs by a specific artist.
    
    Args:
        artist_name: Name of the artist
        limit: Maximum number of songs to return
        
    Returns:
        List of Songs objects
    """
    manager = get_database_manager()
    
    try:
        with manager.get_session() as session:
            songs = session.query(Songs).filter(
                Songs.artist_name.ilike(f"%{artist_name}%")
            ).order_by(Songs.peak_position.asc()).limit(limit).all()
            
            return songs
    except Exception as e:
        logger.error(f"Failed to get songs for artist {artist_name}: {e}")
        raise


def get_top_songs_by_year(year: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get top songs by peak position for a specific year.
    
    Args:
        year: Year to query
        limit: Maximum number of songs to return
        
    Returns:
        List of dictionaries with song information
    """
    manager = get_database_manager()
    
    try:
        with manager.get_session() as session:
            # Query songs that appeared in the specified year
            query = session.query(Songs).join(WeeklyCharts).filter(
                WeeklyCharts.year == year
            ).order_by(Songs.peak_position.asc()).limit(limit)
            
            results = []
            for song in query:
                results.append({
                    'song_name': song.song_name,
                    'artist_name': song.artist_name,
                    'peak_position': song.peak_position,
                    'total_weeks': song.total_weeks_on_chart,
                    'weeks_at_number_one': song.weeks_at_number_one
                })
            
            return results
    except Exception as e:
        logger.error(f"Failed to get top songs for year {year}: {e}")
        raise


def get_yearly_statistics(year: int) -> Dict[str, Any]:
    """
    Get statistics for a specific year.
    
    Args:
        year: Year to get statistics for
        
    Returns:
        Dictionary containing yearly statistics
    """
    manager = get_database_manager()
    
    try:
        with manager.get_session() as session:
            # Get yearly chart record
            yearly_chart = session.query(YearlyCharts).filter(
                YearlyCharts.year == year
            ).first()
            
            if yearly_chart:
                return {
                    'year': yearly_chart.year,
                    'total_weeks': yearly_chart.total_weeks,
                    'total_unique_songs': yearly_chart.total_unique_songs,
                    'total_entries': yearly_chart.total_entries,
                    'number_one_songs': yearly_chart.number_one_songs,
                    'longest_staying_song': yearly_chart.longest_staying_song,
                    'longest_staying_weeks': yearly_chart.longest_staying_weeks
                }
            else:
                return {'error': f'No data found for year {year}'}
                
    except Exception as e:
        logger.error(f"Failed to get statistics for year {year}: {e}")
        raise