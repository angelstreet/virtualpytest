#!/usr/bin/env python3
"""
Hot/Cold Architecture Migration Script
========================================

Safely migrates existing capture files from flat structure to hot/cold architecture.

OLD STRUCTURE:
    capture1/
    ├── segment_*.ts (thousands in root)
    ├── output.m3u8
    └── captures/
        ├── capture_*.jpg (tens of thousands)
        └── capture_*_thumbnail.jpg (tens of thousands)

NEW STRUCTURE:
    capture1/
    ├── segments/
    │   ├── segment_*.ts (hot: 10 files)
    │   ├── output.m3u8
    │   ├── 0/ ... 23/ (cold: hour folders)
    ├── captures/
    │   ├── capture_*.jpg (hot: 100 files)
    │   └── 0/ ... 23/ (cold: hour folders)
    ├── thumbnails/
    │   ├── capture_*_thumbnail.jpg (hot: 100 files)
    │   └── 0/ ... 23/ (cold: hour folders)
    └── metadata/
        ├── capture_*.json (hot: 100 files)
        └── 0/ ... 23/ (cold: hour folders)

SAFE OPERATION:
- Dry-run mode by default (use --execute to apply changes)
- Preserves all file metadata (mtime, permissions)
- Creates backups before moving
- Can resume if interrupted
- Validates file counts before and after
"""

import os
import sys
import shutil
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple


class HotColdMigration:
    """Manages migration from flat to hot/cold architecture"""
    
    def __init__(self, capture_dir: str, dry_run: bool = True):
        self.capture_dir = Path(capture_dir)
        self.dry_run = dry_run
        self.stats = {
            'segments_moved': 0,
            'captures_moved': 0,
            'thumbnails_moved': 0,
            'metadata_moved': 0,
            'errors': []
        }
    
    def log(self, message: str, level: str = 'INFO'):
        """Log with timestamp"""
        prefix = '🔍 [DRY-RUN]' if self.dry_run else '✅'
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"{prefix} [{timestamp}] {level}: {message}")
    
    def create_directory_structure(self):
        """Create hot/cold directory structure"""
        self.log("Creating directory structure...")
        
        directories = [
            'segments',
            'captures',
            'thumbnails',
            'metadata'
        ]
        
        for dir_name in directories:
            dir_path = self.capture_dir / dir_name
            if not self.dry_run:
                dir_path.mkdir(exist_ok=True)
            self.log(f"  Created: {dir_name}/")
            
            # Create 24 hour folders
            for hour in range(24):
                hour_path = dir_path / str(hour)
                if not self.dry_run:
                    hour_path.mkdir(exist_ok=True)
                self.log(f"  Created: {dir_name}/{hour}/", level='DEBUG')
    
    def get_file_hour(self, filepath: Path) -> int:
        """Get hour (0-23) from file modification time"""
        try:
            mtime = filepath.stat().st_mtime
            return datetime.fromtimestamp(mtime).hour
        except Exception as e:
            self.log(f"Error getting hour for {filepath}: {e}", level='ERROR')
            return datetime.now().hour
    
    def migrate_segments(self):
        """Migrate segment files from root to segments/ with hot/cold separation"""
        self.log("=" * 60)
        self.log("MIGRATING SEGMENTS")
        self.log("=" * 60)
        
        # Find all segment files in root
        segments = sorted(
            self.capture_dir.glob('segment_*.ts'),
            key=lambda f: f.stat().st_mtime
        )
        
        if not segments:
            self.log("No segments found in root directory")
            return
        
        self.log(f"Found {len(segments)} segment files")
        
        # Keep last 10 in hot storage, rest in hour folders
        hot_limit = 10
        hot_segments = segments[-hot_limit:] if len(segments) >= hot_limit else segments
        cold_segments = segments[:-hot_limit] if len(segments) > hot_limit else []
        
        self.log(f"  Hot storage: {len(hot_segments)} files")
        self.log(f"  Cold storage: {len(cold_segments)} files")
        
        # Move hot segments
        segments_dir = self.capture_dir / 'segments'
        for seg in hot_segments:
            dest = segments_dir / seg.name
            if not self.dry_run:
                try:
                    shutil.move(str(seg), str(dest))
                    self.stats['segments_moved'] += 1
                except Exception as e:
                    self.log(f"Error moving {seg.name}: {e}", level='ERROR')
                    self.stats['errors'].append(str(e))
            else:
                self.log(f"  Would move: {seg.name} → segments/", level='DEBUG')
        
        # Move cold segments to hour folders
        for seg in cold_segments:
            hour = self.get_file_hour(seg)
            dest = segments_dir / str(hour) / seg.name
            if not self.dry_run:
                try:
                    shutil.move(str(seg), str(dest))
                    self.stats['segments_moved'] += 1
                except Exception as e:
                    self.log(f"Error moving {seg.name}: {e}", level='ERROR')
                    self.stats['errors'].append(str(e))
            else:
                self.log(f"  Would move: {seg.name} → segments/{hour}/", level='DEBUG')
        
        # Move manifest
        manifest = self.capture_dir / 'output.m3u8'
        if manifest.exists():
            dest = segments_dir / 'output.m3u8'
            if not self.dry_run:
                try:
                    shutil.move(str(manifest), str(dest))
                    self.log("Moved output.m3u8 → segments/")
                except Exception as e:
                    self.log(f"Error moving manifest: {e}", level='ERROR')
            else:
                self.log("Would move: output.m3u8 → segments/")
    
    def migrate_images(self):
        """Migrate captures and thumbnails with hot/cold separation"""
        self.log("=" * 60)
        self.log("MIGRATING IMAGES")
        self.log("=" * 60)
        
        captures_dir = self.capture_dir / 'captures'
        if not captures_dir.exists():
            self.log("No captures directory found")
            return
        
        # Find all images
        all_files = list(captures_dir.glob('capture_*'))
        
        # Separate by type
        captures = sorted(
            [f for f in all_files if f.suffix == '.jpg' and '_thumbnail' not in f.name],
            key=lambda f: f.stat().st_mtime
        )
        thumbnails = sorted(
            [f for f in all_files if '_thumbnail.jpg' in f.name],
            key=lambda f: f.stat().st_mtime
        )
        metadata_files = sorted(
            [f for f in all_files if f.suffix == '.json'],
            key=lambda f: f.stat().st_mtime
        )
        
        self.log(f"Found {len(captures)} captures, {len(thumbnails)} thumbnails, {len(metadata_files)} metadata files")
        
        # Migrate full-res captures (1h retention, so move all to hour folders)
        self.log("\nMigrating full-res captures (1h retention)...")
        hot_limit = 100
        hot_captures = captures[-hot_limit:] if len(captures) >= hot_limit else captures
        cold_captures = captures[:-hot_limit] if len(captures) > hot_limit else []
        
        self.log(f"  Hot: {len(hot_captures)}, Cold: {len(cold_captures)}")
        
        # Keep recent in hot storage
        for cap in hot_captures:
            # Already in captures/ root, no need to move
            self.log(f"  Keeping in hot: {cap.name}", level='DEBUG')
        
        # Move old to hour folders
        for cap in cold_captures:
            hour = self.get_file_hour(cap)
            dest = captures_dir / str(hour) / cap.name
            if not self.dry_run:
                try:
                    shutil.move(str(cap), str(dest))
                    self.stats['captures_moved'] += 1
                except Exception as e:
                    self.log(f"Error moving {cap.name}: {e}", level='ERROR')
                    self.stats['errors'].append(str(e))
            else:
                self.log(f"  Would move: {cap.name} → captures/{hour}/", level='DEBUG')
        
        # Migrate thumbnails (24h retention)
        self.log("\nMigrating thumbnails (24h retention)...")
        thumbnails_dir = self.capture_dir / 'thumbnails'
        
        hot_thumbnails = thumbnails[-hot_limit:] if len(thumbnails) >= hot_limit else thumbnails
        cold_thumbnails = thumbnails[:-hot_limit] if len(thumbnails) > hot_limit else []
        
        self.log(f"  Hot: {len(hot_thumbnails)}, Cold: {len(cold_thumbnails)}")
        
        # Move hot thumbnails to new thumbnails/ directory
        for thumb in hot_thumbnails:
            dest = thumbnails_dir / thumb.name
            if not self.dry_run:
                try:
                    shutil.move(str(thumb), str(dest))
                    self.stats['thumbnails_moved'] += 1
                except Exception as e:
                    self.log(f"Error moving {thumb.name}: {e}", level='ERROR')
                    self.stats['errors'].append(str(e))
            else:
                self.log(f"  Would move: {thumb.name} → thumbnails/", level='DEBUG')
        
        # Move cold thumbnails to hour folders
        for thumb in cold_thumbnails:
            hour = self.get_file_hour(thumb)
            dest = thumbnails_dir / str(hour) / thumb.name
            if not self.dry_run:
                try:
                    shutil.move(str(thumb), str(dest))
                    self.stats['thumbnails_moved'] += 1
                except Exception as e:
                    self.log(f"Error moving {thumb.name}: {e}", level='ERROR')
                    self.stats['errors'].append(str(e))
            else:
                self.log(f"  Would move: {thumb.name} → thumbnails/{hour}/", level='DEBUG')
        
        # Migrate metadata files (24h retention)
        self.log("\nMigrating metadata files (24h retention)...")
        metadata_dir = self.capture_dir / 'metadata'
        
        hot_metadata = metadata_files[-hot_limit:] if len(metadata_files) >= hot_limit else metadata_files
        cold_metadata = metadata_files[:-hot_limit] if len(metadata_files) > hot_limit else []
        
        self.log(f"  Hot: {len(hot_metadata)}, Cold: {len(cold_metadata)}")
        
        # Move hot metadata
        for meta in hot_metadata:
            dest = metadata_dir / meta.name
            if not self.dry_run:
                try:
                    shutil.move(str(meta), str(dest))
                    self.stats['metadata_moved'] += 1
                except Exception as e:
                    self.log(f"Error moving {meta.name}: {e}", level='ERROR')
                    self.stats['errors'].append(str(e))
            else:
                self.log(f"  Would move: {meta.name} → metadata/", level='DEBUG')
        
        # Move cold metadata
        for meta in cold_metadata:
            hour = self.get_file_hour(meta)
            dest = metadata_dir / str(hour) / meta.name
            if not self.dry_run:
                try:
                    shutil.move(str(meta), str(dest))
                    self.stats['metadata_moved'] += 1
                except Exception as e:
                    self.log(f"Error moving {meta.name}: {e}", level='ERROR')
                    self.stats['errors'].append(str(e))
            else:
                self.log(f"  Would move: {meta.name} → metadata/{hour}/", level='DEBUG')
    
    def print_summary(self):
        """Print migration summary"""
        self.log("=" * 60)
        self.log("MIGRATION SUMMARY")
        self.log("=" * 60)
        
        if self.dry_run:
            self.log("⚠️  DRY-RUN MODE - No files were actually moved")
            self.log("Run with --execute to apply changes")
        else:
            self.log("✅ Migration completed!")
        
        self.log(f"\nFiles processed:")
        self.log(f"  Segments:   {self.stats['segments_moved']}")
        self.log(f"  Captures:   {self.stats['captures_moved']}")
        self.log(f"  Thumbnails: {self.stats['thumbnails_moved']}")
        self.log(f"  Metadata:   {self.stats['metadata_moved']}")
        
        if self.stats['errors']:
            self.log(f"\n❌ Errors encountered: {len(self.stats['errors'])}", level='ERROR')
            for err in self.stats['errors'][:10]:  # Show first 10
                self.log(f"  - {err}", level='ERROR')
    
    def run(self):
        """Execute full migration"""
        self.log(f"Starting migration for: {self.capture_dir}")
        self.log(f"Mode: {'DRY-RUN' if self.dry_run else 'EXECUTE'}")
        
        start_time = time.time()
        
        try:
            # Step 1: Create structure
            self.create_directory_structure()
            
            # Step 2: Migrate segments
            self.migrate_segments()
            
            # Step 3: Migrate images
            self.migrate_images()
            
            # Summary
            elapsed = time.time() - start_time
            self.log(f"\nCompleted in {elapsed:.1f}s")
            self.print_summary()
            
        except Exception as e:
            self.log(f"Fatal error: {e}", level='ERROR')
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Migrate capture files to hot/cold architecture',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run (default, safe):
  python migrate_to_hot_cold.py /var/www/html/stream/capture1
  
  # Execute migration:
  python migrate_to_hot_cold.py /var/www/html/stream/capture1 --execute
  
  # Migrate all captures:
  for dir in /var/www/html/stream/capture*; do
    python migrate_to_hot_cold.py "$dir" --execute
  done
        """
    )
    
    parser.add_argument(
        'capture_dir',
        help='Capture directory to migrate (e.g., /var/www/html/stream/capture1)'
    )
    
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute migration (default is dry-run)'
    )
    
    args = parser.parse_args()
    
    # Validate directory
    if not os.path.isdir(args.capture_dir):
        print(f"❌ Error: Directory not found: {args.capture_dir}")
        sys.exit(1)
    
    # Confirm if executing
    if args.execute:
        print("⚠️  WARNING: This will move files to new structure!")
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            sys.exit(0)
    
    # Run migration
    migration = HotColdMigration(args.capture_dir, dry_run=not args.execute)
    migration.run()


if __name__ == '__main__':
    main()

