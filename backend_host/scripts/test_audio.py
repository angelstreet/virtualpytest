#!/usr/bin/env python3
"""
Test script for audio detection optimization
Tests FFmpeg audio analysis on sample TS files to find fastest method

Usage:
    python3 test_audio.py
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_ffmpeg_method_1_current(ts_file):
    """
    Current production method - Uses detect_audio_level from shared utils
    This is what's currently running in detector.py
    """
    start = time.perf_counter()
    
    try:
        from shared.src.lib.utils.audio_transcription_utils import detect_audio_level
        has_audio, volume_percentage, mean_volume = detect_audio_level(ts_file, device_id="")
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return {
            'success': True,
            'has_audio': has_audio,
            'volume_percentage': volume_percentage,
            'mean_volume_db': mean_volume,
            'time_ms': elapsed,
            'method': 'Current (detect_audio_level)'
        }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            'success': False,
            'error': str(e),
            'time_ms': elapsed,
            'method': 'Current (detect_audio_level)'
        }


def test_ffmpeg_method_2_volumedetect(ts_file):
    """
    Alternative method - Direct FFmpeg volumedetect filter (faster?)
    Analyzes audio volume using FFmpeg's built-in filter
    """
    start = time.perf_counter()
    
    try:
        # FFmpeg command: analyze audio volume without decoding video
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'info',
            '-i', ts_file,
            '-vn',  # Skip video (faster!)
            '-af', 'volumedetect',  # Audio volume detection filter
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Parse output for volume info
        # Example: [Parsed_volumedetect_0 @ 0x...] mean_volume: -25.3 dB
        output = result.stderr
        
        has_audio = False
        mean_volume = -100.0
        max_volume = -100.0
        
        for line in output.split('\n'):
            if 'mean_volume:' in line:
                try:
                    mean_volume = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                    has_audio = mean_volume > -50.0  # Threshold: -50dB
                except:
                    pass
            if 'max_volume:' in line:
                try:
                    max_volume = float(line.split('max_volume:')[1].split('dB')[0].strip())
                except:
                    pass
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return {
            'success': True,
            'has_audio': has_audio,
            'mean_volume_db': mean_volume,
            'max_volume_db': max_volume,
            'time_ms': elapsed,
            'method': 'FFmpeg volumedetect (no video)'
        }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            'success': False,
            'error': str(e),
            'time_ms': elapsed,
            'method': 'FFmpeg volumedetect (no video)'
        }


def test_ffmpeg_method_3_astats(ts_file):
    """
    Alternative method - FFmpeg astats filter (most detailed, but slower?)
    Provides detailed audio statistics
    """
    start = time.perf_counter()
    
    try:
        # FFmpeg command: detailed audio stats
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'info',
            '-i', ts_file,
            '-vn',  # Skip video
            '-af', 'astats',  # Audio statistics filter
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Parse output for RMS level
        # Example: [Parsed_astats_0 @ 0x...] RMS level dB: -25.3
        output = result.stderr
        
        has_audio = False
        rms_db = -100.0
        
        for line in output.split('\n'):
            if 'RMS level dB:' in line:
                try:
                    rms_db = float(line.split('RMS level dB:')[1].strip().split()[0])
                    has_audio = rms_db > -50.0  # Threshold: -50dB
                except:
                    pass
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return {
            'success': True,
            'has_audio': has_audio,
            'rms_db': rms_db,
            'time_ms': elapsed,
            'method': 'FFmpeg astats (detailed)'
        }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            'success': False,
            'error': str(e),
            'time_ms': elapsed,
            'method': 'FFmpeg astats (detailed)'
        }


def test_ffmpeg_method_4_fast_sample(ts_file):
    """
    Optimized method - Analyze only first 0.5 seconds for speed
    Sample a small portion to detect audio quickly
    """
    start = time.perf_counter()
    
    try:
        # FFmpeg command: analyze only first 0.5 seconds
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'info',
            '-i', ts_file,
            '-t', '0.5',  # Only first 0.5 seconds!
            '-vn',  # Skip video
            '-af', 'volumedetect',
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Parse output
        output = result.stderr
        
        has_audio = False
        mean_volume = -100.0
        
        for line in output.split('\n'):
            if 'mean_volume:' in line:
                try:
                    mean_volume = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                    has_audio = mean_volume > -50.0
                except:
                    pass
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return {
            'success': True,
            'has_audio': has_audio,
            'mean_volume_db': mean_volume,
            'time_ms': elapsed,
            'method': 'Fast sample (0.5s only)'
        }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            'success': False,
            'error': str(e),
            'time_ms': elapsed,
            'method': 'Fast sample (0.5s only)'
        }


def print_result(filename, results):
    """Print test results in clean format"""
    print(f"\n{'='*70}")
    print(f"🔊 {filename}")
    print(f"{'='*70}")
    
    for i, result in enumerate(results, 1):
        method = result.get('method', 'Unknown')
        time_ms = result.get('time_ms', 0)
        
        if result.get('success'):
            has_audio = result.get('has_audio', False)
            status = '✅ AUDIO' if has_audio else '🔇 MUTE'
            
            print(f"\n{i}. {method} ({time_ms:.0f}ms) → {status}")
            
            # Show volume details if available
            if 'mean_volume_db' in result:
                print(f"   Mean volume: {result['mean_volume_db']:.1f} dB")
            if 'max_volume_db' in result:
                print(f"   Max volume: {result['max_volume_db']:.1f} dB")
            if 'rms_db' in result:
                print(f"   RMS level: {result['rms_db']:.1f} dB")
            if 'volume_percentage' in result:
                print(f"   Volume %: {result['volume_percentage']:.0f}%")
        else:
            error = result.get('error', 'Unknown error')
            print(f"\n{i}. {method} ({time_ms:.0f}ms) → ❌ ERROR")
            print(f"   {error}")


def main():
    """Test all methods on both audio files"""
    
    # Get script directory
    script_dir = Path(__file__).parent
    audio_dir = script_dir / 'audio'
    
    if not audio_dir.exists():
        print(f"❌ Error: Audio directory not found: {audio_dir}")
        return 1
    
    # Find test files
    audio_file = audio_dir / 'audio.ts'
    mute_file = audio_dir / 'mute.ts'
    
    test_files = []
    if audio_file.exists():
        test_files.append(audio_file)
    if mute_file.exists():
        test_files.append(mute_file)
    
    if not test_files:
        print(f"❌ Error: No test files found in {audio_dir}")
        print("   Expected: audio.ts and/or mute.ts")
        return 1
    
    print("\n" + "="*70)
    print("🚀 AUDIO DETECTION OPTIMIZATION TEST")
    print("="*70)
    print(f"Testing {len(test_files)} files from {audio_dir}")
    print("\nMethods:")
    print("  1. Current production method (detect_audio_level)")
    print("  2. FFmpeg volumedetect (skip video)")
    print("  3. FFmpeg astats (detailed stats)")
    print("  4. Fast sample (0.5s only)")
    
    # Test each file with all methods
    all_results = {}
    
    for test_file in test_files:
        filename = test_file.name
        
        results = [
            test_ffmpeg_method_1_current(str(test_file)),
            test_ffmpeg_method_2_volumedetect(str(test_file)),
            test_ffmpeg_method_3_astats(str(test_file)),
            test_ffmpeg_method_4_fast_sample(str(test_file))
        ]
        
        all_results[filename] = results
        print_result(filename, results)
    
    # Summary: Find fastest method
    print(f"\n{'='*70}")
    print("📊 SUMMARY - Speed Comparison")
    print(f"{'='*70}")
    
    # Calculate average time per method across all files
    method_times = {}
    for filename, results in all_results.items():
        for result in results:
            if result.get('success'):
                method = result['method']
                time_ms = result['time_ms']
                if method not in method_times:
                    method_times[method] = []
                method_times[method].append(time_ms)
    
    # Sort by average time (fastest first)
    avg_times = {method: sum(times)/len(times) for method, times in method_times.items()}
    sorted_methods = sorted(avg_times.items(), key=lambda x: x[1])
    
    print("\nRanking (fastest to slowest):")
    for rank, (method, avg_time) in enumerate(sorted_methods, 1):
        speedup = sorted_methods[0][1] / avg_time if rank > 1 else 1.0
        speedup_str = f" ({speedup:.1f}x slower)" if rank > 1 else " ⚡ FASTEST"
        print(f"  {rank}. {method}: {avg_time:.0f}ms{speedup_str}")
    
    # Recommendation
    print("\n💡 RECOMMENDATION:")
    fastest_method = sorted_methods[0][0]
    fastest_time = sorted_methods[0][1]
    current_time = avg_times.get('Current (detect_audio_level)', 0)
    
    if fastest_time < current_time:
        speedup = current_time / fastest_time
        savings = current_time - fastest_time
        print(f"   Switch to: {fastest_method}")
        print(f"   Savings: {savings:.0f}ms per check ({speedup:.1f}x faster)")
        print(f"   Impact: With 5s caching, saves ~{savings:.0f}ms every 5 seconds per device")
    else:
        print(f"   Current method is already optimal!")
    
    print(f"\n✅ Test complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())

