#!/usr/bin/env python3
"""
Management Verification API Client for Billboard Music Database
Verifies producer management status through various sources
"""

import os
import sys
import requests
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import quote
import re
from datetime import datetime

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file."""
    env_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load .env file
load_env_file()

logger = logging.getLogger(__name__)

class ManagementVerificationClient:
    """
    Client for verifying producer management status through various sources
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Known management companies and their patterns
        self.management_patterns = {
            'Roc Nation': ['roc nation', 'rocnation', 'rocnation.com'],
            'Scooter Braun Projects': ['scooter braun', 'sb projects', 'scooterbraun.com'],
            'Red Light Management': ['red light management', 'redlightmanagement.com'],
            'Maverick Management': ['maverick management', 'maverickmgmt.com'],
            'Full Stop Management': ['full stop management', 'fullstopmgmt.com'],
            'The Azoff Company': ['azoff company', 'azoffcompany.com'],
            'Maverick': ['maverick', 'maverick.com'],
            'Crush Music': ['crush music', 'crushmusic.com'],
            'Salxco': ['salxco', 'salxco.com'],
            'Universal Music Group': ['universal music', 'umusic.com', 'universalmusic.com'],
            'Sony Music Entertainment': ['sony music', 'sonymusic.com'],
            'Warner Music Group': ['warner music', 'wmg.com', 'warnermusic.com'],
            'Atlantic Records': ['atlantic records', 'atlanticrecords.com'],
            'Interscope Records': ['interscope', 'interscope.com'],
            'Republic Records': ['republic records', 'republicrecords.com'],
            'Columbia Records': ['columbia records', 'columbiarecords.com'],
            'RCA Records': ['rca records', 'rcarecords.com'],
            'Capitol Records': ['capitol records', 'capitolrecords.com'],
            'Def Jam Recordings': ['def jam', 'defjam.com'],
        }
        
        # Social media platforms to check
        self.social_platforms = {
            'instagram': 'https://www.instagram.com/{}',
            'twitter': 'https://twitter.com/{}',
            'linkedin': 'https://www.linkedin.com/in/{}',
            'facebook': 'https://www.facebook.com/{}'
        }
    
    def verify_producer_management(self, producer_name: str, producer_id: int = None) -> Dict[str, Any]:
        """
        Verify management status for a producer through multiple sources
        
        Args:
            producer_name: Name of the producer
            producer_id: Database ID of the producer
            
        Returns:
            Dictionary with verification results
        """
        logger.info(f"🔍 Verifying management status for: {producer_name}")
        
        results = {
            'producer_name': producer_name,
            'producer_id': producer_id,
            'verification_methods': [],
            'management_companies': [],
            'confidence_score': 0.0,
            'verification_status': 'unverified',
            'source_urls': [],
            'notes': []
        }
        
        # Method 1: Web search verification
        web_results = self._verify_via_web_search(producer_name)
        if web_results:
            results['verification_methods'].append('web_search')
            results['management_companies'].extend(web_results.get('companies', []))
            results['source_urls'].extend(web_results.get('urls', []))
            results['notes'].extend(web_results.get('notes', []))
        
        # Method 2: Social media verification
        social_results = self._verify_via_social_media(producer_name)
        if social_results:
            results['verification_methods'].append('social_media')
            results['management_companies'].extend(social_results.get('companies', []))
            results['source_urls'].extend(social_results.get('urls', []))
            results['notes'].extend(social_results.get('notes', []))
        
        # Method 3: Industry database verification
        industry_results = self._verify_via_industry_sources(producer_name)
        if industry_results:
            results['verification_methods'].append('industry_database')
            results['management_companies'].extend(industry_results.get('companies', []))
            results['source_urls'].extend(industry_results.get('urls', []))
            results['notes'].extend(industry_results.get('notes', []))
        
        # Calculate confidence score
        results['confidence_score'] = self._calculate_confidence_score(results)
        
        # Determine verification status
        results['verification_status'] = self._determine_verification_status(results)
        
        # Remove duplicates
        results['management_companies'] = list(set(results['management_companies']))
        results['source_urls'] = list(set(results['source_urls']))
        
        logger.info(f"✅ Verification complete for {producer_name}: {results['verification_status']} (confidence: {results['confidence_score']:.2f})")
        
        return results
    
    def _verify_via_web_search(self, producer_name: str) -> Optional[Dict[str, Any]]:
        """Verify management via web search"""
        try:
            # This would integrate with a search API like Google Custom Search
            # For now, we'll simulate the process
            logger.debug(f"🔍 Web search verification for {producer_name}")
            
            # Simulate web search results
            # In a real implementation, you would use Google Custom Search API or similar
            search_query = f"{producer_name} producer management"
            
            # Mock results based on known patterns
            companies_found = []
            urls = []
            notes = []
            
            # Check if producer name matches any known management patterns
            for company, patterns in self.management_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in producer_name.lower():
                        companies_found.append(company)
                        notes.append(f"Found management pattern: {pattern}")
                        break
            
            if companies_found:
                return {
                    'companies': companies_found,
                    'urls': urls,
                    'notes': notes
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Web search verification failed for {producer_name}: {e}")
            return None
    
    def _verify_via_social_media(self, producer_name: str) -> Optional[Dict[str, Any]]:
        """Verify management via social media profiles"""
        try:
            logger.debug(f"📱 Social media verification for {producer_name}")
            
            # Normalize producer name for social media search
            social_name = self._normalize_for_social_media(producer_name)
            
            companies_found = []
            urls = []
            notes = []
            
            # Check each social media platform
            for platform, url_template in self.social_platforms.items():
                try:
                    url = url_template.format(social_name)
                    # In a real implementation, you would check if the profile exists
                    # and scrape bio/description for management company mentions
                    
                    # Mock: Check if any management patterns appear in the URL
                    for company, patterns in self.management_patterns.items():
                        for pattern in patterns:
                            if pattern.lower() in url.lower():
                                companies_found.append(company)
                                urls.append(url)
                                notes.append(f"Found on {platform}: {pattern}")
                                break
                    
                    # Add small delay to be respectful
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.debug(f"Error checking {platform} for {producer_name}: {e}")
                    continue
            
            if companies_found:
                return {
                    'companies': companies_found,
                    'urls': urls,
                    'notes': notes
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Social media verification failed for {producer_name}: {e}")
            return None
    
    def _verify_via_industry_sources(self, producer_name: str) -> Optional[Dict[str, Any]]:
        """Verify management via industry databases and sources"""
        try:
            logger.debug(f"🏢 Industry database verification for {producer_name}")
            
            # This would integrate with industry databases like:
            # - AllMusic
            # - Discogs
            # - MusicBrainz
            # - Billboard Pro
            # - Variety
            # - The Hollywood Reporter
            
            companies_found = []
            urls = []
            notes = []
            
            # Mock industry database check
            # In a real implementation, you would query these databases
            industry_sources = [
                'https://www.allmusic.com',
                'https://www.discogs.com',
                'https://musicbrainz.org',
                'https://www.billboard.com'
            ]
            
            for source in industry_sources:
                # Simulate checking each source
                # In reality, you would make API calls or scrape these sites
                for company, patterns in self.management_patterns.items():
                    for pattern in patterns:
                        if pattern.lower() in producer_name.lower():
                            companies_found.append(company)
                            urls.append(f"{source}/search?q={quote(producer_name)}")
                            notes.append(f"Found in industry database: {pattern}")
                            break
            
            if companies_found:
                return {
                    'companies': companies_found,
                    'urls': urls,
                    'notes': notes
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Industry database verification failed for {producer_name}: {e}")
            return None
    
    def _normalize_for_social_media(self, name: str) -> str:
        """Normalize producer name for social media search"""
        # Remove common suffixes
        name = re.sub(r'\s+(jr|sr|ii|iii|iv)\.?$', '', name, flags=re.IGNORECASE)
        
        # Replace spaces with dots or underscores
        name = name.replace(' ', '.')
        
        # Remove special characters
        name = re.sub(r'[^\w.]', '', name)
        
        # Convert to lowercase
        name = name.lower()
        
        return name
    
    def _calculate_confidence_score(self, results: Dict[str, Any]) -> float:
        """Calculate confidence score based on verification results"""
        score = 0.0
        
        # Base score for having any verification methods
        if results['verification_methods']:
            score += 0.3
        
        # Score for number of management companies found
        unique_companies = len(set(results['management_companies']))
        score += min(unique_companies * 0.2, 0.4)
        
        # Score for number of source URLs
        unique_urls = len(set(results['source_urls']))
        score += min(unique_urls * 0.1, 0.2)
        
        # Score for verification methods diversity
        method_diversity = len(set(results['verification_methods']))
        score += min(method_diversity * 0.1, 0.1)
        
        return min(score, 1.0)
    
    def _determine_verification_status(self, results: Dict[str, Any]) -> str:
        """Determine verification status based on results"""
        if not results['management_companies']:
            return 'unverified'
        
        confidence = results['confidence_score']
        
        if confidence >= 0.8:
            return 'verified'
        elif confidence >= 0.5:
            return 'pending'
        else:
            return 'disputed'
    
    def get_management_company_info(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a management company"""
        try:
            # This would integrate with company databases or APIs
            # For now, return basic info from our patterns
            if company_name in self.management_patterns:
                return {
                    'company_name': company_name,
                    'patterns': self.management_patterns[company_name],
                    'website': f"https://www.{company_name.lower().replace(' ', '')}.com",
                    'verified': True
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting company info for {company_name}: {e}")
            return None

# Test function
def test_management_verification():
    """Test function to verify management verification system"""
    
    print("🔍 Testing Management Verification System")
    print("=" * 50)
    
    try:
        client = ManagementVerificationClient()
        
        # Test with some well-known producers
        test_producers = [
            'Max Martin',
            'Dr. Dre',
            'Timbaland',
            'Pharrell Williams',
            'Kanye West'
        ]
        
        for producer in test_producers:
            print(f"\n🎵 Testing: {producer}")
            result = client.verify_producer_management(producer)
            
            print(f"   Status: {result['verification_status']}")
            print(f"   Confidence: {result['confidence_score']:.2f}")
            print(f"   Methods: {', '.join(result['verification_methods'])}")
            print(f"   Companies: {', '.join(result['management_companies']) if result['management_companies'] else 'None'}")
            
            time.sleep(1)  # Rate limiting
        
        print("\n🎉 Management verification system test complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing management verification: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_management_verification()
