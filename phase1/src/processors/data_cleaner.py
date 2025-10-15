"""
Data cleaning and normalization module for Billboard Hot 100 data.

This module handles data cleaning, normalization, and quality assurance.
"""

import logging
import re
from datetime import date, datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
import unicodedata

from utils.config import get_config, Constants

# Configure logging
logger = logging.getLogger(__name__)


class DataCleaner:
    """Handles data cleaning and normalization operations."""
    
    def __init__(self):
        """Initialize the data cleaner with configuration."""
        self.config = get_config()
        self.artist_aliases = {}
        self.song_aliases = {}
        self._load_normalization_rules()
    
    def clean_billboard_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean and normalize a list of Billboard entries.
        
        Args:
            entries: List of raw Billboard entry dictionaries
            
        Returns:
            List of cleaned entry dictionaries
        """
        logger.info(f"Starting data cleaning for {len(entries)} entries")
        
        cleaned_entries = []
        stats = {
            'total_processed': 0,
            'cleaned': 0,
            'skipped': 0,
            'errors': 0
        }
        
        for entry in entries:
            stats['total_processed'] += 1
            
            try:
                cleaned_entry = self._clean_single_entry(entry)
                if cleaned_entry:
                    cleaned_entries.append(cleaned_entry)
                    stats['cleaned'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                logger.error(f"Error cleaning entry: {e}")
                stats['errors'] += 1
        
        logger.info(f"Data cleaning completed: {stats}")
        return cleaned_entries
    
    def _clean_single_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Clean a single Billboard entry.
        
        Args:
            entry: Raw entry dictionary
            
        Returns:
            Cleaned entry dictionary or None if entry should be skipped
        """
        # Clean song name
        song_name = self._clean_song_name(entry.get('song_name', ''))
        if not song_name:
            logger.warning("Skipping entry with empty song name")
            return None
        
        # Clean artist name
        artist_name = self._clean_artist_name(entry.get('artist_name', ''))
        if not artist_name:
            logger.warning("Skipping entry with empty artist name")
            return None
        
        # Clean and validate positions
        current_position = self._clean_position(entry.get('current_position'))
        last_week_position = self._clean_position(entry.get('last_week_position'))
        peak_position = self._clean_position(entry.get('peak_position'))
        
        if not self._validate_positions(current_position, last_week_position, peak_position):
            logger.warning(f"Skipping entry with invalid positions: {entry}")
            return None
        
        # Clean weeks on chart
        weeks_on_chart = self._clean_weeks_on_chart(entry.get('weeks_on_chart', 1))
        if not weeks_on_chart:
            logger.warning("Skipping entry with invalid weeks on chart")
            return None
        
        # Clean chart date
        chart_date = self._clean_chart_date(entry.get('chart_date'), entry.get('year'))
        if not chart_date:
            logger.warning("Skipping entry with invalid chart date")
            return None
        
        # Create cleaned entry
        cleaned_entry = {
            'song_name': song_name,
            'artist_name': artist_name,
            'current_position': current_position,
            'last_week_position': last_week_position,
            'peak_position': peak_position,
            'weeks_on_chart': weeks_on_chart,
            'chart_date': chart_date,
            'year': chart_date.year
        }
        
        # Add calculated fields
        cleaned_entry.update(self._calculate_derived_fields(cleaned_entry))
        
        return cleaned_entry
    
    def _clean_song_name(self, song_name: str) -> str:
        """
        Clean and normalize song name.
        
        Args:
            song_name: Raw song name
            
        Returns:
            Cleaned song name
        """
        if not song_name:
            return ""
        
        # Basic text cleaning
        cleaned = self._normalize_text(song_name)
        
        # Remove common prefixes/suffixes
        cleaned = self._remove_song_prefixes(cleaned)
        
        # Normalize punctuation
        cleaned = self._normalize_punctuation(cleaned)
        
        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
    
    def _clean_artist_name(self, artist_name: str) -> str:
        """
        Clean and normalize artist name.
        
        Args:
            artist_name: Raw artist name
            
        Returns:
            Cleaned artist name
        """
        if not artist_name:
            return ""
        
        # Basic text cleaning
        cleaned = self._normalize_text(artist_name)
        
        # Handle featured artists and collaborations
        cleaned = self._normalize_collaborations(cleaned)
        
        # Remove common artist prefixes/suffixes
        cleaned = self._remove_artist_prefixes(cleaned)
        
        # Normalize punctuation
        cleaned = self._normalize_punctuation(cleaned)
        
        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text by removing special characters and standardizing format.
        
        Args:
            text: Raw text string
            
        Returns:
            Normalized text string
        """
        if not text:
            return ""
        
        # Convert to Unicode and normalize
        text = unicodedata.normalize('NFKD', text)
        
        # Remove control characters
        text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C')
        
        # Convert to lowercase for processing
        text = text.lower()
        
        return text
    
    def _remove_song_prefixes(self, song_name: str) -> str:
        """
        Remove common prefixes from song names.
        
        Args:
            song_name: Song name to clean
            
        Returns:
            Cleaned song name
        """
        prefixes_to_remove = [
            r'^the\s+',
            r'^a\s+',
            r'^an\s+',
            r'^\(.*?\)\s*',  # Remove parenthetical content at start
            r'^\[.*?\]\s*',  # Remove bracketed content at start
        ]
        
        cleaned = song_name
        for prefix_pattern in prefixes_to_remove:
            cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _remove_artist_prefixes(self, artist_name: str) -> str:
        """
        Remove common prefixes from artist names.
        
        Args:
            artist_name: Artist name to clean
            
        Returns:
            Cleaned artist name
        """
        prefixes_to_remove = [
            r'^the\s+',
            r'^a\s+',
            r'^an\s+',
        ]
        
        cleaned = artist_name
        for prefix_pattern in prefixes_to_remove:
            cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _normalize_collaborations(self, artist_name: str) -> str:
        """
        Normalize artist collaborations and featured artists.
        
        Args:
            artist_name: Artist name to normalize
            
        Returns:
            Normalized artist name
        """
        # Common collaboration patterns
        collaboration_patterns = [
            (r'\s+feat\.?\s+', ' feat. '),
            (r'\s+ft\.?\s+', ' feat. '),
            (r'\s+featuring\s+', ' feat. '),
            (r'\s+&\s+', ' & '),
            (r'\s+and\s+', ' & '),
            (r'\s+with\s+', ' feat. '),
        ]
        
        cleaned = artist_name
        for pattern, replacement in collaboration_patterns:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _normalize_punctuation(self, text: str) -> str:
        """
        Normalize punctuation in text.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Replace various quote types with standard quotes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"[''']", "'", text)
        
        # Normalize dashes
        text = re.sub(r'[–—]', '-', text)
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _clean_position(self, position: Any) -> Optional[int]:
        """
        Clean and validate chart position.
        
        Args:
            position: Raw position value
            
        Returns:
            Cleaned position integer or None if invalid
        """
        if position is None:
            return None
        
        try:
            pos = int(position)
            if Constants.MIN_POSITION <= pos <= Constants.MAX_POSITION:
                return pos
            else:
                logger.warning(f"Position {pos} out of valid range")
                return None
        except (ValueError, TypeError):
            logger.warning(f"Invalid position value: {position}")
            return None
    
    def _clean_weeks_on_chart(self, weeks: Any) -> Optional[int]:
        """
        Clean and validate weeks on chart.
        
        Args:
            weeks: Raw weeks value
            
        Returns:
            Cleaned weeks integer or None if invalid
        """
        if weeks is None:
            return 1  # Default to 1 week
        
        try:
            weeks_int = int(weeks)
            if Constants.MIN_WEEKS_ON_CHART <= weeks_int <= Constants.MAX_WEEKS_ON_CHART:
                return weeks_int
            else:
                logger.warning(f"Weeks on chart {weeks_int} out of valid range")
                return None
        except (ValueError, TypeError):
            logger.warning(f"Invalid weeks on chart value: {weeks}")
            return None
    
    def _clean_chart_date(self, chart_date: Any, year: int) -> Optional[date]:
        """
        Clean and validate chart date.
        
        Args:
            chart_date: Raw chart date
            year: Year as fallback
            
        Returns:
            Cleaned date object or None if invalid
        """
        if chart_date is None:
            # Use default date for the year
            return date(year, 1, 1)
        
        if isinstance(chart_date, date):
            return chart_date
        
        if isinstance(chart_date, datetime):
            return chart_date.date()
        
        if isinstance(chart_date, str):
            try:
                # Try common date formats
                for date_format in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                    try:
                        parsed_date = datetime.strptime(chart_date, date_format).date()
                        if Constants.MIN_YEAR <= parsed_date.year <= Constants.MAX_YEAR:
                            return parsed_date
                    except ValueError:
                        continue
                
                logger.warning(f"Could not parse chart date: {chart_date}")
                return date(year, 1, 1)
                
            except Exception as e:
                logger.warning(f"Error parsing chart date {chart_date}: {e}")
                return date(year, 1, 1)
        
        logger.warning(f"Invalid chart date type: {type(chart_date)}")
        return date(year, 1, 1)
    
    def _validate_positions(self, current: int, last_week: Optional[int], peak: int) -> bool:
        """
        Validate position relationships.
        
        Args:
            current: Current position
            last_week: Last week's position
            peak: Peak position
            
        Returns:
            True if positions are valid, False otherwise
        """
        # Peak position should be the best (lowest number)
        if peak > current:
            logger.warning(f"Peak position {peak} is worse than current position {current}")
            return False
        
        # If last week position exists, it should be reasonable
        if last_week is not None:
            if last_week < 1 or last_week > 100:
                logger.warning(f"Invalid last week position: {last_week}")
                return False
        
        return True
    
    def _calculate_derived_fields(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate derived fields for an entry.
        
        Args:
            entry: Entry dictionary
            
        Returns:
            Dictionary with derived fields
        """
        derived = {}
        
        # Calculate position change
        if entry.get('last_week_position') is not None:
            derived['position_change'] = entry['current_position'] - entry['last_week_position']
        else:
            derived['position_change'] = None
        
        # Determine if it's a new entry
        derived['is_new_entry'] = 1 if entry.get('last_week_position') is None else 0
        
        return derived
    
    def _load_normalization_rules(self):
        """Load normalization rules for artists and songs."""
        # This could be expanded to load from external files
        # For now, we'll use hardcoded rules
        self.artist_aliases = {
            'the beatles': 'beatles',
            'the rolling stones': 'rolling stones',
            'elvis presley': 'elvis',
            'michael jackson': 'michael jackson',
            'madonna': 'madonna',
        }
        
        self.song_aliases = {
            'i want to hold your hand': 'i want to hold your hand',
            'hey jude': 'hey jude',
            'satisfaction': 'satisfaction',
        }
    
    def detect_duplicates(self, entries: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
        """
        Detect potential duplicate entries.
        
        Args:
            entries: List of entry dictionaries
            
        Returns:
            List of tuples containing indices of potential duplicates
        """
        duplicates = []
        
        # Group entries by song and artist
        entry_groups = defaultdict(list)
        for i, entry in enumerate(entries):
            key = (entry['song_name'].lower(), entry['artist_name'].lower())
            entry_groups[key].append(i)
        
        # Find groups with multiple entries
        for key, indices in entry_groups.items():
            if len(indices) > 1:
                # Check if they're actually duplicates (same date)
                for i in range(len(indices)):
                    for j in range(i + 1, len(indices)):
                        idx1, idx2 = indices[i], indices[j]
                        if entries[idx1]['chart_date'] == entries[idx2]['chart_date']:
                            duplicates.append((idx1, idx2))
        
        return duplicates
    
    def generate_quality_report(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a data quality report.
        
        Args:
            entries: List of entry dictionaries
            
        Returns:
            Dictionary containing quality metrics
        """
        if not entries:
            return {'error': 'No entries to analyze'}
        
        report = {
            'total_entries': len(entries),
            'date_range': {
                'earliest': min(entry['chart_date'] for entry in entries),
                'latest': max(entry['chart_date'] for entry in entries)
            },
            'year_distribution': Counter(entry['year'] for entry in entries),
            'position_distribution': Counter(entry['current_position'] for entry in entries),
            'artists_count': len(set(entry['artist_name'] for entry in entries)),
            'songs_count': len(set(entry['song_name'] for entry in entries)),
            'new_entries': sum(1 for entry in entries if entry.get('is_new_entry', 0) == 1),
            'missing_last_week': sum(1 for entry in entries if entry.get('last_week_position') is None),
            'duplicates': len(self.detect_duplicates(entries))
        }
        
        return report
