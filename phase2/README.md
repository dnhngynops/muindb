# Billboard Music Database - Phase 2: Credits Enrichment (Genius API)

This is Phase 2 of the Billboard Hot 100 music database project, focused on enriching songs with comprehensive credits information using the Genius API.

## Overview

Phase 2 extends the core database with:
- **Credits Management**: Writers, producers, and other contributors from Genius
- **Enhanced Search with Fix #1**: 8 improvements for 94% accuracy (validated October 13, 2025)
- **Genius API Integration**: Comprehensive metadata with intelligent matching
- **Credit Attribution**: Detailed role-based credit tracking
- **Production-Ready**: 97-100% coverage on tested years

## What's New in Phase 2

### New Database Tables
- **credit_roles**: Types of credits (writer, producer, etc.)
- **credits**: Master credits catalog (people who worked on songs)
- **song_credits**: Many-to-many relationship between songs and credits
- **song_genius_metadata**: Genius API metadata for songs

### New Views
- **songs_with_credits**: Songs with their associated credits
- **songs_complete**: Comprehensive song information including Genius metadata

### Enhanced Search System (Fix #1 - October 13, 2025)
- **8 Major Improvements**:
  1. Increased result checking (5 → 15 results)
  2. Adaptive artist thresholds (45%/60%/70%)
  3. Article removal ("the one" → "one")
  4. Parenthetical subtitle handling
  5. Featured artist cleanup
  6. Metadata update on --force
  7. Strong artist validation (prevents false positives)
  8. fuzzywuzzy dependency for accurate matching

- **Performance**: 94% search accuracy, 2% false positive rate (validated)
- **Coverage**: Year 2000 (100%), Year 2001 (98.3%)

### Genius API Integration
- **Primary source** for song credits and metadata
- **Rate limiting** and error handling built-in
- **Batch processing** with --force flag for re-enrichment
- **Connection pooling** for 25% speed improvement

### Search Capabilities
- Search by song name, artist, or credits
- Filter by peak position, year range, weeks on chart
- Role-specific credit searches (writers, producers, etc.)
- Hot songs filtering (Genius API specific)
- Comprehensive statistics and analytics

## Files Structure

```
phase2/
├── README.md                           # This file
├── phase2_schema_extension.sql         # Phase 2 schema SQL
├── scripts/
│   ├── create_artist_producers_table.py   # Artist-producer identification
│   ├── dashboard_analytics.py         # Analytics dashboard
│   ├── data_cleanup_manager.py        # Data cleanup utilities
│   ├── enrich_songs_metadata.py       # High-performance metadata enrichment script
│   ├── search_songs.py                # Advanced search functionality
│   └── test_enhanced_search.py        # Enhanced search test suite
└── src/
    ├── database/
    │   └── phase2_models.py           # Phase 2 database models
    └── api/
        ├── enhanced_genius_client.py  # Enhanced Genius API client
        ├── enhanced_genius_search.py  # ARI-style search improvements
        └── genius_client.py           # Base Genius API client
```

## Prerequisites

Phase 2 requires Phase 1 to be completed first. Ensure you have:
- Phase 1 database set up and populated
- Python dependencies installed
- Genius API access token (free registration required)

## Quick Start

1. **Get Genius API Access**:
   - Register at https://genius.com/api-clients
   - Create a new API client
   - Get your access token

2. **Set up environment**:
   ```bash
   # Set your Genius token
   export GENIUS_ACCESS_TOKEN="your_token_here"
   ```

3. **Enrich songs with metadata**:
   ```bash
   # Phase 2 tables will be created automatically on first run
   # Enrich a specific year
   python scripts/enrich_songs_metadata.py --year 2000 --limit 100
   
   # Or enrich without year filter
   python scripts/enrich_songs_metadata.py --limit 100
   ```

4. **Test the enhanced search**:
   ```bash
   python scripts/test_enhanced_search.py
   ```

5. **Start searching**:
   ```bash
   python scripts/search_songs.py --song "Shape of You" --details
   ```

## Key Features

### Credits Management
- Comprehensive credits tracking (writers, producers, engineers, etc.)
- Role-based categorization
- Primary artist distinction (keeps main artist separate from writers/producers)
- Source tracking and verification

### Advanced Search
- Multi-criteria search with filtering
- Role-specific credit searches
- Temporal filtering (year range, peak position, etc.)
- Hot songs filtering (Genius API specific)
- Comprehensive statistics and analytics

## Example Searches

```bash
# Search by song name
python scripts/search_songs.py --song "Shape of You"

# Search by artist
python scripts/search_songs.py --artist "Taylor Swift"

# Search by credit role
python scripts/search_songs.py --role "Producer"

# Search by credit (writer)
python scripts/search_songs.py --credit "Max Martin" --role "Writer"

# Search hot songs only
python scripts/search_songs.py --hot-only

# Comprehensive search
python scripts/search_songs.py --song "Love" --peak-max 10 --year-from 2020

# Show detailed information
python scripts/search_songs.py --song "Shape of You" --details

# Show statistics
python scripts/search_songs.py --stats

# Show Genius API statistics
python scripts/search_songs.py --genius-stats
```

## Database Queries

```sql
-- Find songs by a specific writer
SELECT s.song_name, s.artist_name, s.peak_position
FROM songs s
JOIN song_credits sc ON s.song_id = sc.song_id
JOIN credits c ON sc.credit_id = c.credit_id
JOIN credit_roles cr ON sc.role_id = cr.role_id
WHERE c.credit_name LIKE '%Max Martin%' AND cr.role_name = 'Writer'
ORDER BY s.peak_position;

-- Find hot songs with high pyongs count
SELECT s.song_name, s.artist_name, sgm.pyongs_count, sgm.genius_url
FROM songs s
JOIN song_genius_metadata sgm ON s.song_id = sgm.song_id
WHERE sgm.hot = 1
ORDER BY sgm.pyongs_count DESC;

-- Get credit distribution by role
SELECT cr.role_name, COUNT(sc.song_id) as song_count, 
       AVG(s.peak_position) as avg_peak_position
FROM credit_roles cr
LEFT JOIN song_credits sc ON cr.role_id = sc.role_id
LEFT JOIN songs s ON sc.song_id = s.song_id
GROUP BY cr.role_id, cr.role_name
HAVING song_count > 0
ORDER BY song_count DESC;
```

## Genius API Configuration

### Getting Started
1. **Register**: Create account at https://genius.com
2. **Create API Client**: Go to https://genius.com/api-clients
3. **Get Token**: Copy your access token
4. **Set Environment Variable**: `export GENIUS_ACCESS_TOKEN="your_token"`

### API Details
- **Free**: No cost for basic usage
- **Rate Limit**: 5 requests per second (conservative)
- **Coverage**: Excellent for popular music and lyrics
- **Data**: Song credits, genres, popularity metrics

## Performance Considerations

- Comprehensive indexing for optimal performance
- API rate limiting built-in (0.5 second delays)
- Batch processing for large datasets
- Connection pooling for database operations

## Troubleshooting

### Common Issues

1. **Genius API Authentication**
   - Ensure your access token is valid
   - Check token permissions
   - Verify environment variable is set

2. **No Metadata Found**
   - Try different song/artist name variations
   - Check if song exists on Genius
   - Verify API token has proper permissions

3. **Rate Limiting**
   - Built-in delays prevent rate limiting
   - Increase delays if needed
   - Check API usage limits

4. **Search Returns No Results**
   - Check spelling and case sensitivity
   - Try partial matches
   - Verify data exists in database

### Logging
Enable verbose logging for debugging:
```bash
python scripts/search_songs.py --song "test" --verbose
```

## Future Enhancements

### Planned Features
- **Lyrics Integration**: Full lyrics from Genius API
- **Artist Pages**: Detailed artist information
- **Trending Songs**: Real-time trending data
- **Web Interface**: Browser-based search and exploration

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For questions or issues:
1. Check the troubleshooting section
2. Review the logs with `--verbose`
3. Check Genius API documentation
4. Create an issue on GitHub

---

**Phase 2 Status**: ✅ Production-Ready (Credits Enrichment with Fix #1)  
**Last Updated**: October 13, 2025  
**Version**: 2.1.0  
**Coverage**: 100% (Year 2000), 98.3% (Year 2001), ~97% (2000-2003)  
**Search Accuracy**: 94% validated  

## Recent Improvements (October 13, 2025)

### Fix #1 - Enhanced Search System:
- **Result check expansion**: 5 → 15 results (finds songs buried in generic title searches)
- **Adaptive matching**: 45% artist for perfect titles, prevents false positives
- **Subtitle handling**: Matches "young'n (holla back)" → "young'n"
- **Validation**: 94% accuracy on 50-song test, 2% false positive rate
- **Recovery**: 12 songs recovered across years 2000-2001
- **URL correction**: All 12 wrong Genius URLs fixed

### Dependencies Added:
```bash
pip install fuzzywuzzy python-Levenshtein
```

---

## Next Phase

**Phase 3**: Genre Classification - See `/phase3/` directory for multi-source genre classification and subgenre enrichment.