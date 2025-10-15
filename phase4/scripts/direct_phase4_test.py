#!/usr/bin/env python3
"""
Direct Phase 4 Test Script
Tests producer management analysis using direct SQL queries
"""

import sys
import os
import logging
import json
from pathlib import Path
from datetime import datetime

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
main_src_dir = project_root.parent / 'phase2' / 'src'
phase4_src_dir = project_root / 'src'
sys.path.insert(0, str(main_src_dir))
sys.path.insert(0, str(phase4_src_dir))

from database.connection import get_database_manager
from database.models import Songs
from database.phase2_models import Credits, SongCredits, CreditRoles
from api.management_verification_client import ManagementVerificationClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_direct_phase4():
    """Test Phase 4 using direct SQL queries"""
    logger.info("🧪 Testing Phase 4 with Direct SQL Queries")
    logger.info("=" * 60)
    
    try:
        # Initialize database manager
        db_manager = get_database_manager()
        verification_client = ManagementVerificationClient()
        
        # Test 1: Get producers from 2000
        logger.info("📊 Test 1: Getting producers from 2000...")
        with db_manager.get_session() as session:
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
            ).distinct().limit(3)
            
            producers = []
            for row in query.all():
                producers.append({
                    'credit_id': row.credit_id,
                    'credit_name': row.credit_name,
                    'normalized_name': row.normalized_name
                })
            
            logger.info(f"✅ Found {len(producers)} producers from 2000")
            for producer in producers:
                logger.info(f"   - {producer['credit_name']} (ID: {producer['credit_id']})")
        
        # Test 2: Analyze each producer
        logger.info("\n🔍 Test 2: Analyzing producer management...")
        analysis_results = []
        
        for producer in producers:
            logger.info(f"\n🎵 Analyzing: {producer['credit_name']}")
            
            # Verify management status
            verification_result = verification_client.verify_producer_management(
                producer['credit_name'], 
                producer['credit_id']
            )
            
            # Calculate performance metrics
            with db_manager.get_session() as session:
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
                    SongCredits.credit_id == producer['credit_id'],
                    CreditRoles.role_name == 'Producer',
                    Songs.first_chart_appearance.like('2000%')
                )
                
                songs = songs_query.all()
                
                if songs:
                    total_songs = len(songs)
                    number_one_hits = sum(1 for song in songs if song.peak_position == 1)
                    top_10_hits = sum(1 for song in songs if song.peak_position <= 10)
                    top_40_hits = sum(1 for song in songs if song.peak_position <= 40)
                    success_rate = (top_40_hits / total_songs) * 100 if total_songs > 0 else 0
                    
                    metrics = {
                        'total_songs': total_songs,
                        'number_one_hits': number_one_hits,
                        'top_10_hits': top_10_hits,
                        'top_40_hits': top_40_hits,
                        'success_rate': round(success_rate, 2)
                    }
                else:
                    metrics = {}
            
            # Store results
            result = {
                'producer_data': producer,
                'verification_result': verification_result,
                'performance_metrics': metrics,
                'analysis_timestamp': datetime.now().isoformat()
            }
            analysis_results.append(result)
            
            # Print summary
            logger.info(f"   Status: {verification_result['verification_status']}")
            logger.info(f"   Confidence: {verification_result['confidence_score']:.2f}")
            logger.info(f"   Companies: {verification_result['management_companies']}")
            if metrics:
                logger.info(f"   Success Rate: {metrics['success_rate']:.1f}%")
                logger.info(f"   Total Songs: {metrics['total_songs']}")
        
        # Test 3: Save results using direct SQL
        logger.info("\n💾 Test 3: Saving results to database...")
        
        with db_manager.get_session() as session:
            from sqlalchemy import text
            
            for result in analysis_results:
                producer_data = result['producer_data']
                verification = result['verification_result']
                metrics = result['performance_metrics']
                
                # Save performance metrics
                if metrics:
                    insert_metrics = text("""
                        INSERT OR REPLACE INTO producer_performance_metrics 
                        (producer_id, year, total_songs, number_one_hits, top_10_hits, top_40_hits, 
                         success_rate, created_at, updated_at)
                        VALUES (:producer_id, :year, :total_songs, :number_one_hits, :top_10_hits, 
                                :top_40_hits, :success_rate, :created_at, :updated_at)
                    """)
                    
                    session.execute(insert_metrics, {
                        'producer_id': producer_data['credit_id'],
                        'year': 2000,
                        'total_songs': metrics.get('total_songs', 0),
                        'number_one_hits': metrics.get('number_one_hits', 0),
                        'top_10_hits': metrics.get('top_10_hits', 0),
                        'top_40_hits': metrics.get('top_40_hits', 0),
                        'success_rate': metrics.get('success_rate', 0),
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    })
                
                # Save verification record
                insert_verification = text("""
                    INSERT INTO management_verification 
                    (producer_id, verification_methods, verification_status, verification_notes, 
                     source_urls, confidence_score, created_at)
                    VALUES (:producer_id, :verification_methods, :verification_status, :verification_notes,
                            :source_urls, :confidence_score, :created_at)
                """)
                
                session.execute(insert_verification, {
                    'producer_id': producer_data['credit_id'],
                    'verification_methods': json.dumps(verification['verification_methods']),
                    'verification_status': verification['verification_status'],
                    'verification_notes': json.dumps(verification['notes']),
                    'source_urls': json.dumps(verification['source_urls']),
                    'confidence_score': verification['confidence_score'],
                    'created_at': datetime.now()
                })
            
            session.commit()
            logger.info("✅ Results saved successfully!")
        
        # Test 4: Query saved data
        logger.info("\n📊 Test 4: Querying saved data...")
        
        with db_manager.get_session() as session:
            from sqlalchemy import text
            
            # Query performance metrics
            metrics_query = text("""
                SELECT c.credit_name, ppm.total_songs, ppm.success_rate, ppm.number_one_hits
                FROM producer_performance_metrics ppm
                JOIN credits c ON ppm.producer_id = c.credit_id
                WHERE ppm.year = 2000
                ORDER BY ppm.success_rate DESC
            """)
            
            result = session.execute(metrics_query)
            metrics_data = result.fetchall()
            
            logger.info("✅ Performance Metrics:")
            for row in metrics_data:
                logger.info(f"   - {row[0]}: {row[1]} songs, {row[2]:.1f}% success, {row[3]} #1 hits")
            
            # Query verification data
            verification_query = text("""
                SELECT c.credit_name, mv.verification_status, mv.confidence_score, mv.verification_methods
                FROM management_verification mv
                JOIN credits c ON mv.producer_id = c.credit_id
                ORDER BY mv.confidence_score DESC
            """)
            
            result = session.execute(verification_query)
            verification_data = result.fetchall()
            
            logger.info("\n✅ Verification Data:")
            for row in verification_data:
                methods = json.loads(row[3]) if row[3] else []
                logger.info(f"   - {row[0]}: {row[1]} (confidence: {row[2]:.2f}, methods: {methods})")
        
        logger.info("\n🎉 Phase 4 direct test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_direct_phase4()
