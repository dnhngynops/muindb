#!/usr/bin/env python3
"""
Enhanced Genius Search Module with ARI-style Improvements
Drop-in enhancement for existing GeniusClient
"""

import re
import logging
from typing import List
from fuzzywuzzy import fuzz

logger = logging.getLogger(__name__)


class EnhancedGeniusSearch:
    """
    Mixin class that adds ARI-style search enhancements to GeniusClient
    Can be used to enhance existing GeniusClient without breaking compatibility
    """
    
    # Title cleaning patterns (from ARI)
    TITLE_CLEANING_PATTERNS = [
        # Featuring/collaboration patterns
        r'\s*\(with\s+[^)]+\)',           # (with Travis Scott)
        r'\s*\(feat\.?\s+[^)]+\)',        # (feat. Artist) or (feat Artist)
        r'\s*\(featuring\s+[^)]+\)',      # (featuring Artist)
        r'\s*\(ft\.?\s+[^)]+\)',          # (ft. Artist) or (ft Artist)
        r'\s*\(f/\s+[^)]+\)',             # (f/ Artist)
        r'\s*\(x\s+[^)]+\)',              # (x Artist)
        
        # Version/remaster patterns
        r'\s*-\s*Remastered[^-]*$',
        r'\s*\(Remastered[^)]*\)',
        r'\s*-\s*[^-]*Remaster[^-]*$',
        r'\s*-\s*[^-]*Version[^-]*$',
        r'\s*\([^)]*Version[^)]*\)',
        r'\s*-\s*From\s+"[^"]+".+$',
        r'\s*\(From\s+"[^"]+".+\)',
        r'\s*-\s*featured\s+in.+$',
        r'\s*\(featured\s+in[^)]+\)',
        r'\s*-\s*From\s+the.+$',
        r'\s*\(From\s+the[^)]+\)',
        r'\s*-\s*[^-]*Radio[^-]*$',
        r'\s*\([^)]*Radio[^)]*\)',
        r'\s*-\s*[^-]*Mix[^-]*$',
        r'\s*\([^)]*Mix[^)]*\)'
    ]
    
    @staticmethod
    def clean_title(title: str) -> str:
        """
        Clean title for better search results using ARI's 18 patterns + censorship handling
        
        Args:
            title: Original song title
            
        Returns:
            Cleaned title without extra information
        """
        cleaned = title
        
        # Apply all cleaning patterns
        for pattern in EnhancedGeniusSearch.TITLE_CLEANING_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Handle censored words (b***h -> bitch, a** -> ass, s**t -> shit, etc.)
        cleaned = re.sub(r'\bb\*+h\b', 'bitch', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\ba\*+\b', 'ass', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bs\*+t\b', 'shit', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bf\*+k\b', 'fuck', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bn\*+a\b', 'nigga', cleaned, flags=re.IGNORECASE)
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    @staticmethod
    def generate_query_variations(title: str, artist: str) -> List[str]:
        """
        Generate multiple search query strategies (ARI's 6 strategies + censorship/punctuation handling)
        
        Args:
            title: Song title
            artist: Artist name
            
        Returns:
            List of query variations to try
        """
        clean_title = EnhancedGeniusSearch.clean_title(title)
        queries = []
        
        # Extract main artist (first listed)
        main_artist = artist.split(",")[0].split("&")[0].strip()
        
        # Also create version without apostrophes/punctuation in artist name
        main_artist_no_punct = re.sub(r"['\-\.]", '', main_artist).strip()
        
        # Strategy 1: Clean title + main artist (highest success rate)
        queries.append(f"{clean_title} {main_artist}")
        
        # Strategy 2: Clean title + all artists (handles collaborations)
        if artist != main_artist:
            queries.append(f"{clean_title} {artist}")
        
        # Strategy 3: Artist + clean title (reversed order)
        queries.append(f"{main_artist} {clean_title}")
        
        # Strategy 4: Just clean title
        queries.append(clean_title)
        
        # Strategy 5: Original title + main artist (fallback)
        if title != clean_title:
            queries.append(f"{title} {main_artist}")
        
        # Strategy 6: Simplified version (remove special characters)
        simplified_title = re.sub(r'[^\w\s]', ' ', clean_title).strip()
        simplified_title = re.sub(r'\s+', ' ', simplified_title)
        if simplified_title != clean_title:
            queries.append(f"{simplified_title} {main_artist}")
        
        # Strategy 7: Artist without punctuation + clean title (handles cam'ron -> camron)
        if main_artist_no_punct != main_artist:
            queries.append(f"{clean_title} {main_artist_no_punct}")
            queries.append(f"{main_artist_no_punct} {clean_title}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for query in queries:
            if query not in seen:
                seen.add(query)
                unique_queries.append(query)
        
        return unique_queries
    
    @staticmethod
    def is_good_match(genius_title: str, genius_artist: str, 
                     original_title: str, original_artist: str,
                     threshold: int = 70) -> bool:
        """
        Check if Genius result is a good match using fuzzy matching
        
        Args:
            genius_title: Title from Genius API
            genius_artist: Artist from Genius API
            original_title: Original search title
            original_artist: Original search artist
            threshold: Minimum similarity score (0-100)
            
        Returns:
            True if it's a good match
        """
        # Clean both titles for comparison
        genius_title_norm = EnhancedGeniusSearch.clean_title(genius_title).lower()
        original_title_norm = EnhancedGeniusSearch.clean_title(original_title).lower()
        genius_artist_norm = genius_artist.lower()
        
        # Extract main artist from original
        main_artist = original_artist.split(",")[0].split("&")[0].strip().lower()
        
        # Remove featuring info for better comparison
        genius_title_no_feat = re.sub(r'\s*\(?(feat\.|ft\.)\s+[^)]*\)?', '', 
                                      genius_title_norm, flags=re.IGNORECASE).strip()
        original_title_no_feat = re.sub(r'\s*\(?(feat\.|ft\.)\s+[^)]*\)?', '', 
                                        original_title_norm, flags=re.IGNORECASE).strip()
        
        # Calculate title similarity
        title_similarity = fuzz.ratio(genius_title_norm, original_title_norm)
        title_similarity_no_feat = fuzz.ratio(genius_title_no_feat, original_title_no_feat)
        
        best_title_similarity = max(title_similarity, title_similarity_no_feat)
        
        # Check artist match
        artist_match = (
            main_artist in genius_artist_norm or 
            genius_artist_norm in main_artist or
            fuzz.ratio(genius_artist_norm, main_artist) >= 70
        )
        
        # Match if title similarity >= threshold AND artist matches
        match_result = best_title_similarity >= threshold and artist_match
        
        if match_result:
            logger.debug(f"Good match: '{genius_title}' ({best_title_similarity}% similarity)")
        
        return match_result


# Test function
def test_enhanced_search():
    """Test the enhanced search functions"""
    print("🧪 Testing Enhanced Genius Search Functions")
    print("=" * 60)
    
    # Test title cleaning
    test_titles = [
        ("Shape of You (feat. Artist)", "Shape of You"),
        ("Sunflower (Spider-Man: Into the Spider-Verse)", "Sunflower"),
        ("Anti-Hero - Radio Edit", "Anti-Hero"),
        ("Blinding Lights - 2020 Remaster", "Blinding Lights"),
        ("As It Was (From Album)", "As It Was")
    ]
    
    print("\n📝 Testing Title Cleaning:")
    print("-" * 60)
    for original, expected in test_titles:
        cleaned = EnhancedGeniusSearch.clean_title(original)
        status = "✅" if cleaned == expected else "⚠️"
        print(f"{status} '{original}'")
        print(f"   → '{cleaned}'")
        if cleaned != expected:
            print(f"   Expected: '{expected}'")
    
    # Test query generation
    print("\n🔍 Testing Query Generation:")
    print("-" * 60)
    title = "Sunflower (Spider-Man: Into the Spider-Verse)"
    artist = "Post Malone & Swae Lee"
    queries = EnhancedGeniusSearch.generate_query_variations(title, artist)
    print(f"Title: '{title}'")
    print(f"Artist: '{artist}'")
    print(f"Generated {len(queries)} query variations:")
    for i, query in enumerate(queries, 1):
        print(f"   {i}. '{query}'")
    
    # Test fuzzy matching
    print("\n🎯 Testing Fuzzy Matching:")
    print("-" * 60)
    test_matches = [
        ("Shape of You", "Ed Sheeran", "Shape of You", "Ed Sheeran", True),
        ("Shape of You", "Ed Sheeran", "Shape Of You", "Ed Sheeran", True),
        ("Sunflower", "Post Malone", "Sunflower - Post Malone & Swae Lee", "Post Malone", True),
        ("Anti-Hero", "Taylor Swift", "Anti Hero", "Taylor Swift", True),
        ("Different Song", "Different Artist", "Shape of You", "Ed Sheeran", False)
    ]
    
    for genius_title, genius_artist, orig_title, orig_artist, expected in test_matches:
        result = EnhancedGeniusSearch.is_good_match(genius_title, genius_artist, orig_title, orig_artist)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{genius_title}' by {genius_artist}")
        print(f"   vs '{orig_title}' by {orig_artist}")
        print(f"   Result: {result} (expected: {expected})")
    
    print("\n" + "=" * 60)
    print("🎉 Enhanced search functions test complete!")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_enhanced_search()
