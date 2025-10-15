"""
Database models for Billboard Hot 100 data.

This module defines the SQLAlchemy models for storing Billboard Hot 100 chart data
with a comprehensive schema optimized for analysis and queries.
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.types import DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Songs(Base):
    """
    Master song catalog - deduplicated songs with lifetime statistics.
    
    This table contains unique song/artist combinations with aggregated
    statistics across all chart appearances.
    """
    __tablename__ = 'songs'
    
    # Primary key
    song_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Song identification
    song_name = Column(String(255), nullable=False, index=True)
    artist_name = Column(String(255), nullable=False, index=True)
    
    # Lifetime statistics
    first_chart_appearance = Column(Date, nullable=True, index=True)
    last_chart_appearance = Column(Date, nullable=True, index=True)
    total_weeks_on_chart = Column(Integer, nullable=False, default=0)
    peak_position = Column(Integer, nullable=False, index=True)
    
    # Performance metrics
    weeks_at_number_one = Column(Integer, nullable=False, default=0)
    weeks_in_top_10 = Column(Integer, nullable=False, default=0)
    weeks_in_top_40 = Column(Integer, nullable=False, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    weekly_entries = relationship("WeeklyCharts", back_populates="song")
    song_stats = relationship("SongStats", back_populates="song")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_song_artist_unique', 'song_name', 'artist_name', unique=True),
        Index('idx_song_peak_position', 'peak_position'),
        Index('idx_song_weeks_on_chart', 'total_weeks_on_chart'),
    )
    
    def __repr__(self):
        return f"<Songs(song='{self.song_name}', artist='{self.artist_name}', peak={self.peak_position})>"


class Artists(Base):
    """
    Master artist catalog - deduplicated artists with career statistics.
    
    This table contains unique artists with aggregated statistics
    across all their chart appearances.
    """
    __tablename__ = 'artists'
    
    # Primary key
    artist_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Artist identification
    artist_name = Column(String(255), nullable=False, unique=True, index=True)
    
    # Career statistics
    first_chart_appearance = Column(Date, nullable=True, index=True)
    last_chart_appearance = Column(Date, nullable=True, index=True)
    total_songs = Column(Integer, nullable=False, default=0)
    total_weeks_on_chart = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    number_one_hits = Column(Integer, nullable=False, default=0)
    top_10_hits = Column(Integer, nullable=False, default=0)
    top_40_hits = Column(Integer, nullable=False, default=0)
    peak_position = Column(Integer, nullable=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Artists(artist='{self.artist_name}', songs={self.total_songs}, weeks={self.total_weeks_on_chart})>"


class WeeklyCharts(Base):
    """
    All weekly chart entries - complete historical record.
    
    This table contains every chart entry from every week,
    linked to the Songs table for deduplication.
    """
    __tablename__ = 'weekly_charts'
    
    # Primary key
    entry_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to Songs table
    song_id = Column(Integer, ForeignKey('songs.song_id'), nullable=False, index=True)
    
    # Chart data
    chart_date = Column(Date, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    week_number = Column(Integer, nullable=True)
    
    # Position data
    current_position = Column(Integer, nullable=False, index=True)
    last_week_position = Column(Integer, nullable=True)
    peak_position = Column(Integer, nullable=False)
    weeks_on_chart = Column(Integer, nullable=False)
    
    # Calculated fields
    position_change = Column(Integer, nullable=True)
    is_new_entry = Column(Boolean, nullable=False, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    song = relationship("Songs", back_populates="weekly_entries")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_weekly_charts_date_position', 'chart_date', 'current_position'),
        Index('idx_weekly_charts_year_position', 'year', 'current_position'),
        Index('idx_weekly_charts_song_date', 'song_id', 'chart_date', unique=True),
        Index('idx_weekly_charts_position', 'current_position'),
    )
    
    def __repr__(self):
        return f"<WeeklyCharts(song_id={self.song_id}, date={self.chart_date}, position={self.current_position})>"


class YearlyCharts(Base):
    """
    Yearly chart summaries - aggregated statistics by year.
    
    This table contains one row per year with pre-calculated
    yearly statistics and summaries.
    """
    __tablename__ = 'yearly_charts'
    
    # Primary key
    year_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Year identification
    year = Column(Integer, nullable=False, unique=True, index=True)
    
    # Yearly statistics
    total_weeks = Column(Integer, nullable=False, default=0)
    total_unique_songs = Column(Integer, nullable=False, default=0)
    total_entries = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    number_one_songs = Column(Integer, nullable=False, default=0)
    most_weeks_at_number_one = Column(Integer, nullable=False, default=0)
    longest_staying_song = Column(String(255), nullable=True)
    longest_staying_weeks = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<YearlyCharts(year={self.year}, songs={self.total_unique_songs}, entries={self.total_entries})>"


class ChartWeeks(Base):
    """
    Weekly chart metadata - information about each chart week.
    
    This table contains metadata about each weekly chart,
    including number one songs and chart statistics.
    """
    __tablename__ = 'chart_weeks'
    
    # Primary key
    week_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Week identification
    chart_date = Column(Date, nullable=False, unique=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    week_number = Column(Integer, nullable=True)
    
    # Chart statistics
    total_entries = Column(Integer, nullable=False, default=100)
    new_entries = Column(Integer, nullable=False, default=0)
    re_entries = Column(Integer, nullable=False, default=0)
    
    # Number one information
    number_one_song = Column(String(255), nullable=True)
    number_one_artist = Column(String(255), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<ChartWeeks(date={self.chart_date}, entries={self.total_entries})>"


class SongStats(Base):
    """
    Pre-calculated song statistics - performance by year.
    
    This table contains pre-calculated statistics for songs
    by year, optimized for fast queries and analysis.
    """
    __tablename__ = 'song_stats'
    
    # Primary key
    stat_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to Songs table
    song_id = Column(Integer, ForeignKey('songs.song_id'), nullable=False, index=True)
    
    # Year identification
    year = Column(Integer, nullable=True, index=True)  # NULL for lifetime stats
    
    # Performance statistics
    total_weeks = Column(Integer, nullable=False, default=0)
    peak_position = Column(Integer, nullable=False)
    weeks_at_number_one = Column(Integer, nullable=False, default=0)
    weeks_in_top_10 = Column(Integer, nullable=False, default=0)
    weeks_in_top_40 = Column(Integer, nullable=False, default=0)
    average_position = Column(DECIMAL(5, 2), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    song = relationship("Songs", back_populates="song_stats")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_song_stats_song_year', 'song_id', 'year', unique=True),
        Index('idx_song_stats_year', 'year'),
        Index('idx_song_stats_peak_position', 'peak_position'),
    )
    
    def __repr__(self):
        return f"<SongStats(song_id={self.song_id}, year={self.year}, weeks={self.total_weeks})>"


# Additional utility tables for enhanced functionality

class ChartPositions(Base):
    """
    Position history - tracks how songs moved up/down the charts.
    
    This table can be used for analyzing chart movement patterns
    and position change trends.
    """
    __tablename__ = 'chart_positions'
    
    position_id = Column(Integer, primary_key=True, autoincrement=True)
    song_id = Column(Integer, ForeignKey('songs.song_id'), nullable=False, index=True)
    chart_date = Column(Date, nullable=False, index=True)
    position = Column(Integer, nullable=False, index=True)
    position_change = Column(Integer, nullable=True)
    weeks_on_chart = Column(Integer, nullable=False)
    
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_chart_positions_song_date', 'song_id', 'chart_date'),
        Index('idx_chart_positions_position', 'position'),
    )


class ArtistCollaborations(Base):
    """
    Artist collaborations - tracks songs with multiple artists.
    
    This table can be used to analyze collaboration patterns
    and featured artist relationships.
    """
    __tablename__ = 'artist_collaborations'
    
    collaboration_id = Column(Integer, primary_key=True, autoincrement=True)
    song_id = Column(Integer, ForeignKey('songs.song_id'), nullable=False, index=True)
    artist_name = Column(String(255), nullable=False, index=True)
    is_primary_artist = Column(Boolean, nullable=False, default=True)
    is_featured_artist = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_artist_collaborations_song', 'song_id'),
        Index('idx_artist_collaborations_artist', 'artist_name'),
    )


# Constants for common queries
class ChartConstants:
    """Constants for chart analysis."""
    
    # Chart positions
    CHART_SIZE = 100
    TOP_10 = 10
    TOP_40 = 40
    NUMBER_ONE = 1
    
    # Performance categories
    HIT_CATEGORIES = {
        'number_one': 1,
        'top_10': 10,
        'top_40': 40,
        'top_100': 100
    }
    
    # Time periods
    DECADES = {
        '2000s': (2000, 2009),
        '2010s': (2010, 2019),
        '2020s': (2020, 2029)
    }