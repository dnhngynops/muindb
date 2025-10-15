#!/usr/bin/env python3
"""
Data Cleanup Manager
Combines all data cleanup functionality for Phase 2 credits data.
Includes: artist credits cleanup, duplicate credits cleanup, and smart credit splitting.
"""

import sys
import os
import re
from pathlib import Path
from sqlalchemy import func, text

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

from database.connection import DatabaseManager
from database.phase2_models import Credits, SongCredits, CreditRoles

class SmartCreditSplitter:
    """Intelligently splits credits based on patterns and rules."""
    
    def __init__(self):
        self.db = DatabaseManager()
        
        # Known patterns that should NOT be split
        self.keep_together_patterns = [
            # Band names
            r'.*and the .*',  # "Jake and The Phatman"
            r'.*& the .*',    # "Jake & The Phatman"
            r'.*and his .*',  # "Jake and His Phatman"
            r'.*& his .*',    # "Jake & His Phatman"
            r'.*and her .*',  # "Jake and Her Phatman"
            r'.*& her .*',    # "Jake & Her Phatman"
            
            # Common music industry patterns
            r'.*and company.*',  # "Jake and Company"
            r'.*& company.*',    # "Jake & Company"
            r'.*and associates.*',  # "Jake and Associates"
            r'.*& associates.*',    # "Jake & Associates"
            
            # Specific known entities
            r'.*and sons.*',   # "Jake and Sons"
            r'.*& sons.*',     # "Jake & Sons"
            r'.*and daughters.*',  # "Jake and Daughters"
            r'.*& daughters.*',    # "Jake & Daughters"
        ]
        
        # Manual rules for specific cases
        self.manual_rules = {
            # Keep these together (exact matches)
            'Jake and The Phatman': 'Jake and The Phatman',
            'Jake & The Phatman': 'Jake & The Phatman',
            'Jake and His Phatman': 'Jake and His Phatman',
            'Jake & His Phatman': 'Jake & His Phatman',
            'Jake and Her Phatman': 'Jake and Her Phatman',
            'Jake & Her Phatman': 'Jake & Her Phatman',
            'Jake and Company': 'Jake and Company',
            'Jake & Company': 'Jake & Company',
            'Jake and Associates': 'Jake and Associates',
            'Jake & Associates': 'Jake & Associates',
            'Jake and Sons': 'Jake and Sons',
            'Jake & Sons': 'Jake & Sons',
            'Jake and Daughters': 'Jake and Daughters',
            'Jake & Daughters': 'Jake & Daughters',
        }
    
    def should_keep_together(self, credit_name):
        """Check if a credit name should be kept together based on patterns."""
        # Check manual rules first
        if credit_name in self.manual_rules:
            return True
        
        # Check pattern rules
        for pattern in self.keep_together_patterns:
            if re.match(pattern, credit_name, re.IGNORECASE):
                return True
        
        return False
    
    def split_credits(self, credit_name):
        """Split credits intelligently based on patterns and rules."""
        if self.should_keep_together(credit_name):
            return [credit_name]
        
        # Split on common separators
        separators = [' and ', ' & ', ', and ', ', & ']
        
        for sep in separators:
            if sep in credit_name:
                parts = credit_name.split(sep)
                # Clean up each part
                cleaned_parts = [part.strip() for part in parts if part.strip()]
                if len(cleaned_parts) > 1:
                    return cleaned_parts
        
        return [credit_name]
    
    def process_credits(self):
        """Process all credits and split them if needed."""
        print("🔧 SMART CREDIT SPLITTING")
        print("=" * 35)
        
        with self.db.get_session() as session:
            # Get all credits that might need splitting
            credits_to_split = session.query(Credits).filter(
                Credits.credit_name.contains(' and '),
                Credits.credit_name.notlike('%and the%'),
                Credits.credit_name.notlike('%and his%'),
                Credits.credit_name.notlike('%and her%'),
                Credits.credit_name.notlike('%and company%'),
                Credits.credit_name.notlike('%and associates%'),
                Credits.credit_name.notlike('%and sons%'),
                Credits.credit_name.notlike('%and daughters%')
            ).all()
            
            print(f"Found {len(credits_to_split)} credits that might need splitting")
            
            split_count = 0
            for credit in credits_to_split:
                original_name = credit.credit_name
                split_names = self.split_credits(original_name)
                
                if len(split_names) > 1:
                    print(f"Splitting: '{original_name}' → {split_names}")
                    
                    # Create new credits for each split name
                    for split_name in split_names:
                        # Check if credit already exists
                        existing = session.query(Credits).filter(
                            Credits.normalized_name == split_name.lower()
                        ).first()
                        
                        if not existing:
                            new_credit = Credits(
                                credit_name=split_name,
                                normalized_name=split_name.lower(),
                                genius_id=credit.genius_id,
                                is_verified=credit.is_verified
                            )
                            session.add(new_credit)
                            split_count += 1
                    
                    # Remove the original credit
                    session.delete(credit)
            
            session.commit()
            print(f"✅ Split {split_count} credits successfully")

def cleanup_artist_credits():
    """Remove credits that are actually artist names with 'feat.'."""
    print("🧹 CLEANUP ARTIST CREDITS")
    print("=" * 35)
    
    db = DatabaseManager()
    
    with db.get_session() as session:
        # Find all credits with 'feat' in the name
        artist_credits = session.query(Credits).filter(
            Credits.credit_name.ilike('%feat%')
        ).all()
        
        print(f"Found {len(artist_credits)} credits with 'feat' in the name")
        
        removed_count = 0
        for credit in artist_credits:
            print(f"Removing: {credit.credit_name}")
            
            # Remove all song credits for this credit
            session.query(SongCredits).filter(
                SongCredits.credit_id == credit.credit_id
            ).delete()
            
            # Remove the credit itself
            session.delete(credit)
            removed_count += 1
        
        session.commit()
        print(f"✅ Removed {removed_count} artist credits successfully")

def cleanup_duplicate_credits():
    """Clean up duplicate credits by merging them."""
    print("🧹 CLEANUP DUPLICATE CREDITS")
    print("=" * 40)
    
    db = DatabaseManager()
    
    with db.get_session() as session:
        # Find duplicates by normalized name (case-insensitive)
        duplicates = session.query(
            Credits.normalized_name,
            func.count(Credits.credit_id).label('count')
        ).group_by(Credits.normalized_name).having(
            func.count(Credits.credit_id) > 1
        ).all()
        
        print(f"Found {len(duplicates)} duplicate credit groups")
        
        merged_count = 0
        for normalized_name, count in duplicates:
            print(f"Processing duplicates for: {normalized_name} ({count} instances)")
            
            # Get all credits with this normalized name
            credit_group = session.query(Credits).filter(
                Credits.normalized_name == normalized_name
            ).order_by(Credits.credit_id).all()
            
            if len(credit_group) > 1:
                # Keep the first one (lowest ID)
                keep_credit = credit_group[0]
                remove_credits = credit_group[1:]
                
                print(f"  Keeping: {keep_credit.credit_name} (ID: {keep_credit.credit_id})")
                
                for remove_credit in remove_credits:
                    print(f"  Removing: {remove_credit.credit_name} (ID: {remove_credit.credit_id})")
                    
                    # Update all song credits to point to the kept credit
                    session.query(SongCredits).filter(
                        SongCredits.credit_id == remove_credit.credit_id
                    ).update({
                        SongCredits.credit_id: keep_credit.credit_id
                    })
                    
                    # Remove the duplicate credit
                    session.delete(remove_credit)
                    merged_count += 1
        
        session.commit()
        print(f"✅ Merged {merged_count} duplicate credits successfully")

def run_all_cleanup():
    """Run all cleanup operations in sequence."""
    print("🧹 DATA CLEANUP MANAGER")
    print("=" * 50)
    print("Running all data cleanup operations...")
    print()
    
    # Run cleanup operations
    cleanup_artist_credits()
    print()
    
    cleanup_duplicate_credits()
    print()
    
    # Initialize and run smart credit splitter
    splitter = SmartCreditSplitter()
    splitter.process_credits()
    print()
    
    print("🎉 All cleanup operations completed successfully!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Data Cleanup Manager for Phase 2')
    parser.add_argument('--artist-credits', action='store_true', help='Clean up artist credits only')
    parser.add_argument('--duplicates', action='store_true', help='Clean up duplicate credits only')
    parser.add_argument('--split-credits', action='store_true', help='Split credits only')
    parser.add_argument('--all', action='store_true', help='Run all cleanup operations (default)')
    
    args = parser.parse_args()
    
    if args.artist_credits:
        cleanup_artist_credits()
    elif args.duplicates:
        cleanup_duplicate_credits()
    elif args.split_credits:
        splitter = SmartCreditSplitter()
        splitter.process_credits()
    else:
        # Default: run all cleanup operations
        run_all_cleanup()
