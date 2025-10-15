#!/usr/bin/env python3
"""
Database setup script for Billboard Music Database.

This script initializes the database schema and creates all necessary tables.
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

from database.connection import get_database_manager
from utils.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_database():
    """Set up the database with all required tables."""
    try:
        # Get configuration
        config = get_config()
        config.ensure_directories()
        
        # Get database manager
        db_manager = get_database_manager()
        
        # Test connection
        logger.info("Testing database connection...")
        if not db_manager.test_connection():
            logger.error("Database connection test failed")
            return False
        
        # Create tables
        logger.info("Creating database tables...")
        db_manager.create_tables()
        
        # Get database info
        info = db_manager.get_database_info()
        logger.info(f"Database setup completed successfully!")
        logger.info(f"Database path: {info['database_path']}")
        logger.info(f"Tables created: billboard_entries, chart_summaries, artist_stats, song_stats")
        
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False


def reset_database():
    """Reset the database by dropping and recreating all tables."""
    try:
        logger.warning("This will delete all existing data!")
        response = input("Are you sure you want to reset the database? (yes/no): ")
        
        if response.lower() != 'yes':
            logger.info("Database reset cancelled")
            return False
        
        # Get database manager
        db_manager = get_database_manager()
        
        # Drop tables
        logger.info("Dropping existing tables...")
        db_manager.drop_tables()
        
        # Create tables
        logger.info("Creating new tables...")
        db_manager.create_tables()
        
        logger.info("Database reset completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return False


def show_database_info():
    """Show information about the current database."""
    try:
        db_manager = get_database_manager()
        info = db_manager.get_database_info()
        
        print("\n" + "="*50)
        print("BILLBOARD MUSIC DATABASE INFO")
        print("="*50)
        print(f"Database Path: {info['database_path']}")
        print(f"Billboard Entries: {info['billboard_entries']:,}")
        print(f"Chart Summaries: {info['chart_summaries']:,}")
        print(f"Artist Stats: {info['artist_stats']:,}")
        print(f"Song Stats: {info['song_stats']:,}")
        
        if info['date_range']['earliest']:
            print(f"Date Range: {info['date_range']['earliest']} to {info['date_range']['latest']}")
        else:
            print("Date Range: No data")
        
        print("="*50)
        
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")


def main():
    """Main function to handle command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Billboard Music Database Setup')
    parser.add_argument('--reset', action='store_true', help='Reset the database (WARNING: deletes all data)')
    parser.add_argument('--info', action='store_true', help='Show database information')
    
    args = parser.parse_args()
    
    if args.reset:
        success = reset_database()
    elif args.info:
        show_database_info()
        success = True
    else:
        success = setup_database()
    
    if success:
        logger.info("Operation completed successfully")
        sys.exit(0)
    else:
        logger.error("Operation failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
