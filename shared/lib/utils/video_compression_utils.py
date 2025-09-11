#!/usr/bin/env python3

"""
Video Compression Utilities for VirtualPyTest

Compress HLS segments into single MP4 files before upload to reduce:
- Number of files (184 segments -> 1 MP4)
- Total file size (better compression)
- Upload time and bandwidth
- Storage costs
"""

import os
import subprocess
import tempfile
import time
from typing import Optional, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class VideoCompressionUtils:
    """Utilities for compressing video files before upload."""
    
    @staticmethod
    def compress_hls_to_mp4(
        m3u8_path: str,
        segment_files: List[Tuple[str, str]],
        output_path: str = None,
        compression_level: str = "medium"
    ) -> Dict[str, any]:
        """
        Convert HLS segments to a single compressed MP4.
        
        Args:
            m3u8_path: Path to M3U8 playlist file
            segment_files: List of (segment_name, segment_path) tuples
            output_path: Output MP4 path (auto-generated if None)
            compression_level: "fast", "medium", "high" compression
            
        Returns:
            Dict with success status, output path, and compression stats
        """
        try:
            if not segment_files:
                return {'success': False, 'error': 'No segments provided'}
            
            # Generate output path if not provided
            if output_path is None:
                timestamp = int(time.time())
                output_path = f"/tmp/compressed_video_{timestamp}.mp4"
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Get compression settings
            settings = VideoCompressionUtils._get_compression_settings(compression_level)
            
            # Create temporary concat file for FFmpeg
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as concat_file:
                for segment_name, segment_path in segment_files:
                    if os.path.exists(segment_path):
                        concat_file.write(f"file '{segment_path}'\n")
                concat_file_path = concat_file.name
            
            try:
                # Calculate original size
                original_size = sum(
                    os.path.getsize(segment_path) 
                    for _, segment_path in segment_files 
                    if os.path.exists(segment_path)
                )
                
                # FFmpeg command to concatenate and compress
                cmd = [
                    'ffmpeg', '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_file_path,
                    '-c:v', 'libx264',
                    '-preset', settings['preset'],
                    '-crf', str(settings['crf']),
                    '-maxrate', settings['maxrate'],
                    '-bufsize', settings['bufsize'],
                    '-c:a', 'aac',
                    '-b:a', '64k',
                    '-movflags', '+faststart',  # Optimize for streaming
                    output_path
                ]
                
                logger.info(f"Compressing {len(segment_files)} HLS segments to MP4...")
                logger.info(f"Command: {' '.join(cmd)}")
                
                # Run FFmpeg compression
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode != 0:
                    logger.error(f"FFmpeg compression failed: {result.stderr}")
                    return {
                        'success': False,
                        'error': f'FFmpeg failed: {result.stderr}'
                    }
                
                # Calculate compression stats
                if os.path.exists(output_path):
                    compressed_size = os.path.getsize(output_path)
                    compression_ratio = (original_size - compressed_size) / original_size * 100
                    
                    logger.info(f"Compression complete:")
                    logger.info(f"  Original: {original_size / 1024 / 1024:.1f} MB ({len(segment_files)} segments)")
                    logger.info(f"  Compressed: {compressed_size / 1024 / 1024:.1f} MB (1 file)")
                    logger.info(f"  Savings: {compression_ratio:.1f}%")
                    
                    return {
                        'success': True,
                        'output_path': output_path,
                        'original_size': original_size,
                        'compressed_size': compressed_size,
                        'compression_ratio': compression_ratio,
                        'segments_count': len(segment_files)
                    }
                else:
                    return {'success': False, 'error': 'Output file not created'}
                    
            finally:
                # Clean up temp concat file
                if os.path.exists(concat_file_path):
                    os.unlink(concat_file_path)
                    
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Compression timeout (>5 minutes)'}
        except Exception as e:
            logger.error(f"Video compression error: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _get_compression_settings(level: str) -> Dict[str, any]:
        """Get FFmpeg settings for different compression levels."""
        settings = {
            'fast': {
                'preset': 'veryfast',
                'crf': 28,
                'maxrate': '1000k',
                'bufsize': '2000k'
            },
            'medium': {
                'preset': 'medium',
                'crf': 23,
                'maxrate': '800k',
                'bufsize': '1600k'
            },
            'high': {
                'preset': 'slow',
                'crf': 20,
                'maxrate': '600k',
                'bufsize': '1200k'
            }
        }
        return settings.get(level, settings['medium'])
    
    @staticmethod
    def estimate_compression_time(segment_count: int, duration_seconds: float) -> float:
        """
        Estimate compression time based on segment count and duration.
        
        Args:
            segment_count: Number of HLS segments
            duration_seconds: Total video duration
            
        Returns:
            Estimated compression time in seconds
        """
        # Rough estimate: ~0.1x realtime for medium compression
        # (3 minutes of video = ~18 seconds compression time)
        base_time = duration_seconds * 0.1
        
        # Add overhead for segment processing
        segment_overhead = segment_count * 0.05  # 50ms per segment
        
        return base_time + segment_overhead
    
    @staticmethod
    def cleanup_segments_after_compression(segment_files: List[Tuple[str, str]]) -> int:
        """
        DEPRECATED: Do not clean up HLS segments - they're needed for live streaming.
        This function is kept for compatibility but does nothing.
        
        Args:
            segment_files: List of (segment_name, segment_path) tuples
            
        Returns:
            Always returns 0 (no files deleted)
        """
        logger.info("Segment cleanup skipped - HLS segments preserved for live streaming")
        return 0

def compress_video_for_upload(
    m3u8_path: str,
    segment_files: List[Tuple[str, str]],
    compression_level: str = "medium"
) -> Optional[str]:
    """
    Convenience function to compress HLS video for upload.
    
    Args:
        m3u8_path: Path to M3U8 playlist
        segment_files: List of segment files
        compression_level: Compression quality level
        
    Returns:
        Path to compressed MP4 file, or None if failed
    """
    compressor = VideoCompressionUtils()
    result = compressor.compress_hls_to_mp4(
        m3u8_path=m3u8_path,
        segment_files=segment_files,
        compression_level=compression_level
    )
    
    if result['success']:
        logger.info(f"Video compressed successfully: {result['compression_ratio']:.1f}% savings")
        return result['output_path']
    else:
        logger.error(f"Video compression failed: {result['error']}")
        return None
