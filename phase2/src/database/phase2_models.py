"""
Phase 2 Database Models for Genre and Credits (Genius API)
Extends the existing Billboard database with genre and credits information from Genius API.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .models import Base


class Genres(Base):
    """Master genre catalog with hierarchical structure."""
    __tablename__ = 'genres'
    
    genre_id = Column(Integer, primary_key=True, autoincrement=True)
    genre_name = Column(String(100), nullable=False, unique=True)
    parent_genre_id = Column(Integer, ForeignKey('genres.genre_id'), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    parent_genre = relationship("Genres", remote_side=[genre_id], backref="subgenres")
    song_genres = relationship("SongGenres", back_populates="genre")


class SongGenres(Base):
    """Many-to-many relationship between songs and genres."""
    __tablename__ = 'song_genres'
    
    song_genre_id = Column(Integer, primary_key=True, autoincrement=True)
    song_id = Column(Integer, ForeignKey('songs.song_id', ondelete='CASCADE'), nullable=False)
    genre_id = Column(Integer, ForeignKey('genres.genre_id', ondelete='CASCADE'), nullable=False)
    confidence_score = Column(Numeric(3, 2), default=1.0)  # 0.0 to 1.0
    source = Column(String(50), default='genius')  # genius, manual, etc.
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    # song = relationship("Songs", back_populates="song_genres")
    genre = relationship("Genres", back_populates="song_genres")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('song_id', 'genre_id', name='uq_song_genre'),
    )


class CreditRoles(Base):
    """Types of credits (writer, producer, etc.)."""
    __tablename__ = 'credit_roles'
    
    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(50), nullable=False, unique=True)
    role_category = Column(String(30), nullable=False)  # creative, technical, performance, etc.
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())


class Credits(Base):
    """Master credits catalog (people who worked on songs)."""
    __tablename__ = 'credits'
    
    credit_id = Column(Integer, primary_key=True, autoincrement=True)
    credit_name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)  # For matching variations
    genius_id = Column(Integer, nullable=True)  # Genius Artist ID
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    song_credits = relationship("SongCredits", back_populates="credit")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('normalized_name', name='uq_credits_normalized_name'),
    )


class SongCredits(Base):
    """Many-to-many relationship between songs and credits with roles."""
    __tablename__ = 'song_credits'
    
    song_credit_id = Column(Integer, primary_key=True, autoincrement=True)
    song_id = Column(Integer, ForeignKey('songs.song_id', ondelete='CASCADE'), nullable=False)
    credit_id = Column(Integer, ForeignKey('credits.credit_id', ondelete='CASCADE'), nullable=False)
    role_id = Column(Integer, ForeignKey('credit_roles.role_id', ondelete='CASCADE'), nullable=False)
    is_primary = Column(Boolean, default=False)  # True if this is the main artist
    source = Column(String(50), default='genius')  # genius, manual, etc.
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    # song = relationship("Songs", back_populates="song_credits")
    credit = relationship("Credits", back_populates="song_credits")
    role = relationship("CreditRoles")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('song_id', 'credit_id', 'role_id', name='uq_song_credit_role'),
    )


class SongGeniusMetadata(Base):
    """Store Genius API metadata for songs."""
    __tablename__ = 'song_genius_metadata'
    
    metadata_id = Column(Integer, primary_key=True, autoincrement=True)
    song_id = Column(Integer, ForeignKey('songs.song_id', ondelete='CASCADE'), nullable=False)
    genius_id = Column(Integer, nullable=False, unique=True)
    genius_url = Column(String(500), nullable=True)
    release_date = Column(String(50), nullable=True)
    lyrics_state = Column(String(20), nullable=True)
    pyongs_count = Column(Integer, default=0)
    hot = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    # song = relationship("Songs", back_populates="genius_metadata")


# Update the existing Songs model to include relationships
def add_phase2_relationships():
    """Add Phase 2 relationships to existing Songs model."""
    from .models import Songs
    
    # Add relationships to existing Songs model
    Songs.song_genres = relationship("SongGenres", back_populates="song")
    Songs.song_credits = relationship("SongCredits", back_populates="song")
    Songs.genius_metadata = relationship("SongGeniusMetadata", back_populates="song")