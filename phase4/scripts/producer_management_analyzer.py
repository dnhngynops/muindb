#!/usr/bin/env python3
"""
Producer Management Analyzer for Billboard Music Database Phase 4
Analyzes producer management status and generates A&R insights
"""

import sys
import os
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
import json

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

# Add the main project src directory
main_src_dir = project_root.parent / 'phase2' / 'src'
sys.path.insert(0, str(main_src_dir))

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file."""
    env_file = project_root.parent / '.env'
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
from database.models import Songs, Artists
from database.phase2_models import Credits, SongCredits, CreditRoles
from database.phase4_models import (
    ManagementCompany, ProducerManagement, ManagementVerification,
    ProducerPerformanceMetrics, ManagementEffectiveness
)
from api.management_verification_client import ManagementVerificationClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProducerManagementAnalyzer:
    """
    Analyzes producer management status and generates A&R insights
    """
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self.verification_client = ManagementVerificationClient()
        self._management_cache = {}
        
    def setup_phase4_tables(self):
        """Set up Phase 4 database tables"""
        logger.info("🔧 Setting up Phase 4 database tables...")
        
        try:
            with self.db_manager.get_session() as session:
                # Create all Phase 4 tables
                ManagementCompany.__table__.create(session.bind, checkfirst=True)
                ProducerManagement.__table__.create(session.bind, checkfirst=True)
                ManagementVerification.__table__.create(session.bind, checkfirst=True)
                ProducerPerformanceMetrics.__table__.create(session.bind, checkfirst=True)
                ManagementEffectiveness.__table__.create(session.bind, checkfirst=True)
                
                session.commit()
                logger.info("✅ Phase 4 tables created successfully")
                
        except Exception as e:
            logger.error(f"❌ Error setting up Phase 4 tables: {e}")
            raise
    
    def populate_initial_data(self):
        """Populate initial management companies and data"""
        logger.info("📊 Populating initial management companies...")
        
        try:
            with self.db_manager.get_session() as session:
                # Check if data already exists
                existing_companies = session.query(ManagementCompany).count()
                if existing_companies > 0:
                    logger.info(f"Management companies already populated ({existing_companies} companies)")
                    return
                
                # Read and execute the schema SQL file
                schema_file = project_root / 'phase4_schema_extension.sql'
                if schema_file.exists():
                    with open(schema_file, 'r') as f:
                        sql_content = f.read()
                    
                    # Split by semicolon and execute each statement
                    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                    
                    for statement in statements:
                        if statement.upper().startswith('INSERT INTO management_companies'):
                            session.execute(statement)
                    
                    session.commit()
                    logger.info("✅ Initial management companies populated")
                else:
                    logger.warning("Schema file not found, skipping initial data population")
                    
        except Exception as e:
            logger.error(f"❌ Error populating initial data: {e}")
            raise
    
    def get_producers_from_2000(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get producers who worked on songs from 2000"""
        logger.info(f"🎵 Getting producers from 2000 songs (limit: {limit})")
        
        try:
            with self.db_manager.get_session() as session:
                query = session.query(
                    Credits.credit_id,
                    Credits.credit_name,
                    Credits.normalized_name
                ).join(
                    SongCredits, Credits.credit_id == SongCredits.credit_id
                ).join(
                    CreditRoles, SongCredits.role_id == CreditRoles.role_id
                ).join(
                    Songs, SongCredits.song_id == Songs.song_id
                ).filter(
                    CreditRoles.role_name == 'Producer',
                    Songs.first_chart_appearance.like('2000%')
                ).distinct().limit(limit)
                
                producers = []
                for row in query.all():
                    producers.append({
                        'credit_id': row.credit_id,
                        'credit_name': row.credit_name,
                        'normalized_name': row.normalized_name
                    })
                
                logger.info(f"Found {len(producers)} producers from 2000")
                return producers
                
        except Exception as e:
            logger.error(f"❌ Error getting producers: {e}")
            return []
    
    def analyze_producer_management(self, producer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze management status for a single producer"""
        producer_name = producer_data['credit_name']
        producer_id = producer_data['credit_id']
        
        logger.info(f"🔍 Analyzing management for: {producer_name}")
        
        # Verify management status
        verification_result = self.verification_client.verify_producer_management(
            producer_name, producer_id
        )
        
        # Calculate performance metrics
        performance_metrics = self._calculate_producer_metrics(producer_id)
        
        return {
            'producer_data': producer_data,
            'verification_result': verification_result,
            'performance_metrics': performance_metrics,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _calculate_producer_metrics(self, producer_id: int) -> Dict[str, Any]:
        """Calculate performance metrics for a producer"""
        try:
            with self.db_manager.get_session() as session:
                # Get all songs by this producer from 2000
                songs_query = session.query(
                    Songs.song_id,
                    Songs.song_name,
                    Songs.artist_name,
                    Songs.peak_position,
                    Songs.total_weeks_on_chart,
                    Songs.weeks_at_number_one,
                    Songs.weeks_in_top_10,
                    Songs.weeks_in_top_40
                ).join(
                    SongCredits, Songs.song_id == SongCredits.song_id
                ).join(
                    CreditRoles, SongCredits.role_id == CreditRoles.role_id
                ).filter(
                    SongCredits.credit_id == producer_id,
                    CreditRoles.role_name == 'Producer',
                    Songs.first_chart_appearance.like('2000%')
                )
                
                songs = songs_query.all()
                
                if not songs:
                    return {
                        'total_songs': 0,
                        'number_one_hits': 0,
                        'top_10_hits': 0,
                        'top_40_hits': 0,
                        'total_weeks_on_chart': 0,
                        'average_peak_position': None,
                        'success_rate': 0.0,
                        'genre_diversity_score': 0.0,
                        'collaboration_count': 0
                    }
                
                # Calculate metrics
                total_songs = len(songs)
                number_one_hits = sum(1 for song in songs if song.peak_position == 1)
                top_10_hits = sum(1 for song in songs if song.peak_position <= 10)
                top_40_hits = sum(1 for song in songs if song.peak_position <= 40)
                total_weeks = sum(song.total_weeks_on_chart for song in songs)
                average_peak = sum(song.peak_position for song in songs) / total_songs
                success_rate = (top_40_hits / total_songs) * 100 if total_songs > 0 else 0
                
                # Calculate genre diversity (simplified)
                unique_artists = len(set(song.artist_name for song in songs))
                genre_diversity_score = min(unique_artists / 10.0, 1.0)  # Normalize to 0-1
                
                return {
                    'total_songs': total_songs,
                    'number_one_hits': number_one_hits,
                    'top_10_hits': top_10_hits,
                    'top_40_hits': top_40_hits,
                    'total_weeks_on_chart': total_weeks,
                    'average_peak_position': round(average_peak, 2),
                    'success_rate': round(success_rate, 2),
                    'genre_diversity_score': round(genre_diversity_score, 2),
                    'collaboration_count': unique_artists
                }
                
        except Exception as e:
            logger.error(f"❌ Error calculating metrics for producer {producer_id}: {e}")
            return {}
    
    def save_analysis_results(self, analysis_results: List[Dict[str, Any]]):
        """Save analysis results to database"""
        logger.info(f"💾 Saving analysis results for {len(analysis_results)} producers...")
        
        try:
            with self.db_manager.get_session() as session:
                for result in analysis_results:
                    producer_data = result['producer_data']
                    verification = result['verification_result']
                    metrics = result['performance_metrics']
                    
                    # Save performance metrics
                    if metrics:
                        performance = ProducerPerformanceMetrics(
                            producer_id=producer_data['credit_id'],
                            year=2000,
                            total_songs=metrics.get('total_songs', 0),
                            number_one_hits=metrics.get('number_one_hits', 0),
                            top_10_hits=metrics.get('top_10_hits', 0),
                            top_40_hits=metrics.get('top_40_hits', 0),
                            total_weeks_on_chart=metrics.get('total_weeks_on_chart', 0),
                            average_peak_position=metrics.get('average_peak_position'),
                            success_rate=metrics.get('success_rate', 0),
                            genre_diversity_score=metrics.get('genre_diversity_score', 0),
                            collaboration_count=metrics.get('collaboration_count', 0)
                        )
                        session.add(performance)
                    
                    # Save verification results
                    if verification['management_companies']:
                        for company_name in verification['management_companies']:
                            # Get or create management company
                            company = session.query(ManagementCompany).filter(
                                ManagementCompany.company_name == company_name
                            ).first()
                            
                            if not company:
                                company = ManagementCompany(
                                    company_name=company_name,
                                    company_type='management',
                                    is_active=True
                                )
                                session.add(company)
                                session.flush()
                            
                            # Create producer management record
                            producer_mgmt = ProducerManagement(
                                producer_id=producer_data['credit_id'],
                                company_id=company.company_id,
                                management_type='exclusive',  # Default assumption
                                is_current=True,
                                source=verification['verification_methods'][0] if verification['verification_methods'] else 'manual',
                                confidence_score=verification['confidence_score']
                            )
                            session.add(producer_mgmt)
                    
                    # Save verification record
                    verification_record = ManagementVerification(
                        producer_id=producer_data['credit_id'],
                        verification_methods=json.dumps(verification['verification_methods']),
                        verification_status=verification['verification_status'],
                        verification_notes=json.dumps(verification['notes']),
                        source_urls=json.dumps(verification['source_urls']),
                        confidence_score=verification['confidence_score']
                    )
                    session.add(verification_record)
                
                session.commit()
                logger.info("✅ Analysis results saved successfully")
                
        except Exception as e:
            logger.error(f"❌ Error saving analysis results: {e}")
            raise
    
    def generate_ar_insights(self) -> Dict[str, Any]:
        """Generate A&R insights from the analysis"""
        logger.info("📈 Generating A&R insights...")
        
        try:
            with self.db_manager.get_session() as session:
                # Get management effectiveness summary
                effectiveness_query = session.query(
                    ManagementCompany.company_name,
                    ManagementCompany.company_type,
                    ProducerPerformanceMetrics.success_rate,
                    ProducerPerformanceMetrics.number_one_hits,
                    ProducerPerformanceMetrics.total_songs
                ).join(
                    ProducerManagement, ManagementCompany.company_id == ProducerManagement.company_id
                ).join(
                    ProducerPerformanceMetrics, ProducerManagement.producer_id == ProducerPerformanceMetrics.producer_id
                ).filter(
                    ProducerManagement.is_current == True,
                    ProducerPerformanceMetrics.year == 2000
                )
                
                effectiveness_data = effectiveness_query.all()
                
                # Calculate insights
                insights = {
                    'total_producers_analyzed': len(set(row[0] for row in effectiveness_data)),
                    'management_companies': {},
                    'top_performers': [],
                    'unmanaged_high_performers': [],
                    'management_effectiveness': {}
                }
                
                # Group by management company
                company_stats = {}
                for row in effectiveness_data:
                    company_name = row[0]
                    if company_name not in company_stats:
                        company_stats[company_name] = {
                            'producers': [],
                            'total_songs': 0,
                            'total_hits': 0,
                            'avg_success_rate': 0
                        }
                    
                    company_stats[company_name]['producers'].append({
                        'success_rate': row[2],
                        'number_one_hits': row[3],
                        'total_songs': row[4]
                    })
                    company_stats[company_name]['total_songs'] += row[4]
                    company_stats[company_name]['total_hits'] += row[3]
                
                # Calculate averages
                for company, stats in company_stats.items():
                    if stats['producers']:
                        stats['avg_success_rate'] = sum(p['success_rate'] for p in stats['producers']) / len(stats['producers'])
                        insights['management_companies'][company] = stats
                
                # Find top performers
                all_producers = []
                for stats in company_stats.values():
                    all_producers.extend(stats['producers'])
                
                top_performers = sorted(all_producers, key=lambda x: x['success_rate'], reverse=True)[:10]
                insights['top_performers'] = top_performers
                
                logger.info("✅ A&R insights generated successfully")
                return insights
                
        except Exception as e:
            logger.error(f"❌ Error generating A&R insights: {e}")
            return {}
    
    def run_analysis(self, limit: int = 10, test_mode: bool = False):
        """Run the complete producer management analysis"""
        logger.info("🚀 Starting Producer Management Analysis")
        logger.info("=" * 60)
        
        try:
            # Setup Phase 4 tables
            self.setup_phase4_tables()
            
            # Populate initial data
            self.populate_initial_data()
            
            # Get producers from 2000
            producers = self.get_producers_from_2000(limit)
            
            if not producers:
                logger.warning("No producers found for analysis")
                return
            
            logger.info(f"Analyzing {len(producers)} producers...")
            
            # Analyze each producer
            analysis_results = []
            for i, producer in enumerate(producers, 1):
                logger.info(f"Progress: {i}/{len(producers)} - {producer['credit_name']}")
                
                try:
                    result = self.analyze_producer_management(producer)
                    analysis_results.append(result)
                    
                    if test_mode:
                        # In test mode, just analyze first few
                        if i >= 3:
                            break
                            
                except Exception as e:
                    logger.error(f"Error analyzing {producer['credit_name']}: {e}")
                    continue
            
            # Save results
            if analysis_results:
                self.save_analysis_results(analysis_results)
                
                # Generate insights
                insights = self.generate_ar_insights()
                
                # Print summary
                self._print_analysis_summary(analysis_results, insights)
                
                # Save insights to file
                insights_file = project_root / 'producer_management_insights.json'
                with open(insights_file, 'w') as f:
                    json.dump(insights, f, indent=2, default=str)
                logger.info(f"💾 Insights saved to {insights_file}")
            
            logger.info("🎉 Producer management analysis complete!")
            
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            raise
    
    def _print_analysis_summary(self, results: List[Dict[str, Any]], insights: Dict[str, Any]):
        """Print analysis summary"""
        print("\n" + "=" * 60)
        print("PRODUCER MANAGEMENT ANALYSIS SUMMARY")
        print("=" * 60)
        
        print(f"Total Producers Analyzed: {len(results)}")
        print(f"Management Companies Found: {len(insights.get('management_companies', {}))}")
        
        print("\nTop Performing Producers:")
        for i, producer in enumerate(insights.get('top_performers', [])[:5], 1):
            print(f"  {i}. Success Rate: {producer['success_rate']:.1f}% | Hits: {producer['number_one_hits']} | Songs: {producer['total_songs']}")
        
        print("\nManagement Companies:")
        for company, stats in list(insights.get('management_companies', {}).items())[:5]:
            print(f"  - {company}: {len(stats['producers'])} producers, {stats['avg_success_rate']:.1f}% avg success")
        
        print("=" * 60)

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description='Producer Management Analyzer for Phase 4')
    parser.add_argument('--limit', type=int, default=10,
                       help='Number of producers to analyze (default: 10)')
    parser.add_argument('--test', action='store_true',
                       help='Run in test mode (analyze only 3 producers)')
    parser.add_argument('--setup-only', action='store_true',
                       help='Only set up Phase 4 tables and initial data')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize analyzer
    analyzer = ProducerManagementAnalyzer()
    
    if args.setup_only:
        analyzer.setup_phase4_tables()
        analyzer.populate_initial_data()
        logger.info("Phase 4 setup complete!")
    else:
        # Run analysis
        limit = 3 if args.test else args.limit
        analyzer.run_analysis(limit=limit, test_mode=args.test)

if __name__ == '__main__':
    main()
