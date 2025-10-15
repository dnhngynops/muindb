#!/usr/bin/env python3
"""
Producer Genre Specialization Patterns
Maps producers to their genre signatures based on Billboard data analysis
"""

# Producer Genre Specializations
# Based on analysis of 1,261 songs with credits (years 2000-2003)

PRODUCER_GENRE_SIGNATURES = {
    # POP SPECIALISTS (100% pop focus)
    'max martin': {
        'primary': 'pop',
        'subgenres': ['dance-pop', 'teen-pop', 'electropop'],
        'confidence': 0.95,
        'notes': 'Legendary pop producer, Britney/Backstreet Boys era'
    },
    'rami': {
        'primary': 'pop',
        'subgenres': ['dance-pop', 'electropop'],
        'confidence': 0.90,
        'notes': 'Pop specialist, works with Max Martin'
    },
    'bag & arnthor': {
        'primary': 'pop',
        'subgenres': ['dance-pop', 'teen-pop'],
        'confidence': 0.90,
        'notes': 'Scandinavian pop production team'
    },
    'kristian lundin': {
        'primary': 'pop',
        'subgenres': ['dance-pop', 'teen-pop'],
        'confidence': 0.90,
        'notes': 'Cheiron Studios, Max Martin collaborator'
    },
    
    # HIP-HOP SPECIALISTS (100% hip-hop focus)
    'the neptunes': {
        'primary': 'hip-hop',
        'subgenres': ['alternative-hip-hop', 'pop-rap', 'southern-hip-hop'],
        'confidence': 0.95,
        'notes': 'Pharrell & Chad Hugo, distinctive sound'
    },
    'mannie fresh': {
        'primary': 'hip-hop',
        'subgenres': ['southern-hip-hop', 'crunk', 'bounce'],
        'confidence': 0.95,
        'notes': 'Cash Money Records, New Orleans sound'
    },
    'dr. dre': {
        'primary': 'hip-hop',
        'subgenres': ['west-coast-hip-hop', 'g-funk', 'gangster-rap'],
        'confidence': 0.95,
        'notes': 'West coast legend, G-funk pioneer'
    },
    'swizz beatz': {
        'primary': 'hip-hop',
        'subgenres': ['east-coast-hip-hop', 'hardcore-hip-hop'],
        'confidence': 0.90,
        'notes': 'Ruff Ryders, aggressive beats'
    },
    
    # R&B SPECIALISTS
    'bryan-michael cox': {
        'primary': 'r&b',
        'subgenres': ['contemporary-r&b', 'neo-soul'],
        'confidence': 0.90,
        'notes': 'Modern R&B specialist'
    },
    'rodney jerkins': {
        'primary': 'r&b',
        'subgenres': ['contemporary-r&b', 'pop-r&b'],
        'confidence': 0.85,
        'notes': 'Darkchild, crossover R&B'
    },
    
    # HIP-HOP/R&B CROSSOVER (Versatile)
    'timbaland': {
        'primary': 'hip-hop',
        'subgenres': ['alternative-r&b', 'contemporary-r&b', 'pop-rap'],
        'confidence': 0.85,
        'notes': 'Versatile, hip-hop and R&B, futuristic sound',
        'secondary_genre': 'r&b'
    },
    'jermaine dupri': {
        'primary': 'hip-hop',
        'subgenres': ['southern-hip-hop', 'contemporary-r&b', 'pop-rap'],
        'confidence': 0.80,
        'notes': 'So So Def, hip-hop and R&B crossover',
        'secondary_genre': 'r&b'
    },
    
    # COUNTRY SPECIALISTS (100% country focus)
    'byron gallimore': {
        'primary': 'country',
        'subgenres': ['contemporary-country', 'country-pop'],
        'confidence': 0.95,
        'notes': 'Major country producer, Tim McGraw, Faith Hill'
    },
    'james stroud': {
        'primary': 'country',
        'subgenres': ['contemporary-country', 'traditional-country'],
        'confidence': 0.90,
        'notes': 'Country specialist'
    },
    'paul worley': {
        'primary': 'country',
        'subgenres': ['contemporary-country', 'bluegrass'],
        'confidence': 0.90,
        'notes': 'Country producer, Dixie Chicks'
    },
    'dann huff': {
        'primary': 'country',
        'subgenres': ['contemporary-country', 'country-rock'],
        'confidence': 0.90,
        'notes': 'Nashville sound, country-rock blend'
    },
    
    # ROCK SPECIALISTS
    'rick rubin': {
        'primary': 'rock',
        'subgenres': ['alternative-rock', 'hard-rock', 'rap-rock'],
        'confidence': 0.90,
        'notes': 'Versatile legend, raw sound'
    },
    'don gilmore': {
        'primary': 'rock',
        'subgenres': ['nu-metal', 'alternative-metal'],
        'confidence': 0.90,
        'notes': 'Nu-metal specialist, Linkin Park'
    },
}

# Genre-specific subgenre mappings for known eras
ERA_BASED_SUBGENRES = {
    'pop': {
        '2000-2004': ['teen-pop', 'dance-pop'],
        '2005-2009': ['pop-rock', 'emo-pop'],
        '2010-2015': ['electropop', 'indie-pop'],
        '2016-2020': ['alt-pop', 'bedroom-pop'],
        '2021-2025': ['hyperpop', 'alt-pop']
    },
    'hip-hop': {
        '2000-2003': ['southern-hip-hop', 'crunk'],
        '2004-2008': ['snap-music', 'ringtone-rap'],
        '2009-2012': ['blog-rap', 'conscious-hip-hop'],
        '2013-2016': ['trap', 'drill'],
        '2017-2020': ['emo-rap', 'melodic-rap'],
        '2021-2025': ['rage-rap', 'plugg']
    },
    'country': {
        '2000-2010': ['country-pop', 'contemporary-country'],
        '2011-2015': ['bro-country', 'country-pop'],
        '2016-2025': ['country-trap', 'country-pop']
    },
    'r&b': {
        '2000-2005': ['neo-soul', 'contemporary-r&b'],
        '2006-2010': ['alternative-r&b', 'contemporary-r&b'],
        '2011-2025': ['alternative-r&b', 'pop-r&b']
    }
}

# Normalize producer names (for matching)
PRODUCER_NAME_VARIATIONS = {
    'pharrell williams': 'the neptunes',
    'chad hugo': 'the neptunes',
    'pharrell': 'the neptunes',
    'darkchild': 'rodney jerkins',
    'rodney jenkins': 'rodney jerkins',
    'timbo': 'timbaland',
    'tim mosley': 'timbaland',
    'jd': 'jermaine dupri',
    'max': 'max martin',
}


def get_producer_subgenres(producer_name: str, year: int = None) -> dict:
    """
    Get subgenre suggestions based on producer.
    
    Args:
        producer_name: Producer name (will be normalized)
        year: Optional year for era-based refinement
    
    Returns:
        dict with primary, subgenres, confidence
    """
    producer_lower = producer_name.lower().strip()
    
    # Normalize name variations
    if producer_lower in PRODUCER_NAME_VARIATIONS:
        producer_lower = PRODUCER_NAME_VARIATIONS[producer_lower]
    
    # Check if we have a signature for this producer
    if producer_lower in PRODUCER_GENRE_SIGNATURES:
        signature = PRODUCER_GENRE_SIGNATURES[producer_lower].copy()
        
        # Add era-based refinement if year provided
        if year and signature['primary'] in ERA_BASED_SUBGENRES:
            era_subgenres = get_era_subgenres(signature['primary'], year)
            if era_subgenres:
                # Combine producer subgenres with era subgenres
                signature['subgenres'] = list(set(signature['subgenres'] + era_subgenres))
        
        return signature
    
    return None


def get_era_subgenres(genre: str, year: int) -> list:
    """Get era-appropriate subgenres for a genre and year."""
    if genre not in ERA_BASED_SUBGENRES:
        return []
    
    era_map = ERA_BASED_SUBGENRES[genre]
    
    for era_range, subgenres in era_map.items():
        start, end = map(int, era_range.split('-'))
        if start <= year <= end:
            return subgenres
    
    return []


def analyze_producer_contribution(song_producers: list, song_year: int = None) -> dict:
    """
    Analyze all producers for a song and aggregate their genre signals.
    
    Args:
        song_producers: List of producer names for the song
        song_year: Optional year for era context
    
    Returns:
        Aggregated genre signals with confidence
    """
    if not song_producers:
        return None
    
    all_subgenres = []
    all_primaries = []
    total_confidence = 0
    
    for producer in song_producers:
        signature = get_producer_subgenres(producer, song_year)
        if signature:
            all_primaries.append(signature['primary'])
            all_subgenres.extend(signature['subgenres'])
            total_confidence += signature['confidence']
    
    if not all_subgenres:
        return None
    
    # Deduplicate and return most common
    from collections import Counter
    subgenre_counts = Counter(all_subgenres)
    
    return {
        'suggested_subgenres': [sg for sg, count in subgenre_counts.most_common(3)],
        'confidence': min(total_confidence / len(song_producers), 1.0),
        'num_producers': len([p for p in song_producers if get_producer_subgenres(p, song_year)]),
        'source': 'producer_specialization'
    }

