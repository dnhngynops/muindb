#!/usr/bin/env python3
"""
A&R Insights Analyzer for Billboard Music Database
Advanced analytics and insights for A&R decision making
Adapted from ARI project for Billboard database structure
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import statistics

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file."""
    env_file = project_root / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load .env file
load_env_file()

from database.connection import get_database_manager
from database.models import Songs, Artists, WeeklyCharts
from database.phase2_models import Genres, SongGenres, Credits, SongCredits, CreditRoles
from database.spotify_models import SpotifyTracks, SongSpotifyGenres, SpotifyGenres

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ARInsightsAnalyzer:
    """
    A&R Insights Analyzer for comprehensive music industry analysis.
    
    Provides insights for:
    - Artist development opportunities
    - Genre trends and market positioning
    - Crossover potential analysis
    - Producer/songwriter effectiveness
    - Chart performance patterns
    """
    
    def __init__(self):
        """Initialize the A&R insights analyzer."""
        self.db_manager = get_database_manager()
        
        # Analysis results storage
        self.insights = {
            'genre_trends': {},
            'artist_opportunities': {},
            'crossover_analysis': {},
            'producer_effectiveness': {},
            'chart_patterns': {},
            'market_insights': {}
        }
        
        logger.info("A&R Insights Analyzer initialized")
    
    def generate_comprehensive_insights(self) -> Dict[str, Any]:
        """
        Generate comprehensive A&R insights from the database.
        
        Returns:
            Dictionary containing all insights
        """
        logger.info("Generating comprehensive A&R insights...")
        
        # 1. Genre Trends Analysis
        self.insights['genre_trends'] = self._analyze_genre_trends()
        
        # 2. Artist Development Opportunities
        self.insights['artist_opportunities'] = self._analyze_artist_opportunities()
        
        # 3. Crossover Potential Analysis
        self.insights['crossover_analysis'] = self._analyze_crossover_potential()
        
        # 4. Producer/Songwriter Effectiveness
        self.insights['producer_effectiveness'] = self._analyze_producer_effectiveness()
        
        # 5. Chart Performance Patterns
        self.insights['chart_patterns'] = self._analyze_chart_patterns()
        
        # 6. Market Insights
        self.insights['market_insights'] = self._generate_market_insights()
        
        logger.info("Comprehensive A&R insights generated")
        return self.insights
    
    def _analyze_genre_trends(self) -> Dict[str, Any]:
        """Analyze genre trends over time."""
        logger.info("Analyzing genre trends...")
        
        try:
            with self.db_manager.get_session() as session:
                # Get genre distribution by year
                genre_yearly = session.query(
                    Genres.name,
                    Songs.release_year,
                    func.count(Songs.song_id).label('song_count')
                ).join(
                    SongGenres, Genres.genre_id == SongGenres.genre_id
                ).join(
                    Songs, SongGenres.song_id == Songs.song_id
                ).filter(
                    Songs.release_year.isnot(None),
                    Songs.release_year >= 2000
                ).group_by(
                    Genres.name, Songs.release_year
                ).order_by(
                    Songs.release_year.desc(), func.count(Songs.song_id).desc()
                ).all()
                
                # Process genre trends
                genre_trends = defaultdict(list)
                for genre_name, year, count in genre_yearly:
                    genre_trends[genre_name].append({
                        'year': year,
                        'song_count': count
                    })
                
                # Calculate trend directions
                trend_analysis = {}
                for genre, yearly_data in genre_trends.items():
                    if len(yearly_data) >= 3:  # Need at least 3 years of data
                        years = [d['year'] for d in yearly_data]
                        counts = [d['song_count'] for d in yearly_data]
                        
                        # Calculate trend slope
                        if len(years) > 1:
                            trend_slope = statistics.correlation(years, counts) if len(years) > 2 else 0
                            
                            trend_analysis[genre] = {
                                'trend_direction': 'rising' if trend_slope > 0.3 else 'declining' if trend_slope < -0.3 else 'stable',
                                'trend_strength': abs(trend_slope),
                                'recent_performance': counts[-1] if counts else 0,
                                'peak_year': years[counts.index(max(counts))] if counts else None,
                                'yearly_data': yearly_data
                            }
                
                # Identify emerging genres
                emerging_genres = []
                for genre, analysis in trend_analysis.items():
                    if (analysis['trend_direction'] == 'rising' and 
                        analysis['trend_strength'] > 0.5 and
                        analysis['recent_performance'] > 5):
                        emerging_genres.append({
                            'genre': genre,
                            'trend_strength': analysis['trend_strength'],
                            'recent_songs': analysis['recent_performance']
                        })
                
                # Sort by trend strength
                emerging_genres.sort(key=lambda x: x['trend_strength'], reverse=True)
                
                return {
                    'trend_analysis': trend_analysis,
                    'emerging_genres': emerging_genres[:10],  # Top 10 emerging genres
                    'total_genres_analyzed': len(trend_analysis),
                    'analysis_period': '2000-2024'
                }
                
        except Exception as e:
            logger.error(f"Error analyzing genre trends: {e}")
            return {'error': str(e)}
    
    def _analyze_artist_opportunities(self) -> Dict[str, Any]:
        """Analyze artist development opportunities."""
        logger.info("Analyzing artist development opportunities...")
        
        try:
            with self.db_manager.get_session() as session:
                # Find artists with potential for growth
                # Criteria: Good chart performance but limited genre diversity
                
                # Get artists with chart success
                chart_successful = session.query(
                    Artists.artist_id,
                    Artists.artist_name,
                    Artists.total_songs,
                    Artists.total_weeks_on_chart,
                    Artists.number_one_hits,
                    Artists.top_10_hits
                ).filter(
                    Artists.total_weeks_on_chart > 10,
                    Artists.top_10_hits > 0
                ).order_by(
                    Artists.total_weeks_on_chart.desc()
                ).limit(100).all()
                
                opportunities = []
                
                for artist in chart_successful:
                    # Check genre diversity
                    genre_count = session.query(func.count(Genres.genre_id)).join(
                        SongGenres, Genres.genre_id == SongGenres.genre_id
                    ).join(
                        Songs, SongGenres.song_id == Songs.song_id
                    ).filter(
                        Songs.artist_name == artist.artist_name
                    ).scalar() or 0
                    
                    # Check for crossover potential
                    crossover_score = self._calculate_crossover_score(session, artist.artist_name)
                    
                    # Calculate opportunity score
                    opportunity_score = (
                        (artist.total_weeks_on_chart / 100) * 0.4 +  # Chart success weight
                        (artist.top_10_hits / 10) * 0.3 +  # Hit potential weight
                        (crossover_score) * 0.3  # Crossover potential weight
                    )
                    
                    if opportunity_score > 0.3:  # Threshold for opportunities
                        opportunities.append({
                            'artist_id': artist.artist_id,
                            'artist_name': artist.artist_name,
                            'total_songs': artist.total_songs,
                            'total_weeks': artist.total_weeks_on_chart,
                            'top_10_hits': artist.top_10_hits,
                            'genre_diversity': genre_count,
                            'crossover_score': crossover_score,
                            'opportunity_score': opportunity_score,
                            'recommendations': self._generate_artist_recommendations(
                                artist.artist_name, genre_count, crossover_score
                            )
                        })
                
                # Sort by opportunity score
                opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)
                
                return {
                    'high_potential_artists': opportunities[:20],  # Top 20 opportunities
                    'total_opportunities': len(opportunities),
                    'analysis_criteria': {
                        'min_chart_weeks': 10,
                        'min_top_10_hits': 1,
                        'opportunity_threshold': 0.3
                    }
                }
                
        except Exception as e:
            logger.error(f"Error analyzing artist opportunities: {e}")
            return {'error': str(e)}
    
    def _analyze_crossover_potential(self) -> Dict[str, Any]:
        """Analyze crossover potential between genres."""
        logger.info("Analyzing crossover potential...")
        
        try:
            with self.db_manager.get_session() as session:
                # Find artists with multiple genre classifications
                multi_genre_artists = session.query(
                    Songs.artist_name,
                    func.count(func.distinct(Genres.name)).label('genre_count'),
                    func.count(Songs.song_id).label('song_count')
                ).join(
                    SongGenres, Songs.song_id == SongGenres.song_id
                ).join(
                    Genres, SongGenres.genre_id == Genres.genre_id
                ).group_by(
                    Songs.artist_name
                ).having(
                    func.count(func.distinct(Genres.name)) > 1
                ).order_by(
                    func.count(func.distinct(Genres.name)).desc()
                ).limit(50).all()
                
                crossover_analysis = []
                
                for artist_name, genre_count, song_count in multi_genre_artists:
                    # Get genre combinations for this artist
                    genre_combinations = session.query(
                        Genres.name
                    ).join(
                        SongGenres, Genres.genre_id == SongGenres.genre_id
                    ).join(
                        Songs, SongGenres.song_id == Songs.song_id
                    ).filter(
                        Songs.artist_name == artist_name
                    ).distinct().all()
                    
                    genres = [g.name for g in genre_combinations]
                    
                    # Calculate crossover potential
                    crossover_score = self._calculate_genre_crossover_score(genres)
                    
                    crossover_analysis.append({
                        'artist_name': artist_name,
                        'genre_count': genre_count,
                        'song_count': song_count,
                        'genres': genres,
                        'crossover_score': crossover_score,
                        'crossover_potential': 'high' if crossover_score > 0.7 else 'medium' if crossover_score > 0.4 else 'low'
                    })
                
                # Sort by crossover score
                crossover_analysis.sort(key=lambda x: x['crossover_score'], reverse=True)
                
                # Analyze genre pair combinations
                genre_pairs = defaultdict(int)
                for artist in crossover_analysis:
                    genres = artist['genres']
                    for i in range(len(genres)):
                        for j in range(i + 1, len(genres)):
                            pair = tuple(sorted([genres[i], genres[j]]))
                            genre_pairs[pair] += 1
                
                # Get most common genre pairs
                common_pairs = sorted(genre_pairs.items(), key=lambda x: x[1], reverse=True)[:20]
                
                return {
                    'crossover_artists': crossover_analysis[:30],  # Top 30 crossover artists
                    'common_genre_pairs': [{'pair': pair, 'frequency': freq} for pair, freq in common_pairs],
                    'total_crossover_artists': len(crossover_analysis),
                    'analysis_metrics': {
                        'min_genres': 2,
                        'crossover_thresholds': {'high': 0.7, 'medium': 0.4, 'low': 0.0}
                    }
                }
                
        except Exception as e:
            logger.error(f"Error analyzing crossover potential: {e}")
            return {'error': str(e)}
    
    def _analyze_producer_effectiveness(self) -> Dict[str, Any]:
        """Analyze producer and songwriter effectiveness."""
        logger.info("Analyzing producer/songwriter effectiveness...")
        
        try:
            with self.db_manager.get_session() as session:
                # Get producer effectiveness
                producer_stats = session.query(
                    Credits.credit_name,
                    CreditRoles.role_name,
                    func.count(Songs.song_id).label('song_count'),
                    func.avg(Songs.peak_position).label('avg_peak_position'),
                    func.sum(Songs.weeks_on_chart).label('total_weeks')
                ).join(
                    SongCredits, Credits.credit_id == SongCredits.credit_id
                ).join(
                    CreditRoles, Credits.role_id == CreditRoles.role_id
                ).join(
                    Songs, SongCredits.song_id == Songs.song_id
                ).filter(
                    CreditRoles.role_name.in_(['Producer', 'Executive Producer', 'Co-Producer'])
                ).group_by(
                    Credits.credit_name, CreditRoles.role_name
                ).having(
                    func.count(Songs.song_id) >= 3  # Minimum 3 songs
                ).order_by(
                    func.count(Songs.song_id).desc()
                ).limit(50).all()
                
                # Get songwriter effectiveness
                songwriter_stats = session.query(
                    Credits.credit_name,
                    CreditRoles.role_name,
                    func.count(Songs.song_id).label('song_count'),
                    func.avg(Songs.peak_position).label('avg_peak_position'),
                    func.sum(Songs.weeks_on_chart).label('total_weeks')
                ).join(
                    SongCredits, Credits.credit_id == SongCredits.credit_id
                ).join(
                    CreditRoles, Credits.role_id == CreditRoles.role_id
                ).join(
                    Songs, SongCredits.song_id == Songs.song_id
                ).filter(
                    CreditRoles.role_name.in_(['Songwriter', 'Composer', 'Lyricist'])
                ).group_by(
                    Credits.credit_name, CreditRoles.role_name
                ).having(
                    func.count(Songs.song_id) >= 3  # Minimum 3 songs
                ).order_by(
                    func.count(Songs.song_id).desc()
                ).limit(50).all()
                
                # Process producer effectiveness
                producer_effectiveness = []
                for credit_name, role_name, song_count, avg_peak, total_weeks in producer_stats:
                    effectiveness_score = self._calculate_effectiveness_score(
                        song_count, avg_peak, total_weeks
                    )
                    
                    producer_effectiveness.append({
                        'credit_name': credit_name,
                        'role_name': role_name,
                        'song_count': song_count,
                        'avg_peak_position': avg_peak,
                        'total_weeks': total_weeks,
                        'effectiveness_score': effectiveness_score,
                        'effectiveness_rating': 'high' if effectiveness_score > 0.7 else 'medium' if effectiveness_score > 0.4 else 'low'
                    })
                
                # Process songwriter effectiveness
                songwriter_effectiveness = []
                for credit_name, role_name, song_count, avg_peak, total_weeks in songwriter_stats:
                    effectiveness_score = self._calculate_effectiveness_score(
                        song_count, avg_peak, total_weeks
                    )
                    
                    songwriter_effectiveness.append({
                        'credit_name': credit_name,
                        'role_name': role_name,
                        'song_count': song_count,
                        'avg_peak_position': avg_peak,
                        'total_weeks': total_weeks,
                        'effectiveness_score': effectiveness_score,
                        'effectiveness_rating': 'high' if effectiveness_score > 0.7 else 'medium' if effectiveness_score > 0.4 else 'low'
                    })
                
                return {
                    'top_producers': producer_effectiveness[:20],
                    'top_songwriters': songwriter_effectiveness[:20],
                    'producer_count': len(producer_effectiveness),
                    'songwriter_count': len(songwriter_effectiveness),
                    'analysis_criteria': {
                        'min_songs': 3,
                        'effectiveness_thresholds': {'high': 0.7, 'medium': 0.4, 'low': 0.0}
                    }
                }
                
        except Exception as e:
            logger.error(f"Error analyzing producer effectiveness: {e}")
            return {'error': str(e)}
    
    def _analyze_chart_patterns(self) -> Dict[str, Any]:
        """Analyze chart performance patterns."""
        logger.info("Analyzing chart performance patterns...")
        
        try:
            with self.db_manager.get_session() as session:
                # Analyze chart performance by genre
                genre_chart_performance = session.query(
                    Genres.name,
                    func.count(Songs.song_id).label('song_count'),
                    func.avg(Songs.peak_position).label('avg_peak_position'),
                    func.avg(Songs.weeks_on_chart).label('avg_weeks_on_chart'),
                    func.sum(Songs.weeks_on_chart).label('total_weeks')
                ).join(
                    SongGenres, Genres.genre_id == SongGenres.genre_id
                ).join(
                    Songs, SongGenres.song_id == Songs.song_id
                ).group_by(
                    Genres.name
                ).having(
                    func.count(Songs.song_id) >= 5  # Minimum 5 songs
                ).order_by(
                    func.avg(Songs.peak_position).asc()  # Best peak position first
                ).all()
                
                # Analyze seasonal patterns
                seasonal_patterns = session.query(
                    func.extract('month', WeeklyCharts.chart_date).label('month'),
                    func.count(WeeklyCharts.entry_id).label('entry_count'),
                    func.avg(WeeklyCharts.position).label('avg_position')
                ).group_by(
                    func.extract('month', WeeklyCharts.chart_date)
                ).order_by(
                    func.extract('month', WeeklyCharts.chart_date)
                ).all()
                
                # Process genre chart performance
                genre_performance = []
                for genre_name, song_count, avg_peak, avg_weeks, total_weeks in genre_chart_performance:
                    performance_score = self._calculate_genre_performance_score(
                        song_count, avg_peak, avg_weeks
                    )
                    
                    genre_performance.append({
                        'genre': genre_name,
                        'song_count': song_count,
                        'avg_peak_position': avg_peak,
                        'avg_weeks_on_chart': avg_weeks,
                        'total_weeks': total_weeks,
                        'performance_score': performance_score,
                        'performance_rating': 'high' if performance_score > 0.7 else 'medium' if performance_score > 0.4 else 'low'
                    })
                
                # Process seasonal patterns
                seasonal_data = []
                for month, entry_count, avg_position in seasonal_patterns:
                    seasonal_data.append({
                        'month': int(month),
                        'month_name': self._get_month_name(int(month)),
                        'entry_count': entry_count,
                        'avg_position': avg_position
                    })
                
                return {
                    'genre_performance': genre_performance,
                    'seasonal_patterns': seasonal_data,
                    'total_genres_analyzed': len(genre_performance),
                    'analysis_period': 'All available data'
                }
                
        except Exception as e:
            logger.error(f"Error analyzing chart patterns: {e}")
            return {'error': str(e)}
    
    def _generate_market_insights(self) -> Dict[str, Any]:
        """Generate overall market insights."""
        logger.info("Generating market insights...")
        
        try:
            with self.db_manager.get_session() as session:
                # Get overall database statistics
                total_artists = session.query(func.count(Artists.artist_id)).scalar()
                total_songs = session.query(func.count(Songs.song_id)).scalar()
                total_genres = session.query(func.count(Genres.genre_id)).scalar()
                
                # Get chart statistics
                chart_entries = session.query(func.count(WeeklyCharts.entry_id)).scalar()
                unique_chart_dates = session.query(func.count(func.distinct(WeeklyCharts.chart_date))).scalar()
                
                # Get credit statistics
                total_credits = session.query(func.count(Credits.credit_id)).scalar()
                total_song_credits = session.query(func.count(SongCredits.song_credit_id)).scalar()
                
                # Calculate market concentration
                # Top 10% of artists by chart weeks
                top_artists = session.query(Artists.artist_name, Artists.total_weeks_on_chart).order_by(
                    Artists.total_weeks_on_chart.desc()
                ).limit(int(total_artists * 0.1)).all()
                
                top_artist_weeks = sum(artist.total_weeks_on_chart for artist in top_artists)
                total_weeks = session.query(func.sum(Artists.total_weeks_on_chart)).scalar() or 0
                
                market_concentration = (top_artist_weeks / total_weeks * 100) if total_weeks > 0 else 0
                
                # Genre diversity analysis
                genre_distribution = session.query(
                    Genres.name,
                    func.count(SongGenres.song_id).label('song_count')
                ).join(
                    SongGenres, Genres.genre_id == SongGenres.genre_id
                ).group_by(
                    Genres.name
                ).order_by(
                    func.count(SongGenres.song_id).desc()
                ).limit(20).all()
                
                return {
                    'database_statistics': {
                        'total_artists': total_artists,
                        'total_songs': total_songs,
                        'total_genres': total_genres,
                        'chart_entries': chart_entries,
                        'unique_chart_dates': unique_chart_dates,
                        'total_credits': total_credits,
                        'total_song_credits': total_song_credits
                    },
                    'market_concentration': {
                        'top_10_percent_share': market_concentration,
                        'concentration_level': 'high' if market_concentration > 50 else 'medium' if market_concentration > 30 else 'low'
                    },
                    'genre_diversity': {
                        'top_genres': [{'genre': name, 'song_count': count} for name, count in genre_distribution],
                        'total_genres': total_genres
                    },
                    'market_insights': {
                        'diversity_score': self._calculate_diversity_score(genre_distribution),
                        'competition_level': 'high' if market_concentration < 30 else 'medium' if market_concentration < 50 else 'low',
                        'growth_potential': 'high' if total_genres > 50 else 'medium' if total_genres > 20 else 'low'
                    }
                }
                
        except Exception as e:
            logger.error(f"Error generating market insights: {e}")
            return {'error': str(e)}
    
    def _calculate_crossover_score(self, session, artist_name: str) -> float:
        """Calculate crossover potential score for an artist."""
        try:
            # Get genres for this artist
            genres = session.query(Genres.name).join(
                SongGenres, Genres.genre_id == SongGenres.genre_id
            ).join(
                Songs, SongGenres.song_id == Songs.song_id
            ).filter(
                Songs.artist_name == artist_name
            ).distinct().all()
            
            genre_list = [g.name for g in genres]
            return self._calculate_genre_crossover_score(genre_list)
            
        except Exception as e:
            logger.warning(f"Error calculating crossover score for {artist_name}: {e}")
            return 0.0
    
    def _calculate_genre_crossover_score(self, genres: List[str]) -> float:
        """Calculate crossover score based on genre combinations."""
        if len(genres) < 2:
            return 0.0
        
        # Define genre compatibility matrix
        compatibility_matrix = {
            ('pop', 'hip-hop'): 0.8,
            ('pop', 'r&b'): 0.9,
            ('pop', 'country'): 0.6,
            ('pop', 'rock'): 0.7,
            ('hip-hop', 'r&b'): 0.9,
            ('hip-hop', 'electronic'): 0.7,
            ('rock', 'alternative'): 0.8,
            ('country', 'folk'): 0.8,
            ('electronic', 'pop'): 0.8,
            ('latin', 'pop'): 0.7,
            ('latin', 'hip-hop'): 0.6
        }
        
        # Calculate average compatibility
        total_compatibility = 0.0
        pair_count = 0
        
        for i in range(len(genres)):
            for j in range(i + 1, len(genres)):
                pair = tuple(sorted([genres[i].lower(), genres[j].lower()]))
                compatibility = compatibility_matrix.get(pair, 0.3)  # Default compatibility
                total_compatibility += compatibility
                pair_count += 1
        
        return total_compatibility / pair_count if pair_count > 0 else 0.0
    
    def _calculate_effectiveness_score(self, song_count: int, avg_peak: float, total_weeks: int) -> float:
        """Calculate effectiveness score for producers/songwriters."""
        if song_count == 0:
            return 0.0
        
        # Normalize metrics (higher is better for all)
        peak_score = max(0, (101 - avg_peak) / 100)  # Convert peak position to score
        weeks_score = min(1.0, total_weeks / (song_count * 20))  # Normalize weeks per song
        count_score = min(1.0, song_count / 50)  # Normalize song count
        
        # Weighted combination
        effectiveness = (peak_score * 0.5 + weeks_score * 0.3 + count_score * 0.2)
        return min(1.0, effectiveness)
    
    def _calculate_genre_performance_score(self, song_count: int, avg_peak: float, avg_weeks: float) -> float:
        """Calculate performance score for genres."""
        if song_count == 0:
            return 0.0
        
        # Normalize metrics
        peak_score = max(0, (101 - avg_peak) / 100)  # Convert peak position to score
        weeks_score = min(1.0, avg_weeks / 20)  # Normalize average weeks
        count_score = min(1.0, song_count / 100)  # Normalize song count
        
        # Weighted combination
        performance = (peak_score * 0.4 + weeks_score * 0.4 + count_score * 0.2)
        return min(1.0, performance)
    
    def _calculate_diversity_score(self, genre_distribution: List[Tuple[str, int]]) -> float:
        """Calculate genre diversity score."""
        if not genre_distribution:
            return 0.0
        
        total_songs = sum(count for _, count in genre_distribution)
        if total_songs == 0:
            return 0.0
        
        # Calculate entropy (diversity measure)
        entropy = 0.0
        for _, count in genre_distribution:
            if count > 0:
                p = count / total_songs
                entropy -= p * (p.bit_length() - 1)  # log2 approximation
        
        # Normalize to 0-1 scale
        max_entropy = (len(genre_distribution) * (1/len(genre_distribution)) * 
                      (1/len(genre_distribution)).bit_length() - 1) if len(genre_distribution) > 1 else 0
        
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _generate_artist_recommendations(self, artist_name: str, genre_count: int, crossover_score: float) -> List[str]:
        """Generate recommendations for artist development."""
        recommendations = []
        
        if genre_count < 2:
            recommendations.append("Consider genre diversification to expand market reach")
        
        if crossover_score > 0.6:
            recommendations.append("High crossover potential - consider cross-genre collaborations")
        
        if crossover_score < 0.3:
            recommendations.append("Focus on genre-specific marketing and audience development")
        
        if genre_count > 5:
            recommendations.append("High genre diversity - consider consolidating brand identity")
        
        return recommendations
    
    def _get_month_name(self, month: int) -> str:
        """Get month name from number."""
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        return months[month - 1] if 1 <= month <= 12 else 'Unknown'
    
    def save_insights(self, output_file: Optional[Path] = None):
        """Save insights to JSON file."""
        if output_file is None:
            output_file = project_root / 'results' / 'ar_insights.json'
        
        output_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(output_file, 'w') as f:
                json.dump(self.insights, f, indent=2, default=str)
            
            logger.info(f"A&R insights saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Error saving insights: {e}")
    
    def print_summary(self):
        """Print insights summary."""
        logger.info("=" * 60)
        logger.info("A&R INSIGHTS SUMMARY")
        logger.info("=" * 60)
        
        # Genre Trends
        if 'genre_trends' in self.insights and 'emerging_genres' in self.insights['genre_trends']:
            emerging = self.insights['genre_trends']['emerging_genres']
            logger.info(f"Emerging Genres: {len(emerging)} identified")
            for genre in emerging[:5]:
                logger.info(f"  - {genre['genre']}: {genre['trend_strength']:.2f} trend strength")
        
        # Artist Opportunities
        if 'artist_opportunities' in self.insights and 'high_potential_artists' in self.insights['artist_opportunities']:
            opportunities = self.insights['artist_opportunities']['high_potential_artists']
            logger.info(f"Artist Opportunities: {len(opportunities)} identified")
            for artist in opportunities[:5]:
                logger.info(f"  - {artist['artist_name']}: {artist['opportunity_score']:.2f} opportunity score")
        
        # Crossover Analysis
        if 'crossover_analysis' in self.insights and 'crossover_artists' in self.insights['crossover_analysis']:
            crossover = self.insights['crossover_analysis']['crossover_artists']
            logger.info(f"Crossover Artists: {len(crossover)} identified")
            for artist in crossover[:5]:
                logger.info(f"  - {artist['artist_name']}: {artist['crossover_score']:.2f} crossover score")
        
        # Producer Effectiveness
        if 'producer_effectiveness' in self.insights and 'top_producers' in self.insights['producer_effectiveness']:
            producers = self.insights['producer_effectiveness']['top_producers']
            logger.info(f"Top Producers: {len(producers)} analyzed")
            for producer in producers[:3]:
                logger.info(f"  - {producer['credit_name']}: {producer['effectiveness_score']:.2f} effectiveness")
        
        logger.info("=" * 60)

def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='A&R Insights Analyzer')
    parser.add_argument('--output', type=str, help='Output file for insights')
    parser.add_argument('--summary', action='store_true', help='Print summary only')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = ARInsightsAnalyzer()
    
    # Generate insights
    insights = analyzer.generate_comprehensive_insights()
    
    # Save results
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = None
    
    analyzer.save_insights(output_file)
    
    # Print summary
    if args.summary:
        analyzer.print_summary()

if __name__ == "__main__":
    main()
