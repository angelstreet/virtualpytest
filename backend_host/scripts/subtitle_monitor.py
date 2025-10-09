#!/usr/bin/env python3
"""
Subtitle OCR Monitor - processes subtitle detection in dedicated process

OPTIMIZATIONS:
- Downscale to 33% (was 50%) → 30% faster OCR
- Binarization (black/white) before OCR → 20% faster  
- Language caching per device (2min) → 2x faster after first detection
- Round-robin processing (1s delay per device)
- LIFO queue (newest frames first, max 10 per device)

EXPECTED PERFORMANCE:
- OCR time: 50-100ms (was 200-300ms)
- Total per frame: 80-150ms (was 300-500ms)
"""

import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'

import sys
import json
import logging
import queue
import threading
import time
import cv2
import numpy as np
import inotify.adapters

import re
from spellchecker import SpellChecker

import inotify.adapters

from shared.src.lib.utils.audio_transcription_utils import clean_transcript_text, correct_spelling, ENABLE_SPELLCHECK

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.src.lib.utils.storage_path_utils import (
    get_capture_base_directories,
    get_capture_folder,
    get_metadata_path,
    get_captures_path
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class InotifySubtitleMonitor:
    def __init__(self, capture_dirs):
        self.inotify = inotify.adapters.Inotify()
        self.path_to_folder = {}
        self.capture_dirs_map = {}
        self.queues = {}
        self.ocr_worker = None
        self.worker_running = False
        
        # Language cache per device: {capture_folder: (timestamp, detected_language)}
        # Reuse language for 2 minutes before detecting again
        self.language_cache = {}
        
        for capture_dir in capture_dirs:
            capture_folder = get_capture_folder(capture_dir)
            metadata_dir = get_metadata_path(capture_folder)
            os.makedirs(metadata_dir, mode=0o777, exist_ok=True)
            
            if os.path.exists(metadata_dir):
                self.inotify.add_watch(metadata_dir)
                self.path_to_folder[metadata_dir] = {
                    'capture_folder': capture_folder,
                    'captures_dir': capture_dir
                }
                self.capture_dirs_map[capture_folder] = capture_dir
                logger.info(f"Watching: {metadata_dir} -> {capture_folder}")
            
            self.queues[capture_folder] = queue.LifoQueue(maxsize=10)
        
        self._start_ocr_worker()
    
    def _start_ocr_worker(self):
        self.worker_running = True
        self.ocr_worker = threading.Thread(
            target=self._round_robin_worker,
            daemon=True,
            name="ocr-worker"
        )
        self.ocr_worker.start()
        logger.info("OCR worker started (33% downscale + binarization + language caching)")
    
    def _round_robin_worker(self):
        devices = list(self.queues.keys())
        if not devices:
            return
        
        device_index = 0
        
        while self.worker_running:
            capture_folder = devices[device_index]
            work_queue = self.queues[capture_folder]
            captures_dir = self.capture_dirs_map[capture_folder]
            
            try:
                json_path = work_queue.get_nowait()
                
                try:
                    self.process_ocr(json_path, captures_dir, capture_folder)
                except Exception as e:
                    logger.error(f"[{capture_folder}] OCR error: {e}")
                
                work_queue.task_done()
                time.sleep(1.0)
                
            except queue.Empty:
                pass
            
            device_index = (device_index + 1) % len(devices)
            time.sleep(0.1)
    
    def process_ocr(self, json_path, captures_dir, capture_folder):
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # New: Skip OCR if no audio detected (CPU optimization)
        if not data.get('audio', True):
            logger.info(f"[{capture_folder}] ⊗ Skip: no audio detected")
            data['subtitle_analysis'] = {
                'has_subtitles': False,
                'extracted_text': '',
                'skipped': True,
                'skip_reason': 'no_audio'
            }
            data['subtitle_ocr_pending'] = False
            
            with open(json_path + '.tmp', 'w') as f:
                json.dump(data, f, indent=2)
            os.rename(json_path + '.tmp', json_path)
            return
        
        frame_file = os.path.basename(json_path).replace('.json', '.jpg')
        
        # Log detection state
        audio = "🔇" if not data.get('audio', True) else "🔊"
        freeze = "❄️" if data.get('freeze', False) else ""
        black = "⬛" if data.get('blackscreen', False) else ""
        logger.info(f"[{capture_folder}] {frame_file} {audio}{freeze}{black}")
        
        if not data.get('subtitle_ocr_pending', False):
            logger.info(f"[{capture_folder}] ⊗ Skip: no OCR pending")
            return
        
        frame_path = os.path.join(captures_dir, frame_file)
        
        if not os.path.exists(frame_path):
            logger.error(f"[{capture_folder}] ⊗ Skip: image deleted")
            return
        
        try:
            start_total = time.perf_counter()
            img = cv2.imread(frame_path, cv2.IMREAD_GRAYSCALE)
            
            if img is None:
                return
            
            img_height, img_width = img.shape
            
            # Edge detection
            start_edge = time.perf_counter()
            edges = cv2.Canny(img, 50, 150)
            subtitle_y = int(img_height * 0.85)
            edges_subtitle = edges[subtitle_y:img_height, :]
            subtitle_edge_density = np.sum(edges_subtitle > 0) / edges_subtitle.size * 100
            edge_time = (time.perf_counter() - start_edge) * 1000
            
            if not (1.5 < subtitle_edge_density < 8):
                logger.info(f"[{capture_folder}] ⊗ Skip: no_edges (density={subtitle_edge_density:.1f}%, {edge_time:.0f}ms)")
                data['subtitle_analysis'] = {
                    'has_subtitles': False,
                    'extracted_text': '',
                    'subtitle_edge_density': round(subtitle_edge_density, 1),
                    'skipped': True,
                    'skip_reason': 'no_edges'
                }
            else:
                # Crop
                start_crop = time.perf_counter()
                x = int(img_width * 0.10)
                y = int(img_height * 0.60)
                w = int(img_width * 0.80)
                h = int(img_height * 0.35)
                crop = img[y:y+h, x:x+w]
                crop_time = (time.perf_counter() - start_crop) * 1000
                
                # Downscale to 33% (was 50%) - 30% faster OCR
                start_down = time.perf_counter()
                crop = cv2.resize(crop, None, fx=0.33, fy=0.33, interpolation=cv2.INTER_AREA)
                down_h, down_w = crop.shape
                down_time = (time.perf_counter() - start_down) * 1000
                
                # Binarization (black/white only) - 20% faster OCR
                start_binarize = time.perf_counter()
                _, crop = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                binarize_time = (time.perf_counter() - start_binarize) * 1000
                
                logger.info(f"[{capture_folder}] ✓ Crop: {w}x{h}@({x},{y}) → {down_w}x{down_h} ({crop_time:.1f}ms + {down_time:.1f}ms + bin={binarize_time:.1f}ms)")
                
                # Get cached language or use default (reuse language for 2 minutes)
                current_time = time.time()
                cached_lang = None
                lang_config = 'eng+deu+fra'  # Default
                
                if capture_folder in self.language_cache:
                    cache_time, cached_lang = self.language_cache[capture_folder]
                    cache_age = current_time - cache_time
                    if cache_age < 120:  # 2 minutes
                        # Use cached language
                        if cached_lang == 'fra':
                            lang_config = 'fra'
                        elif cached_lang == 'deu':
                            lang_config = 'deu'
                        elif cached_lang == 'eng':
                            lang_config = 'eng'
                        logger.debug(f"[{capture_folder}] Using cached language: {cached_lang} (age={cache_age:.0f}s)")
                
                # OCR
                start_ocr = time.perf_counter()
                import pytesseract
                text = pytesseract.image_to_string(
                    crop,
                    config=f'--psm 6 --oem 1 -l {lang_config}',
                    timeout=2
                ).strip()
                ocr_time = (time.perf_counter() - start_ocr) * 1000
                
                # Clean OCR noise
                if text:
                    import re
                    lines = text.split('\n')
                    cleaned = []
                    for line in lines:
                        words = line.split()
                        real = [w for w in words if len(re.sub(r'[^a-zA-Z]', '', w)) >= 3]
                        if real:
                            cleaned.append(line.strip())
                    text = '\n'.join(cleaned).strip()
                
                # New: Apply shared regex-based filter and optional spell correction
                text = clean_transcript_text(text)
                if ENABLE_SPELLCHECK:
                    text = correct_spelling(text, detected_language)
                
                # Detect language if text found and not cached (or cache expired)
                detected_language = None
                if text and len(text) > 10:  # Only detect if meaningful text
                    # Check if we should detect language (no cache or cache expired)
                    should_detect_language = True
                    if capture_folder in self.language_cache:
                        cache_time, cached_lang = self.language_cache[capture_folder]
                        if current_time - cache_time < 120:  # 2 minutes
                            should_detect_language = False
                            detected_language = cached_lang
                    
                    if should_detect_language:
                        # Detect language and cache for 2 minutes
                        start_lang = time.perf_counter()
                        try:
                            from langdetect import detect
                            detected_language = detect(text)
                            # Update cache
                            self.language_cache[capture_folder] = (current_time, detected_language)
                            lang_time = (time.perf_counter() - start_lang) * 1000
                            logger.info(f"[{capture_folder}] 🌐 Detected language: {detected_language} ({lang_time:.0f}ms) - cached for 2min")
                        except Exception as e:
                            detected_language = 'unknown'
                            logger.debug(f"[{capture_folder}] Language detection failed: {e}")
                
                total_time = (time.perf_counter() - start_total) * 1000
                
                data['subtitle_analysis'] = {
                    'has_subtitles': bool(text),
                    'extracted_text': text,
                    'detected_language': detected_language,
                    'subtitle_edge_density': round(subtitle_edge_density, 1),
                    'box': {'x': x, 'y': y, 'width': w, 'height': h},
                    'skipped': False,
                    'ocr_time_ms': round(ocr_time, 2),
                    'downscale_factor': 0.33,
                    'binarized': True
                }
                
                if text:
                    lang_str = f" [{detected_language}]" if detected_language else ""
                    logger.info(f"[{capture_folder}] 📝 Text{lang_str}: {len(text)} chars in {total_time:.0f}ms (OCR={ocr_time:.0f}ms) | '{text[:60]}'")
                else:
                    logger.info(f"[{capture_folder}] ⊗ No text (OCR={ocr_time:.0f}ms, total={total_time:.0f}ms)")
        
        except Exception as e:
            data['subtitle_analysis'] = {
                'has_subtitles': False,
                'extracted_text': '',
                'error': str(e)
            }
        
        data['subtitle_ocr_pending'] = False
        
        with open(json_path + '.tmp', 'w') as f:
            json.dump(data, f, indent=2)
        os.rename(json_path + '.tmp', json_path)
    
    def run(self):
        try:
            for event in self.inotify.event_gen(yield_nones=False):
                (_, type_names, path, filename) = event
                
                if 'IN_CLOSE_WRITE' not in type_names and 'IN_MOVED_TO' not in type_names:
                    continue
                
                if not filename.endswith('.json'):
                    continue
                
                if path in self.path_to_folder:
                    capture_folder = self.path_to_folder[path]['capture_folder']
                    json_path = os.path.join(path, filename)
                    work_queue = self.queues[capture_folder]
                    
                    try:
                        work_queue.put_nowait(json_path)
                    except queue.Full:
                        try:
                            work_queue.get_nowait()
                            work_queue.put_nowait(json_path)
                        except:
                            pass
        
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            for path in self.path_to_folder.keys():
                try:
                    self.inotify.remove_watch(path)
                except:
                    pass

def main():
    from shared.src.lib.utils.system_utils import kill_existing_script_instances
    
    killed = kill_existing_script_instances('subtitle_monitor.py')
    if killed:
        logger.info(f"Killed existing instances: {killed}")
        time.sleep(1)
    
    base_dirs = get_capture_base_directories()
    capture_dirs = []
    
    for base_dir in base_dirs:
        device_folder = os.path.basename(base_dir)
        capture_path = get_captures_path(device_folder)
        capture_dirs.append(capture_path)
    
    logger.info("=" * 80)
    logger.info("Subtitle OCR Monitor - OPTIMIZED")
    logger.info("- 33% downscale (89% fewer pixels)")
    logger.info("- Binarization (black/white for faster OCR)")
    logger.info("- Language caching (2min per device)")
    logger.info("=" * 80)
    logger.info(f"Monitoring {len(capture_dirs)} devices (queue: 10 most recent per device)")
    
    monitor = InotifySubtitleMonitor(capture_dirs)
    monitor.run()

if __name__ == '__main__':
    main()

