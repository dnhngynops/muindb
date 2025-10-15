#!/usr/bin/env python3
"""
Quick start script for Billboard Music Database.

This script performs a complete setup and data processing pipeline using existing JSON files.
"""

import sys
import os
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

from database.connection import get_database_manager
from processors.data_cleaner import DataCleaner
from utils.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def quick_start(data_dir: str = None):
    """
    Perform complete setup and data processing using existing JSON files.
    
    Args:
        data_dir: Directory containing yearly JSON files
    """
    try:
        logger.info("="*60)
        logger.info("BILLBOARD MUSIC DATABASE - QUICK START")
        logger.info("="*60)
        
        # Get configuration
        config = get_config()
        config.ensure_directories()
        
        if data_dir is None:
            data_dir = os.path.join(project_root, 'data', 'raw')
        
        # Step 1: Setup database
        logger.info("Step 1: Setting up database...")
        db_manager = get_database_manager()
        
        if not db_manager.test_connection():
            logger.error("Database connection test failed")
            return False
        
        db_manager.create_tables()
        logger.info("✓ Database setup completed")
        
        # Step 2: Check for JSON files
        logger.info("Step 2: Checking for JSON data files...")
        
        if not os.path.exists(data_dir):
            logger.error(f"Data directory not found: {data_dir}")
            logger.error("Please ensure you have downloaded the JSON data files first.")
            return False
        
        json_files = [f for f in os.listdir(data_dir) if f.startswith('billboard_') and f.endswith('.json')]
        
        if not json_files:
            logger.error(f"No billboard JSON files found in {data_dir}")
            logger.error("Please ensure you have downloaded the JSON data files first.")
            return False
        
        logger.info(f"✓ Found {len(json_files)} yearly JSON files")
        
        # Step 3: Process data
        logger.info("Step 3: Processing JSON data...")
        
        # Import the process_data function
        from process_billboard_data import process_data
        
        success = process_data(data_dir, clean_data=True, batch_size=1000)
        
        if not success:
            logger.error("Data processing failed")
            return False
        
        logger.info("✓ Data processing completed")
        
        # Step 4: Show final results
        logger.info("Step 4: Generating final statistics...")
        
        db_info = db_manager.get_database_info()
        
        logger.info("="*60)
        logger.info("QUICK START COMPLETED SUCCESSFULLY!")
        logger.info("="*60)
        logger.info(f"Database Path: {db_info['database_path']}")
        logger.info(f"Total Entries: {db_info['billboard_entries']:,}")
        logger.info(f"Chart Summaries: {db_info['chart_summaries']:,}")
        logger.info(f"Artist Stats: {db_info['artist_stats']:,}")
        logger.info(f"Song Stats: {db_info['song_stats']:,}")
        
        if db_info['date_range']['earliest']:
            logger.info(f"Date Range: {db_info['date_range']['earliest']} to {db_info['date_range']['latest']}")
        else:
            logger.info("Date Range: No data")
        
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"Quick start failed: {e}")
        return False


def interactive_setup():
    """Interactive setup with user prompts."""
    try:
        print("\n" + "="*60)
        print("BILLBOARD MUSIC DATABASE - INTERACTIVE SETUP")
        print("="*60)
        
        # Check for data directory
        data_dir = os.path.join(project_root, 'data', 'raw')
        
        if not os.path.exists(data_dir):
            print(f"Data directory not found: {data_dir}")
            print("Please ensure you have downloaded the JSON data files first.")
            return False
        
        json_files = [f for f in os.listdir(data_dir) if f.startswith('billboard_') and f.endswith('.json')]
        
        if not json_files:
            print(f"No billboard JSON files found in {data_dir}")
            print("Please ensure you have downloaded the JSON data files first.")
            return False
        
        print(f"Found {len(json_files)} yearly JSON files:")
        for json_file in sorted(json_files):
            print(f"  - {json_file}")
        
        # Confirm setup
        print(f"\nSetup configuration:")
        print(f"  Data Directory: {data_dir}")
        print(f"  JSON Files: {len(json_files)}")
        
        confirm = input("\nProceed with database setup? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Setup cancelled")
            return False
        
        # Run quick start
        return quick_start(data_dir)
        
    except KeyboardInterrupt:
        print("\nSetup cancelled by user")
        return False
    except Exception as e:
        logger.error(f"Interactive setup failed: {e}")
        return False


def show_help():
    """Show help information."""
    print("\n" + "="*60)
    print("BILLBOARD MUSIC DATABASE - QUICK START HELP")
    print("="*60)
    print("\nThis script performs a complete setup of the Billboard Music Database:")
    print("  1. Sets up the database schema")
    print("  2. Processes existing JSON data files")
    print("  3. Loads the data into the database")
    print("  4. Generates statistics")
    print("\nPrerequisites:")
    print("  - JSON data files must be present in data/raw/")
    print("  - Files should be named billboard_YYYY.json")
    print("\nCommand line options:")
    print("  --data-dir DIR     Directory containing JSON files (default: data/raw)")
    print("  --interactive       Run in interactive mode")
    print("  --help-full         Show this help message")
    print("\nExamples:")
    print("  python quick_start.py")
    print("  python quick_start.py --data-dir /path/to/json/files")
    print("  python quick_start.py --interactive")
    print("="*60)


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='Billboard Music Database Quick Start')
    parser.add_argument('--data-dir', type=str, default=None,
                       help='Directory containing yearly JSON files (default: data/raw)')
    parser.add_argument('--interactive', action='store_true',
                       help='Run in interactive mode')
    parser.add_argument('--help-full', action='store_true',
                       help='Show detailed help information')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Show help
    if args.help_full:
        show_help()
        sys.exit(0)
    
    # Interactive mode
    if args.interactive:
        success = interactive_setup()
    else:
        # Command line mode
        success = quick_start(args.data_dir)
    
    if success:
        logger.info("Quick start completed successfully!")
        sys.exit(0)
    else:
        logger.error("Quick start failed")
        sys.exit(1)


if __name__ == '__main__':
    main()