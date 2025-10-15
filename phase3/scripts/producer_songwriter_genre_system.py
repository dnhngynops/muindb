#!/usr/bin/env python3
"""
Producer and Songwriter Genre Classification System

This module classifies producers and songwriters based on the genres of songs they've worked on.
Uses a simple majority-based classification approach.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from collections import Counter
import json

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

from database.connection import get_database_manager
from database.models import Songs
from database.phase2_models import Genres, SongGenres, Credits, SongCredits, CreditRoles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CreatorClassificationResult:
    """Result of producer/songwriter genre classification."""
    creator_name: str
    creator_type: str
    primary_genre: str
    secondary_genres: List[str]
    confidence_score: float
    total_songs: int
    genre_breakdown: Dict[str, int]
    reasoning: str


class ProducerSongwriterGenreSystem:
    """System for classifying producers and songwriters based on their work."""
    
    def __init__(self):
        """Initialize the creator classification system."""
        self.db_manager = get_database_manager()
        
        # Cache for results
        self._classification_cache = {}
        
        logger.info("Producer/Songwriter Genre Classification System initialized")
    
    def classify_creator(self, creator_name: str, creator_type: str) -> CreatorClassificationResult:
        """
        Classify a producer or songwriter based on genres of songs they've worked on.
        
        Args:
            creator_name: Name of the producer/songwriter
            creator_type: 'producer' or 'songwriter'
            
        Returns:
            CreatorClassificationResult with classification
        """
        # Check cache first
        cache_key = f"{creator_type}_{creator_name.lower()}"
        if cache_key in self._classification_cache:
            logger.debug(f"Using cached classification for {creator_type} {creator_name}")
            return self._classification_cache[cache_key]
        
        logger.info(f"Classifying {creator_type}: {creator_name}")
        
        try:
            with self.db_manager.get_session() as session:
                # Get songs this creator has worked on
                songs_query = session.query(
                    Songs.song_name,
                    Songs.artist_name,
                    Songs.song_id
                ).join(
                    SongCredits, Songs.song_id == SongCredits.song_id
                ).join(
                    Credits, SongCredits.credit_id == Credits.credit_id
                ).join(
                    CreditRoles, SongCredits.role_id == CreditRoles.role_id
                ).filter(
                    Credits.credit_name.ilike(f"%{creator_name}%"),
                    CreditRoles.role_name.ilike(f"%{creator_type}%")
                ).limit(100)  # Limit to avoid too much processing
                
                songs = songs_query.all()
                
                if not songs:
                    result = CreatorClassificationResult(
                        creator_name=creator_name,
                        creator_type=creator_type,
                        primary_genre='other',
                        secondary_genres=[],
                        confidence_score=0.0,
                        total_songs=0,
                        genre_breakdown={},
                        reasoning=f"No songs found for {creator_type} {creator_name}"
                    )
                    self._classification_cache[cache_key] = result
                    return result
                
                # Get genres for each song
                song_genres = {}
                for song_name, artist_name, song_id in songs:
                    # Get genres for this song
                    genres_query = session.query(Genres.genre_name).join(
                        SongGenres, Genres.genre_id == SongGenres.genre_id
                    ).filter(SongGenres.song_id == song_id)
                    
                    genres = [row[0] for row in genres_query.all()]
                    song_genres[song_id] = {
                        'song_name': song_name,
                        'artist_name': artist_name,
                        'genres': genres
                    }
                
                # Analyze genre distribution
                result = self._analyze_creator_genres(
                    creator_name, creator_type, songs, song_genres
                )
                
                # Cache the result
                self._classification_cache[cache_key] = result
                
                return result
                
        except Exception as e:
            logger.error(f"Error classifying {creator_type} {creator_name}: {e}")
            result = CreatorClassificationResult(
                creator_name=creator_name,
                creator_type=creator_type,
                primary_genre='other',
                secondary_genres=[],
                confidence_score=0.0,
                total_songs=0,
                genre_breakdown={},
                reasoning=f"Error during classification: {str(e)}"
            )
            return result
    
    def _analyze_creator_genres(self, creator_name: str, creator_type: str,
                              songs: List[Tuple], song_genres: Dict[int, Dict]) -> CreatorClassificationResult:
        """
        Analyze genre distribution for a creator.
        
        Args:
            creator_name: Name of the creator
            creator_type: Type of creator
            songs: List of songs the creator worked on
            song_genres: Dictionary mapping song_id to genre information
            
        Returns:
            CreatorClassificationResult
        """
        # Count genres across all songs
        genre_counts = Counter()
        songs_with_genres = 0
        
        for song_name, artist_name, song_id in songs:
            if song_id in song_genres and song_genres[song_id]['genres']:
                songs_with_genres += 1
                for genre in song_genres[song_id]['genres']:
                    genre_counts[genre] += 1
        
        total_songs = len(songs)
        
        if not genre_counts:
            return CreatorClassificationResult(
                creator_name=creator_name,
                creator_type=creator_type,
                primary_genre='other',
                secondary_genres=[],
                confidence_score=0.0,
                total_songs=total_songs,
                genre_breakdown={},
                reasoning=f"No genre data available for {total_songs} songs"
            )
        
        # Determine primary genre (most common)
        primary_genre = genre_counts.most_common(1)[0][0]
        
        # Calculate confidence based on how dominant the primary genre is
        total_genre_occurrences = sum(genre_counts.values())
        primary_genre_count = genre_counts[primary_genre]
        confidence_score = primary_genre_count / total_genre_occurrences
        
        # Get secondary genres (other genres with significant representation)
        secondary_genres = []
        for genre, count in genre_counts.most_common():
            if genre != primary_genre and count >= 2:  # At least 2 occurrences
                secondary_genres.append(genre)
        
        # Limit secondary genres
        secondary_genres = secondary_genres[:5]
        
        # Build reasoning
        reasoning_parts = []
        reasoning_parts.append(f"Analyzed {total_songs} songs ({songs_with_genres} with genre data)")
        reasoning_parts.append(f"Primary: {primary_genre} ({primary_genre_count}/{total_genre_occurrences} occurrences)")
        
        if secondary_genres:
            reasoning_parts.append(f"Secondary: {', '.join(secondary_genres)}")
        
        reasoning_parts.append(f"Confidence: {confidence_score:.2f}")
        
        reasoning = ". ".join(reasoning_parts)
        
        return CreatorClassificationResult(
            creator_name=creator_name,
            creator_type=creator_type,
            primary_genre=primary_genre,
            secondary_genres=secondary_genres,
            confidence_score=confidence_score,
            total_songs=total_songs,
            genre_breakdown=dict(genre_counts),
            reasoning=reasoning
        )
    
    def classify_creators_batch(self, creators: List[Tuple[str, str]], 
                              delay: float = 0.1) -> List[CreatorClassificationResult]:
        """
        Classify multiple creators in batch.
        
        Args:
            creators: List of (creator_name, creator_type) tuples
            delay: Delay between classifications (for logging)
            
        Returns:
            List of CreatorClassificationResult objects
        """
        results = []
        
        for i, (creator_name, creator_type) in enumerate(creators, 1):
            logger.info(f"Processing creator {i}/{len(creators)}: {creator_type} {creator_name}")
            
            try:
                result = self.classify_creator(creator_name, creator_type)
                results.append(result)
                
                # Small delay for logging
                if i < len(creators):
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Error classifying {creator_type} {creator_name}: {e}")
                # Create error result
                error_result = CreatorClassificationResult(
                    creator_name=creator_name,
                    creator_type=creator_type,
                    primary_genre='other',
                    secondary_genres=[],
                    confidence_score=0.0,
                    total_songs=0,
                    genre_breakdown={},
                    reasoning=f"Error during classification: {str(e)}"
                )
                results.append(error_result)
        
        return results
    
    def get_top_creators_by_genre(self, genre: str, creator_type: str, limit: int = 20) -> List[Dict]:
        """
        Get top creators in a specific genre.
        
        Args:
            genre: Genre to filter by
            creator_type: 'producer' or 'songwriter'
            limit: Maximum number of results
            
        Returns:
            List of creator information
        """
        try:
            with self.db_manager.get_session() as session:
                # Get creators who have worked on songs in this genre
                query = session.query(
                    Credits.credit_name,
                    session.query(SongCredits).join(Songs).join(SongGenres).join(Genres).filter(
                        SongCredits.credit_id == Credits.credit_id,
                        Songs.song_id == SongCredits.song_id,
                        SongGenres.song_id == Songs.song_id,
                        Genres.genre_id == SongGenres.genre_id,
                        Genres.genre_name == genre
                    ).count().label('song_count')
                ).join(SongCredits).join(CreditRoles).filter(
                    CreditRoles.role_name.ilike(f"%{creator_type}%")
                ).group_by(Credits.credit_name).order_by('song_count DESC').limit(limit)
                
                results = []
                for row in query.all():
                    results.append({
                        'creator_name': row[0],
                        'creator_type': creator_type,
                        'song_count': row[1],
                        'genre': genre
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting top {creator_type}s for genre {genre}: {e}")
            return []
    
    def get_genre_network_analysis(self, creator_name: str, creator_type: str) -> Dict[str, Any]:
        """
        Analyze the genre network for a creator (what genres they work in and with whom).
        
        Args:
            creator_name: Name of the creator
            creator_type: Type of creator
            
        Returns:
            Dictionary with network analysis
        """
        try:
            with self.db_manager.get_session() as session:
                # Get all songs and their genres for this creator
                songs_query = session.query(
                    Songs.song_name,
                    Songs.artist_name,
                    Genres.genre_name
                ).join(
                    SongCredits, Songs.song_id == SongCredits.song_id
                ).join(
                    Credits, SongCredits.credit_id == Credits.credit_id
                ).join(
                    CreditRoles, SongCredits.role_id == CreditRoles.role_id
                ).join(
                    SongGenres, Songs.song_id == SongGenres.song_id
                ).join(
                    Genres, SongGenres.genre_id == Genres.genre_id
                ).filter(
                    Credits.credit_name.ilike(f"%{creator_name}%"),
                    CreditRoles.role_name.ilike(f"%{creator_type}%")
                )
                
                songs_data = songs_query.all()
                
                # Analyze the network
                genre_artists = {}
                genre_songs = {}
                
                for song_name, artist_name, genre_name in songs_data:
                    if genre_name not in genre_artists:
                        genre_artists[genre_name] = set()
                        genre_songs[genre_name] = set()
                    
                    genre_artists[genre_name].add(artist_name)
                    genre_songs[genre_name].add(song_name)
                
                # Convert sets to lists for JSON serialization
                network_analysis = {
                    'creator_name': creator_name,
                    'creator_type': creator_type,
                    'total_songs': len(set((song[0], song[1]) for song in songs_data)),
                    'genre_network': {}
                }
                
                for genre in genre_artists:
                    network_analysis['genre_network'][genre] = {
                        'song_count': len(genre_songs[genre]),
                        'artist_count': len(genre_artists[genre]),
                        'artists': list(genre_artists[genre]),
                        'songs': list(genre_songs[genre])
                    }
                
                return network_analysis
                
        except Exception as e:
            logger.error(f"Error analyzing genre network for {creator_type} {creator_name}: {e}")
            return {'error': str(e)}
    
    def save_results_to_database(self, results: List[CreatorClassificationResult]):
        """
        Save creator classification results to database.
        
        Note: This would require additional tables for creator genres.
        For now, this is a placeholder for future implementation.
        
        Args:
            results: List of CreatorClassificationResult objects
        """
        logger.info(f"Saving {len(results)} creator classifications to database")
        
        # TODO: Implement database schema for creator genres
        # This would require tables like:
        # - creator_genres (creator_id, genre_id, confidence_score, source)
        # - creators (creator_id, creator_name, creator_type)
        
        logger.warning("Creator genre database storage not yet implemented")
        
        # For now, just log the results
        for result in results:
            logger.info(f"{result.creator_type.title()}: {result.creator_name} -> {result.primary_genre} "
                       f"(confidence: {result.confidence_score:.2f}, {result.total_songs} songs)")


def main():
    """Main function for testing the creator classification system."""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='Producer/Songwriter Genre Classification System')
    parser.add_argument('--creator', type=str, help='Creator name to classify')
    parser.add_argument('--type', type=str, choices=['producer', 'songwriter'], 
                       help='Type of creator to classify')
    parser.add_argument('--batch', type=str, help='JSON file with list of creators to classify')
    parser.add_argument('--top-by-genre', type=str, help='Get top creators in a specific genre')
    parser.add_argument('--genre-type', type=str, choices=['producer', 'songwriter'],
                       help='Creator type for top-by-genre query')
    parser.add_argument('--network-analysis', type=str, help='Analyze genre network for a creator')
    parser.add_argument('--network-type', type=str, choices=['producer', 'songwriter'],
                       help='Creator type for network analysis')
    parser.add_argument('--test', action='store_true', help='Run test classifications')
    parser.add_argument('--save-db', action='store_true', help='Save results to database')
    
    args = parser.parse_args()
    
    # Initialize the system
    system = ProducerSongwriterGenreSystem()
    
    if args.test:
        # Test with some well-known creators
        test_creators = [
            ("Max Martin", "producer"),
            ("Dr. Dre", "producer"),
            ("Timbaland", "producer"),
            ("Diane Warren", "songwriter"),
            ("Max Martin", "songwriter")
        ]
        
        print(f"\n{'='*60}")
        print("TESTING CREATOR CLASSIFICATION SYSTEM")
        print(f"{'='*60}")
        
        for creator_name, creator_type in test_creators:
            print(f"\n👤 Classifying: {creator_type.title()} {creator_name}")
            print("-" * 50)
            
            result = system.classify_creator(creator_name, creator_type)
            
            print(f"Primary Genre: {result.primary_genre}")
            print(f"Secondary Genres: {', '.join(result.secondary_genres)}")
            print(f"Confidence: {result.confidence_score:.2f}")
            print(f"Total Songs: {result.total_songs}")
            print(f"Genre Breakdown: {result.genre_breakdown}")
            print(f"Reasoning: {result.reasoning}")
            
            time.sleep(0.5)
    
    elif args.creator and args.type:
        result = system.classify_creator(args.creator, args.type)
        
        print(f"\n👤 Creator Classification Results")
        print(f"{'='*40}")
        print(f"{args.type.title()}: {args.creator}")
        print(f"Primary Genre: {result.primary_genre}")
        print(f"Secondary Genres: {', '.join(result.secondary_genres)}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Total Songs: {result.total_songs}")
        print(f"Genre Breakdown: {result.genre_breakdown}")
        print(f"Reasoning: {result.reasoning}")
    
    elif args.batch:
        # Load creators from JSON file
        try:
            with open(args.batch, 'r') as f:
                creators_data = json.load(f)
            
            if isinstance(creators_data, list):
                creators = [(item['creator'], item['type']) for item in creators_data]
            else:
                print("Error: JSON file should contain a list of objects with 'creator' and 'type' keys")
                return
            
            print(f"\n👤 Batch Classification: {len(creators)} creators")
            print(f"{'='*50}")
            
            results = system.classify_creators_batch(creators)
            
            # Print summary
            genre_counts = {}
            type_counts = {'producer': 0, 'songwriter': 0}
            
            for result in results:
                genre_counts[result.primary_genre] = genre_counts.get(result.primary_genre, 0) + 1
                type_counts[result.creator_type] += 1
            
            print(f"\nClassification Summary:")
            print(f"By Type:")
            for creator_type, count in type_counts.items():
                print(f"  {creator_type.title()}s: {count}")
            
            print(f"\nBy Genre:")
            for genre, count in sorted(genre_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {genre}: {count} creators")
            
            # Save to database if requested
            if args.save_db:
                system.save_results_to_database(results)
                print(f"\n✅ Results saved to database")
            
        except Exception as e:
            print(f"Error processing batch file: {e}")
    
    elif args.top_by_genre and args.genre_type:
        print(f"\n🏆 Top {args.genre_type.title()}s in {args.top_by_genre}")
        print(f"{'='*50}")
        
        results = system.get_top_creators_by_genre(args.top_by_genre, args.genre_type)
        
        if results:
            for i, result in enumerate(results[:20], 1):
                print(f"{i:2d}. {result['creator_name']:<25} ({result['song_count']} songs)")
        else:
            print(f"No {args.genre_type}s found for genre {args.top_by_genre}")
    
    elif args.network_analysis and args.network_type:
        print(f"\n🕸️  Genre Network Analysis: {args.network_type.title()} {args.network_analysis}")
        print(f"{'='*60}")
        
        analysis = system.get_genre_network_analysis(args.network_analysis, args.network_type)
        
        if 'error' in analysis:
            print(f"Error: {analysis['error']}")
        else:
            print(f"Total Songs: {analysis['total_songs']}")
            print(f"\nGenre Network:")
            
            for genre, data in analysis['genre_network'].items():
                print(f"\n🎵 {genre}:")
                print(f"   Songs: {data['song_count']}")
                print(f"   Artists: {data['artist_count']}")
                print(f"   Top Artists: {', '.join(data['artists'][:5])}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
