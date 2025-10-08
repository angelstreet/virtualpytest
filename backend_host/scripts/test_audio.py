#!/usr/bin/env python3
"""
Test script for audio detection optimization
Tests fast FFmpeg audio analysis on all TS files in audio/ directory

Usage:
    python3 test_audio.py
"""

import sys
import time
import subprocess
from pathlib import Path


def test_fast_sample(ts_file):
    """Fast sample - Analyze only first 0.5 seconds"""
    start = time.perf_counter()
    
    try:
        cmd = [
            'ffmpeg', '-hide_banner', '-loglevel', 'info',
            '-i', ts_file, '-t', '0.5', '-vn',
            '-af', 'volumedetect', '-f', 'null', '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        has_audio = False
        mean_volume = -100.0
        
        for line in result.stderr.split('\n'):
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
            'method': 'Fast (0.5s)'
        }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            'success': False,
            'error': str(e),
            'time_ms': elapsed,
            'method': 'Fast (0.5s)'
        }


def test_ultrafast_sample(ts_file):
    """Ultrafast sample - Analyze only first 0.1 seconds"""
    start = time.perf_counter()
    
    try:
        cmd = [
            'ffmpeg', '-hide_banner', '-loglevel', 'info',
            '-i', ts_file, '-t', '0.1', '-vn',
            '-af', 'volumedetect', '-f', 'null', '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
        
        has_audio = False
        mean_volume = -100.0
        
        for line in result.stderr.split('\n'):
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
            'method': 'Ultrafast (0.1s)'
        }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            'success': False,
            'error': str(e),
            'time_ms': elapsed,
            'method': 'Ultrafast (0.1s)'
        }


def print_result(filename, results):
    """Print test results"""
    print(f"\n{'='*70}")
    print(f"🔊 {filename}")
    print(f"{'='*70}")
    
    for i, result in enumerate(results, 1):
        method = result.get('method', 'Unknown')
        time_ms = result.get('time_ms', 0)
        
        if result.get('success'):
            has_audio = result.get('has_audio', False)
            status = '✅ AUDIO' if has_audio else '🔇 MUTE'
            mean_volume_db = result.get('mean_volume_db', -100.0)
            
            print(f"{i}. {method:15} ({time_ms:4.0f}ms) → {status} | {mean_volume_db:.1f} dB")
        else:
            error = result.get('error', 'Unknown error')
            print(f"{i}. {method:15} ({time_ms:4.0f}ms) → ❌ ERROR: {error}")


def main():
    """Test fast methods on all TS files in audio/ directory"""
    
    script_dir = Path(__file__).parent
    audio_dir = script_dir / 'audio'
    
    if not audio_dir.exists():
        print(f"❌ Error: Audio directory not found: {audio_dir}")
        return 1
    
    # Find all .ts files
    test_files = sorted(audio_dir.glob('*.ts'))
    
    if not test_files:
        print(f"❌ Error: No .ts files found in {audio_dir}")
        return 1
    
    print("\n" + "="*70)
    print("🚀 AUDIO DETECTION TEST")
    print("="*70)
    print(f"Testing {len(test_files)} files from {audio_dir.name}/")
    print("Methods: Fast (0.5s) | Ultrafast (0.1s)")
    
    # Test each file
    all_results = {}
    
    for test_file in test_files:
        filename = test_file.name
        
        results = [
            test_fast_sample(str(test_file)),
            test_ultrafast_sample(str(test_file))
        ]
        
        all_results[filename] = results
        print_result(filename, results)
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 SUMMARY")
    print(f"{'='*70}")
    
    method_times = {}
    for filename, results in all_results.items():
        for result in results:
            if result.get('success'):
                method = result['method']
                time_ms = result['time_ms']
                if method not in method_times:
                    method_times[method] = []
                method_times[method].append(time_ms)
    
    print("\nAverage times:")
    for method, times in method_times.items():
        avg_time = sum(times) / len(times)
        print(f"  {method:15} {avg_time:5.0f}ms")
    
    print(f"\n✅ Test complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())

