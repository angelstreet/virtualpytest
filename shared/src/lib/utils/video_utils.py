"""
Video Utilities for VirtualPyTest

Generic video operations: merging, compression, extraction
Reused by: hot_cold_archiver, video_compression_utils, audio_transcription_utils
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple


def merge_video_files(
    input_files: List[str],
    output_path: str,
    output_format: str = 'mp4',
    delete_source: bool = False,
    timeout: int = 30,
    compression_settings: Dict[str, Any] = None,
    skip_faststart: bool = False
) -> Optional[str]:
    """
    Generic video file merger using FFmpeg concat demuxer
    
    Args:
        input_files: List of video file paths to merge
        output_path: Path for output file
        output_format: Output format ('mp4' or 'ts')
        delete_source: Delete source files after successful merge
        timeout: FFmpeg timeout in seconds
        compression_settings: Optional compression settings (preset, crf, maxrate, etc.)
        skip_faststart: Skip -movflags +faststart (faster on slow disks like SD cards)
        
    Returns:
        Output path if successful, None otherwise
    """
    if not input_files:
        return None
    
    if len(input_files) == 1:
        return input_files[0]
    
    concat_file = f"{output_path}.concat.txt"
    
    try:
        with open(concat_file, 'w') as f:
            for video_file in input_files:
                f.write(f"file '{video_file}'\n")
        
        cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file]
        
        if compression_settings:
            cmd.extend(['-c:v', 'libx264'])
            cmd.extend(['-preset', compression_settings.get('preset', 'medium')])
            cmd.extend(['-crf', str(compression_settings.get('crf', 23))])
            cmd.extend(['-maxrate', compression_settings.get('maxrate', '800k')])
            cmd.extend(['-bufsize', compression_settings.get('bufsize', '1600k')])
            if 'fps' in compression_settings:
                cmd.extend(['-vf', f'fps={compression_settings["fps"]}'])
            cmd.extend(['-c:a', 'aac', '-b:a', '64k'])
        else:
            # Copy all streams (video + audio) without re-encoding
            cmd.extend(['-c:v', 'copy', '-c:a', 'copy'])
        
        if output_format == 'mp4' and not skip_faststart:
            cmd.extend(['-movflags', '+faststart'])
        
        # Explicitly specify output format to avoid issues with .tmp or non-standard extensions
        cmd.extend(['-f', output_format])
        cmd.append(output_path)
        
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        
        if result.returncode == 0 and os.path.exists(output_path):
            os.remove(concat_file)
            
            if delete_source:
                for file_path in input_files:
                    try:
                        os.remove(file_path)
                    except:
                        pass
            
            return output_path
        else:
            # Log FFmpeg failure details
            stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else 'No stderr'
            print(f"[video_utils] FFmpeg merge failed (returncode={result.returncode})")
            print(f"[video_utils] FFmpeg stderr: {stderr[-500:]}")  # Last 500 chars
            return None
        
    except subprocess.TimeoutExpired as e:
        print(f"[video_utils] FFmpeg merge timeout after {timeout}s")
        return None
    except Exception as e:
        print(f"[video_utils] FFmpeg merge exception: {e}")
        return None
    finally:
        if os.path.exists(concat_file):
            try:
                os.remove(concat_file)
            except:
                pass


def get_compression_settings(level: str) -> Dict[str, Any]:
    """Get FFmpeg compression settings for different quality levels"""
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
        },
        'low': {
            'preset': 'ultrafast',
            'crf': 30,
            'maxrate': '500k',
            'bufsize': '1000k'
        },
        'pi_optimized': {
            'preset': 'ultrafast',
            'crf': 30,
            'maxrate': '500k',
            'bufsize': '1000k',
            'fps': 15
        }
    }
    return settings.get(level, settings['medium'])


def compress_video_segments(
    segment_files: List[Tuple[str, str]],
    output_path: str,
    compression_level: str = "medium"
) -> Dict[str, Any]:
    """
    Compress video segments to single MP4 with optional quality settings
    
    Args:
        segment_files: List of (segment_name, segment_path) tuples
        output_path: Output MP4 path
        compression_level: "fast", "medium", "high", "low", "pi_optimized"
        
    Returns:
        Dict with success status, output path, and compression stats
    """
    try:
        if not segment_files:
            return {'success': False, 'error': 'No segments provided'}
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        original_size = sum(
            os.path.getsize(segment_path) 
            for _, segment_path in segment_files 
            if os.path.exists(segment_path)
        )
        
        file_paths = [segment_path for _, segment_path in segment_files]
        compression_settings = get_compression_settings(compression_level)
        
        result_path = merge_video_files(
            file_paths,
            output_path,
            'mp4',
            False,
            300,
            compression_settings
        )
        
        if result_path and os.path.exists(result_path):
            compressed_size = os.path.getsize(result_path)
            compression_ratio = (original_size - compressed_size) / original_size * 100
            
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
            
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Compression timeout (>5 minutes)'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def merge_progressive_batch(
    source_dir: str,
    source_pattern: str,
    output_path: str,
    count: int,
    delete_source: bool = True,
    timeout: int = 30
) -> Optional[str]:
    """
    Find video files matching pattern, merge N oldest into single file
    
    Generic progressive merge: finds files, sorts by time, merges batch
    Used for progressive grouping: 6s→1min→10min→1h
    
    Args:
        source_dir: Directory to search for files
        source_pattern: Glob pattern (e.g., 'segment_*.ts', '6s_*.mp4')
        output_path: Output file path
        count: Number of files to merge
        delete_source: Delete source files after merge
        timeout: FFmpeg timeout in seconds
        
    Returns:
        Output path if successful, None otherwise
    """
    if not os.path.isdir(source_dir):
        return None
    
    files = sorted(
        [str(f) for f in Path(source_dir).glob(source_pattern) if f.is_file()],
        key=os.path.getmtime
    )
    
    if len(files) < count:
        return None
    
    return merge_video_files(files[:count], output_path, 'mp4', delete_source, timeout)

