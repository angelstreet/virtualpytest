#!/usr/bin/env python3
"""
Manual script to rebuild archive manifests from existing chunks on disk.
Run this to rediscover all existing chunks when manifest is lost/incomplete.
"""

import os
import sys
import json
import logging
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from shared.src.lib.utils.storage_path_utils import get_capture_base_directories

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [REBUILD_MANIFESTS] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def rebuild_archive_manifest_from_disk(capture_dir: str) -> dict:
    """
    Scan all hour directories and rebuild manifest from existing chunk files.
    """
    segments_dir = os.path.join(capture_dir, 'segments')
    chunks = []
    
    if not os.path.isdir(segments_dir):
        return {"chunks": [], "last_updated": None, "available_hours": [], "total_chunks": 0}
    
    # Scan all hour directories (0-23)
    for hour in range(24):
        hour_dir = os.path.join(segments_dir, str(hour))
        if not os.path.isdir(hour_dir):
            continue
        
        # Find all chunk MP4 files
        for mp4_file in Path(hour_dir).glob('chunk_10min_*.mp4'):
            try:
                # Extract chunk index from filename
                chunk_index = int(mp4_file.stem.replace('chunk_10min_', ''))
                mp4_stat = mp4_file.stat()
                
                # Check for corresponding metadata
                metadata_path = os.path.join(capture_dir, 'metadata', str(hour), f'chunk_10min_{chunk_index}.json')
                has_metadata = os.path.exists(metadata_path)
                
                chunk_info = {
                    "hour": hour,
                    "chunk_index": chunk_index,
                    "name": mp4_file.name,
                    "size": mp4_stat.st_size,
                    "created": mp4_stat.st_mtime,
                    "has_metadata": has_metadata
                }
                
                # Add metadata details if available
                if has_metadata:
                    try:
                        with open(metadata_path) as f:
                            meta = json.load(f)
                        chunk_info.update({
                            "start_time": meta.get("start_time"),
                            "end_time": meta.get("end_time"),
                            "frames_count": meta.get("frames_count")
                        })
                    except:
                        pass
                
                chunks.append(chunk_info)
                logger.debug(f"Found chunk: hour={hour}, index={chunk_index}, size={mp4_stat.st_size}")
                
            except Exception as e:
                logger.warning(f"Error processing chunk file {mp4_file}: {e}")
    
    # Build complete manifest
    chunks.sort(key=lambda x: (x["hour"], x["chunk_index"]))
    manifest = {
        "chunks": chunks,
        "last_updated": os.times().elapsed,
        "available_hours": sorted(list(set(c["hour"] for c in chunks))),
        "total_chunks": len(chunks)
    }
    
    return manifest


def main():
    logger.info("=" * 60)
    logger.info("REBUILD ARCHIVE MANIFESTS FROM DISK")
    logger.info("=" * 60)
    
    capture_dirs = get_capture_base_directories()
    logger.info(f"Found {len(capture_dirs)} capture directories")
    logger.info("")
    
    for capture_dir in capture_dirs:
        try:
            logger.info(f"Processing: {capture_dir}")
            
            # Rebuild manifest from disk
            manifest = rebuild_archive_manifest_from_disk(capture_dir)
            manifest_path = os.path.join(capture_dir, 'segments', 'archive_manifest.json')
            
            # Show what was found
            if manifest['total_chunks'] == 0:
                logger.info(f"  No chunks found")
            else:
                logger.info(f"  Found {manifest['total_chunks']} chunks across {len(manifest['available_hours'])} hours")
                for hour in manifest['available_hours']:
                    hour_chunks = [c for c in manifest['chunks'] if c['hour'] == hour]
                    total_size = sum(c['size'] for c in hour_chunks)
                    logger.info(f"    Hour {hour:02d}: {len(hour_chunks)} chunks, {total_size / 1024 / 1024:.1f} MB")
            
            # Save manifest
            os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
            with open(manifest_path + '.tmp', 'w') as f:
                json.dump(manifest, f, indent=2)
            os.rename(manifest_path + '.tmp', manifest_path)
            
            logger.info(f"  ✓ Saved manifest to {manifest_path}")
            logger.info("")
            
        except Exception as e:
            logger.error(f"Error processing {capture_dir}: {e}", exc_info=True)
    
    logger.info("=" * 60)
    logger.info("DONE")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
