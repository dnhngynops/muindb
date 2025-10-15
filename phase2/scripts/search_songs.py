#!/usr/bin/env python3
"""
Song Search Script (Genius API)
Search songs by name, artist, genre, or credits with comprehensive filtering options.
"""

import sys
import os
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, func

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

from database.connection import get_database_manager
from database.models import Songs
from database.phase2_models import Genres, SongGenres, Credits, SongCredits, CreditRoles, SongGeniusMetadata

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SongSearchEngine:
    """Advanced song search engine with genre and credits filtering."""
    
    def __init__(self):
        self.db_manager = get_database_manager()
    
    def search_by_name(self, song_name: str, exact_match: bool = False) -> List[Dict]:
        """Search songs by name."""
        with self.db_manager.get_session() as session:
            if exact_match:
                songs = session.query(Songs).filter(
                    Songs.song_name == song_name
                ).all()
            else:
                songs = session.query(Songs).filter(
                    Songs.song_name.ilike(f'%{song_name}%')
                ).all()
            
            return [self._song_to_dict(song, include_details=True) for song in songs]
    
    def search_by_artist(self, artist_name: str, exact_match: bool = False) -> List[Dict]:
        """Search songs by artist."""
        with self.db_manager.get_session() as session:
            if exact_match:
                songs = session.query(Songs).filter(
                    Songs.artist_name == artist_name
                ).all()
            else:
                songs = session.query(Songs).filter(
                    Songs.artist_name.ilike(f'%{artist_name}%')
                ).all()
            
            return [self._song_to_dict(song, include_details=True) for song in songs]
    
    def search_by_genre(self, genre_name: str, exact_match: bool = False) -> List[Dict]:
        """Search songs by genre."""
        with self.db_manager.get_session() as session:
            if exact_match:
                songs = session.query(Songs).join(SongGenres).join(Genres).filter(
                    Genres.genre_name == genre_name
                ).all()
            else:
                songs = session.query(Songs).join(SongGenres).join(Genres).filter(
                    Genres.genre_name.ilike(f'%{genre_name}%')
                ).all()
            
            return [self._song_to_dict(song, include_details=True) for song in songs]
    
    def search_by_credit(self, credit_name: str, role: str = None, exact_match: bool = False) -> List[Dict]:
        """Search songs by credit (writer, producer, etc.)."""
        with self.db_manager.get_session() as session:
            query = session.query(Songs).join(SongCredits).join(Credits)
            
            if role:
                query = query.join(CreditRoles).filter(CreditRoles.role_name == role)
            
            if exact_match:
                songs = query.filter(Credits.credit_name == credit_name).all()
            else:
                songs = query.filter(Credits.credit_name.ilike(f'%{credit_name}%')).all()
            
            return [self._song_to_dict(song, include_details=True) for song in songs]
    
    def search_comprehensive(self, song_name: str = None, artist_name: str = None, 
                           genre_name: str = None, credit_name: str = None, 
                           role: str = None, peak_position_max: int = None,
                           year_from: int = None, year_to: int = None,
                           weeks_on_chart_min: int = None, hot_only: bool = False) -> List[Dict]:
        """Comprehensive search with multiple filters."""
        with self.db_manager.get_session() as session:
            query = session.query(Songs)
            
            # Apply filters
            if song_name:
                query = query.filter(Songs.song_name.ilike(f'%{song_name}%'))
            
            if artist_name:
                query = query.filter(Songs.artist_name.ilike(f'%{artist_name}%'))
            
            if peak_position_max:
                query = query.filter(Songs.peak_position <= peak_position_max)
            
            if year_from:
                query = query.filter(Songs.first_chart_appearance >= f'{year_from}-01-01')
            
            if year_to:
                query = query.filter(Songs.first_chart_appearance <= f'{year_to}-12-31')
            
            if weeks_on_chart_min:
                query = query.filter(Songs.total_weeks_on_chart >= weeks_on_chart_min)
            
            # Genre filter
            if genre_name:
                query = query.join(SongGenres).join(Genres).filter(
                    Genres.genre_name.ilike(f'%{genre_name}%')
                )
            
            # Credit filter
            if credit_name:
                query = query.join(SongCredits).join(Credits).filter(
                    Credits.credit_name.ilike(f'%{credit_name}%')
                )
                
                if role:
                    query = query.join(CreditRoles).filter(CreditRoles.role_name == role)
            
            # Hot songs filter (Genius API specific)
            if hot_only:
                query = query.join(SongGeniusMetadata).filter(SongGeniusMetadata.hot == True)
            
            # Order by peak position
            query = query.order_by(Songs.peak_position)
            
            songs = query.all()
            return [self._song_to_dict(song, include_details=True) for song in songs]
    
    def get_song_details(self, song_id: int) -> Optional[Dict]:
        """Get detailed information about a specific song."""
        with self.db_manager.get_session() as session:
            song = session.query(Songs).filter(Songs.song_id == song_id).first()
            if not song:
                return None
            
            return self._song_to_dict(song, include_details=True)
    
    def get_genre_statistics(self) -> List[Dict]:
        """Get genre distribution statistics."""
        with self.db_manager.get_session() as session:
            stats = session.query(
                Genres.genre_name,
                func.count(SongGenres.song_id).label('song_count'),
                func.avg(Songs.peak_position).label('avg_peak_position'),
                func.min(Songs.peak_position).label('best_position')
            ).select_from(
                Genres
            ).join(
                SongGenres, Genres.genre_id == SongGenres.genre_id
            ).join(
                Songs, SongGenres.song_id == Songs.song_id
            ).group_by(
                Genres.genre_id, Genres.genre_name
            ).order_by(func.count(SongGenres.song_id).desc()).all()
            
            return [
                {
                    'genre': stat.genre_name,
                    'song_count': stat.song_count,
                    'avg_peak_position': round(stat.avg_peak_position, 2) if stat.avg_peak_position else None,
                    'best_position': stat.best_position
                }
                for stat in stats
            ]
    
    def get_credit_statistics(self, role: str = None) -> List[Dict]:
        """Get credit statistics by role."""
        with self.db_manager.get_session() as session:
            query = session.query(
                Credits.credit_name,
                CreditRoles.role_name,
                func.count(SongCredits.song_id).label('song_count'),
                func.avg(Songs.peak_position).label('avg_peak_position'),
                func.min(Songs.peak_position).label('best_position')
            ).select_from(
                Credits
            ).join(
                SongCredits, Credits.credit_id == SongCredits.credit_id
            ).join(
                CreditRoles, SongCredits.role_id == CreditRoles.role_id
            ).join(
                Songs, SongCredits.song_id == Songs.song_id
            )
            
            if role:
                query = query.filter(CreditRoles.role_name == role)
            
            stats = query.group_by(
                Credits.credit_id, Credits.credit_name, CreditRoles.role_name
            ).order_by(func.count(SongCredits.song_id).desc()).all()
            
            return [
                {
                    'credit_name': stat.credit_name,
                    'role': stat.role_name,
                    'song_count': stat.song_count,
                    'avg_peak_position': round(stat.avg_peak_position, 2) if stat.avg_peak_position else None,
                    'best_position': stat.best_position
                }
                for stat in stats
            ]
    
    def get_genius_metadata_stats(self) -> Dict:
        """Get Genius API metadata statistics."""
        with self.db_manager.get_session() as session:
            total_songs = session.query(Songs).count()
            songs_with_metadata = session.query(SongGeniusMetadata).count()
            hot_songs = session.query(SongGeniusMetadata).filter(SongGeniusMetadata.hot == True).count()
            
            # Get top songs by pyongs count
            top_pyongs = session.query(
                Songs.song_name,
                Songs.artist_name,
                SongGeniusMetadata.pyongs_count
            ).join(SongGeniusMetadata).order_by(
                SongGeniusMetadata.pyongs_count.desc()
            ).limit(10).all()
            
            return {
                'total_songs': total_songs,
                'songs_with_metadata': songs_with_metadata,
                'metadata_coverage': round((songs_with_metadata / total_songs * 100), 2) if total_songs > 0 else 0,
                'hot_songs': hot_songs,
                'top_pyongs': [
                    {
                        'song_name': song.song_name,
                        'artist_name': song.artist_name,
                        'pyongs_count': song.pyongs_count
                    }
                    for song in top_pyongs
                ]
            }
    
    def _song_to_dict(self, song: Songs, include_details: bool = False) -> Dict:
        """Convert song object to dictionary."""
        result = {
            'song_id': song.song_id,
            'song_name': song.song_name,
            'artist_name': song.artist_name,
            'peak_position': song.peak_position,
            'total_weeks_on_chart': song.total_weeks_on_chart,
            'weeks_at_number_one': song.weeks_at_number_one,
            'first_chart_appearance': song.first_chart_appearance.isoformat() if song.first_chart_appearance else None,
            'last_chart_appearance': song.last_chart_appearance.isoformat() if song.last_chart_appearance else None
        }
        
        if include_details:
            # Get genres
            with self.db_manager.get_session() as session:
                genres = session.query(Genres.genre_name).join(SongGenres).filter(
                    SongGenres.song_id == song.song_id
                ).all()
                result['genres'] = [genre.genre_name for genre in genres]
                
                # Get credits
                credits = session.query(
                    Credits.credit_name, CreditRoles.role_name, SongCredits.is_primary
                ).select_from(SongCredits).join(
                    Credits, SongCredits.credit_id == Credits.credit_id
                ).join(
                    CreditRoles, SongCredits.role_id == CreditRoles.role_id
                ).filter(
                    SongCredits.song_id == song.song_id
                ).all()
                
                result['credits'] = [
                    {
                        'name': credit.credit_name,
                        'role': credit.role_name,
                        'is_primary': credit.is_primary
                    }
                    for credit in credits
                ]
                
                # Get Genius metadata
                genius_meta = session.query(SongGeniusMetadata).filter(
                    SongGeniusMetadata.song_id == song.song_id
                ).first()
                
                if genius_meta:
                    result['genius_metadata'] = {
                        'genius_id': genius_meta.genius_id,
                        'genius_url': genius_meta.genius_url,
                        'release_date': genius_meta.release_date,
                        'pyongs_count': genius_meta.pyongs_count,
                        'hot': genius_meta.hot,
                        'lyrics_state': genius_meta.lyrics_state
                    }
        
        return result


def print_song_results(songs: List[Dict], show_details: bool = False):
    """Print search results in a formatted way."""
    if not songs:
        print("No songs found.")
        return
    
    print(f"\nFound {len(songs)} songs:")
    print("-" * 80)
    
    for i, song in enumerate(songs, 1):
        print(f"{i:2d}. {song['song_name']} - {song['artist_name']}")
        print(f"     Peak: #{song['peak_position']}, Weeks: {song['total_weeks_on_chart']}, #1s: {song['weeks_at_number_one']}")
        
        if show_details and 'genres' in song:
            if song['genres']:
                print(f"     Genres: {', '.join(song['genres'])}")
            else:
                print(f"     Genres: None")
            
            if 'credits' in song and song['credits']:
                credits_str = ', '.join([
                    f"{credit['name']} ({credit['role']})" 
                    for credit in song['credits']
                ])
                print(f"     Credits: {credits_str}")
            else:
                print(f"     Credits: None")
            
            if 'genius_metadata' in song and song['genius_metadata']:
                meta = song['genius_metadata']
                print(f"     Genius: {meta['pyongs_count']} pyongs, Hot: {meta['hot']}")
                if meta['genius_url']:
                    print(f"     URL: {meta['genius_url']}")
        
        print()


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='Search songs in the database')
    parser.add_argument('--song', type=str, help='Search by song name')
    parser.add_argument('--artist', type=str, help='Search by artist name')
    parser.add_argument('--genre', type=str, help='Search by genre')
    parser.add_argument('--credit', type=str, help='Search by credit name')
    parser.add_argument('--role', type=str, help='Filter by credit role (writer, producer, etc.)')
    parser.add_argument('--peak-max', type=int, help='Maximum peak position')
    parser.add_argument('--year-from', type=int, help='From year')
    parser.add_argument('--year-to', type=int, help='To year')
    parser.add_argument('--weeks-min', type=int, help='Minimum weeks on chart')
    parser.add_argument('--hot-only', action='store_true', help='Only show hot songs (Genius)')
    parser.add_argument('--exact', action='store_true', help='Use exact matching')
    parser.add_argument('--details', action='store_true', help='Show detailed information')
    parser.add_argument('--limit', type=int, default=20, help='Limit results (default: 20)')
    parser.add_argument('--stats', action='store_true', help='Show genre/credit statistics')
    parser.add_argument('--genius-stats', action='store_true', help='Show Genius API statistics')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize search engine
    search_engine = SongSearchEngine()
    
    # Show statistics if requested
    if args.stats:
        print("\n" + "="*50)
        print("GENRE STATISTICS")
        print("="*50)
        genre_stats = search_engine.get_genre_statistics()
        for stat in genre_stats[:20]:  # Top 20
            print(f"{stat['genre']:20} | Songs: {stat['song_count']:4d} | Avg Peak: {stat['avg_peak_position']:6.1f} | Best: #{stat['best_position']:2d}")
        
        print("\n" + "="*50)
        print("CREDIT STATISTICS (Top Writers)")
        print("="*50)
        credit_stats = search_engine.get_credit_statistics('Writer')
        for stat in credit_stats[:20]:  # Top 20
            print(f"{stat['credit_name']:25} | Songs: {stat['song_count']:4d} | Avg Peak: {stat['avg_peak_position']:6.1f} | Best: #{stat['best_position']:2d}")
        
        return
    
    if args.genius_stats:
        print("\n" + "="*50)
        print("GENIUS API STATISTICS")
        print("="*50)
        genius_stats = search_engine.get_genius_metadata_stats()
        print(f"Total songs in database: {genius_stats['total_songs']:,}")
        print(f"Songs with Genius metadata: {genius_stats['songs_with_metadata']:,}")
        print(f"Metadata coverage: {genius_stats['metadata_coverage']}%")
        print(f"Hot songs: {genius_stats['hot_songs']:,}")
        
        print(f"\nTop songs by pyongs count:")
        for song in genius_stats['top_pyongs']:
            print(f"  {song['song_name']} - {song['artist_name']} ({song['pyongs_count']:,} pyongs)")
        
        return
    
    # Perform search
    if args.song:
        results = search_engine.search_by_name(args.song, args.exact)
    elif args.artist:
        results = search_engine.search_by_artist(args.artist, args.exact)
    elif args.genre:
        results = search_engine.search_by_genre(args.genre, args.exact)
    elif args.credit:
        results = search_engine.search_by_credit(args.credit, args.role, args.exact)
    else:
        # Comprehensive search
        results = search_engine.search_comprehensive(
            song_name=args.song,
            artist_name=args.artist,
            genre_name=args.genre,
            credit_name=args.credit,
            role=args.role,
            peak_position_max=args.peak_max,
            year_from=args.year_from,
            year_to=args.year_to,
            weeks_on_chart_min=args.weeks_min,
            hot_only=args.hot_only
        )
    
    # Limit results
    results = results[:args.limit]
    
    # Print results
    print_song_results(results, args.details)


if __name__ == '__main__':
    main()