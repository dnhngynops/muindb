# Subgenre Duplicate Issue - Fixed

## Problem Description

When extracting detailed genres from APIs (Spotify, Last.fm, Genius), the system was saving **genre-level terms** (like "soul", "funk", "rap", "dance") as subgenres under multiple parent genres. This created semantic duplicates:

### Example of the Problem:
```
"soul" was stored as:
  • Subgenre under r&b (42 songs)     ← Makes sense
  • Subgenre under pop (12 songs)     ← Confusing
  • Subgenre under rock (7 songs)     ← Incorrect
  • Subgenre under jazz (2 songs)     ← Incorrect
  • Subgenre under other (2 songs)    ← Incorrect
```

**Root Cause:** When an artist has tags like `["neo soul", "r&b", "soul", "quiet storm"]`, the system would:
1. Map "r&b" as primary genre ✅
2. Save "neo soul", "soul", "quiet storm" as subgenres ❌

The problem: "soul" is itself a genre-level term, not a subgenre!

## What's Fixed

### 1. Updated `save_artist_subgenres()` method
**File:** `phase3/scripts/genre_classification_system.py` (lines 744-784)

**Changes:**
- Added dynamic filtering of ALL primary genre names from database
- Added static list of common genre-level terms to exclude
- Prevents genre-level terms from being saved as subgenres

**New filtering logic:**
```python
# Get all primary genre names from database
primary_genre_names = set()
all_genres = session.query(Genres.genre_name).all()
for (genre_name,) in all_genres:
    primary_genre_names.add(genre_name.lower())

# Add common genre-level terms
genre_level_terms = {
    'soul', 'blues', 'funk', 'disco', 'gospel', 'reggae',
    'punk', 'metal', 'indie', 'dance', 'edm', 'house',
    'techno', 'trance', 'dubstep', 'r&b', 'rnb',
    'rap', 'hip hop', 'hip-hop', 'country', 'folk',
    'rock', 'pop', 'jazz', 'classical', 'latin',
    'electronic', 'alternative', 'other'
}
primary_genre_names.update(genre_level_terms)

# Skip genre-level terms when saving subgenres
if classification.name.lower() in primary_genre_names:
    continue
```

### 2. Created Cleanup Script
**File:** `phase3/scripts/cleanup_duplicate_subgenres.py`

**Features:**
- Identifies genre-level terms stored as subgenres
- Shows dry-run preview before cleanup
- Removes problematic subgenre records and their links
- Provides before/after statistics

**Usage:**
```bash
# Dry run (preview)
python cleanup_duplicate_subgenres.py --db ../../data/music_database.db

# Execute cleanup
python cleanup_duplicate_subgenres.py --db ../../data/music_database.db --execute
```

## Results

### Before Cleanup:
- **Total subgenre records:** 154
- **Unique subgenre names:** 113
- **Subgenres across multiple parents:** 30
- **Total song-subgenre links:** 585
- **Problematic genre-level terms:** 20 terms across 35 records

### After Cleanup:
- **Total subgenre records:** 119 ✅ (-35)
- **Unique subgenre names:** 93 ✅ (-20)
- **Subgenres across multiple parents:** 21 ✅ (-9)
- **Total song-subgenre links:** 396 ✅ (-189)
- **Problematic genre-level terms:** 0 ✅

### Removed Terms:
Genre-level terms that were incorrectly stored as subgenres:
- soul (64 songs affected)
- rap (60 songs)
- hip hop (22 songs)
- dance (6 songs)
- rock (5 songs)
- r&b (4 songs)
- grunge (4 songs)
- funk, punk, reggae, pop (3 songs each)
- house, metal, alternative, blues, gospel, etc. (1-2 songs each)

### Legitimate Cross-Parent Subgenres (Kept):
Compound/specific terms that correctly appear under multiple parents:
- ✅ "alternative rock" (appears under rock, alternative, pop, hip-hop)
- ✅ "neo soul" / "neo-soul" (appears under r&b, hip-hop, pop)
- ✅ "nu metal" (appears under rock, hip-hop)
- ✅ "post-grunge" (appears under rock, alternative)
- ✅ "latin pop" (appears under latin, pop)
- ✅ "funk rock" (appears under rock, r&b)
- ✅ "new jack swing" (appears under r&b, jazz, other)

## Why These Are Different

| Type | Example | Valid Subgenre? | Reasoning |
|------|---------|----------------|-----------|
| **Genre-level** | soul, funk, rap | ❌ No | These are primary genres themselves |
| **Compound** | neo soul, funk rock | ✅ Yes | Combines two concepts into specific style |
| **Modified** | alternative rock, nu metal | ✅ Yes | Adds modifier to create specific subgenre |
| **Era/Style** | teen-pop, post-grunge | ✅ Yes | Indicates specific era or style variant |

## Prevention for Future

The updated code now prevents this issue going forward:

1. **Dynamic filtering:** Queries database for all primary genre names
2. **Static list:** Maintains known genre-level terms
3. **Validation:** Checks both before saving subgenres
4. **Result:** Only compound/specific terms saved as subgenres

### Example of New Behavior:

**Artist tags:** `["neo soul", "r&b", "soul", "quiet storm"]`  
**Primary genre:** r&b

**OLD behavior:**
- Save "neo soul" ✅
- Save "soul" ❌ (genre-level term)
- Save "quiet storm" ✅

**NEW behavior:**
- Save "neo soul" ✅
- Skip "soul" ✅ (filtered out as genre-level)
- Save "quiet storm" ✅

## Testing

To verify the fix is working, reprocess a year with the updated code:

```bash
cd phase3/scripts
python enrich_producer_subgenres.py --year 2000
```

Check results:
```bash
python cleanup_duplicate_subgenres.py --db ../../data/music_database.db
```

Should show: ✅ No genre-level terms found in subgenres!

## Summary

✅ **Issue identified:** Genre-level terms incorrectly stored as subgenres  
✅ **Code fixed:** Added filtering to prevent future occurrences  
✅ **Data cleaned:** Removed 35 problematic subgenre records  
✅ **Validated:** Remaining cross-parent subgenres are legitimate compound terms  
✅ **Prevention:** System now only stores true subgenre descriptors  

The subgenre system now properly distinguishes between:
- **Primary genres** (soul, funk, rap) - NOT stored as subgenres
- **Subgenres** (neo soul, funk rock, conscious rap) - Properly stored with context

