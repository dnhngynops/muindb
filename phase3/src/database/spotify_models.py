#!/usr/bin/env python3
"""
Spotify-specific database models for genre tagging.
Extends the existing Phase 2 schema with Spotify integration.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class SpotifyTracks(Base):
    """Spotify track information."""
    __tablename__ = 'spotify_tracks'
    
    spotify_id = Column(String(50), primary_key=True)
    song_id = Column(Integer, nullable=False, unique=True)  # Foreign key will be added after table creation
    spotify_name = Column(String(500), nullable=False)
    spotify_artists = Column(Text)  # JSON string of artist names
    popularity = Column(Integer, default=0)
    explicit = Column(Boolean, default=False)
    release_date = Column(String(20))  # YYYY-MM-DD format
    album_name = Column(String(500))
    preview_url = Column(String(1000))
    spotify_url = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships (will be set up after all models are defined)
    # song = relationship("Songs", back_populates="spotify_track")
    # genres = relationship("SongSpotifyGenres", back_populates="spotify_track")


class SongSpotifyGenres(Base):
    """Many-to-many relationship between songs and Spotify genres."""
    __tablename__ = 'song_spotify_genres'
    
    id = Column(Integer, primary_key=True)
    song_id = Column(Integer, nullable=False)  # Foreign key will be added after table creation
    spotify_id = Column(String(50), ForeignKey('spotify_tracks.spotify_id'), nullable=False)
    genre_name = Column(String(200), nullable=False)
    confidence_score = Column(Float, default=0.8)
    source = Column(String(50), default='spotify')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships (will be set up after all models are defined)
    # song = relationship("Songs", back_populates="spotify_genres")
    # spotify_track = relationship("SpotifyTracks", back_populates="genres")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('song_id', 'spotify_id', 'genre_name', name='uq_song_spotify_genre'),
    )


class SpotifyGenres(Base):
    """Master catalog of Spotify genres."""
    __tablename__ = 'spotify_genres'
    
    genre_id = Column(Integer, primary_key=True)
    genre_name = Column(String(200), unique=True, nullable=False)
    genre_category = Column(String(100))  # e.g., 'main', 'sub', 'micro'
    parent_genre = Column(String(200))  # For hierarchical genres
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('genre_name', name='uq_spotify_genre_name'),
    )


class SpotifyMetadata(Base):
    """Additional Spotify metadata for songs."""
    __tablename__ = 'song_spotify_metadata'
    
    id = Column(Integer, primary_key=True)
    song_id = Column(Integer, nullable=False, unique=True)  # Foreign key will be added after table creation
    spotify_id = Column(String(50), ForeignKey('spotify_tracks.spotify_id'), nullable=False)
    danceability = Column(Float)  # 0.0 to 1.0
    energy = Column(Float)  # 0.0 to 1.0
    valence = Column(Float)  # 0.0 to 1.0 (musical positivity)
    tempo = Column(Float)  # BPM
    loudness = Column(Float)  # dB
    acousticness = Column(Float)  # 0.0 to 1.0
    instrumentalness = Column(Float)  # 0.0 to 1.0
    liveness = Column(Float)  # 0.0 to 1.0
    speechiness = Column(Float)  # 0.0 to 1.0
    key = Column(Integer)  # 0-11 (musical key)
    mode = Column(Integer)  # 0=minor, 1=major
    time_signature = Column(Integer)  # 3/4, 4/4, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships (will be set up after all models are defined)
    # song = relationship("Songs", back_populates="spotify_metadata")
    # spotify_track = relationship("SpotifyTracks")


# Add relationships to existing Songs model (these would be added to the main models.py)
# Note: These are just for reference - the actual relationships would be added to the Songs class
"""
# Add these relationships to the Songs class in models.py:
spotify_track = relationship("SpotifyTracks", back_populates="song", uselist=False)
spotify_genres = relationship("SongSpotifyGenres", back_populates="song")
spotify_metadata = relationship("SpotifyMetadata", back_populates="song", uselist=False)
"""
