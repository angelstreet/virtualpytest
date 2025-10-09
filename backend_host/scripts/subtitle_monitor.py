#!/usr/bin/env python3
"""
Subtitle OCR Monitor - processes subtitle detection in dedicated process

OPTIMIZATIONS:
- Skip if freeze/blackscreen/no audio → ~70% fewer OCR calls
- Configurable downscale (default 33% = 89% fewer pixels)
- Optional binarization (black/white) before OCR → ~20% faster  
- Language caching per device (2min) → 2x faster after first detection
- Round-robin processing (1s delay per device)
- LIFO queue (newest frames first, max 10 per device)

DISABLED (too slow for real-time):
- Spell checking (adds 200-500ms per OCR)

PERFORMANCE TUNING:
- Edit DOWNSCALE_FACTOR (line 28) to test different resize percentages
- Edit ENABLE_BINARIZATION (line 29) to toggle black/white conversion
- Edit ENABLE_SPELLCHECK (line 30) to enable/disable spell correction

EXPECTED PERFORMANCE (without spellcheck):
- OCR time: 50-100ms (was 200-300ms)
- Total per frame: 80-150ms (was 300-500ms)

WITH SPELLCHECK ENABLED (adds 200-500ms):
- Corrects misspelled words (e.g., "helo" → "hello")
- Filters garbage text (replaces unknown words)
- Shows corrections in logs with timing
"""

# ============================================================================
# PERFORMANCE TUNING FLAGS
# ============================================================================
DOWNSCALE_FACTOR = 0.5      # Resize factor (0.33 = 33% = 89% fewer pixels, 0.5 = 50% = 75% fewer pixels)
ENABLE_BINARIZATION = False  # Set to False to disable binarization for speed comparison
ENABLE_SPELLCHECK = False    # Set to True to enable spell checking (SLOW: adds 200-500ms per OCR)
# ============================================================================

import os
os.environ['OMP_NUM_THREADS'] = '4'
os.environ['MKL_NUM_THREADS'] = '4'
os.environ['OPENBLAS_NUM_THREADS'] = '4'

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

# Setup project root BEFORE importing from shared
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Now import from shared (after path is set up)
from shared.src.lib.utils.audio_transcription_utils import clean_transcript_text

# Spell checker import (only used if ENABLE_SPELLCHECK=True)
try:
    from spellchecker import SpellChecker
    SPELLCHECKER_AVAILABLE = True
except ImportError:
    SPELLCHECKER_AVAILABLE = False

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
        binarize_status = "ON" if ENABLE_BINARIZATION else "OFF"
        spellcheck_status = "ON" if ENABLE_SPELLCHECK else "OFF"
        downscale_pct = int(DOWNSCALE_FACTOR * 100)
        logger.info(f"OCR worker started (resize={downscale_pct}% + binarization={binarize_status} + spellcheck={spellcheck_status} + language caching)")
    
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
        
        # Skip OCR if no audio detected (no content = no subtitles)
        if not data.get('audio', True):
            logger.info(f"[{capture_folder}] ⊗ SKIP: No audio (no content to subtitle)")
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
        frame_path = os.path.join(captures_dir, frame_file)
        
        # Log detection state with full paths
        audio = "🔇" if not data.get('audio', True) else "🔊"
        freeze = "❄️" if data.get('freeze', False) else ""
        black = "⬛" if data.get('blackscreen', False) else ""
        logger.info(f"[{capture_folder}] Processing frame: {frame_path} {audio}{freeze}{black}")
        logger.info(f"[{capture_folder}]    └─ JSON: {json_path}")
        
        if not data.get('subtitle_ocr_pending', False):
            logger.info(f"[{capture_folder}] ⊗ Skip: no OCR pending")
            return
        
        # Skip OCR if freeze detected (frozen frame = no new subtitles)
        if data.get('freeze', False):
            logger.info(f"[{capture_folder}] ⊗ SKIP: Freeze detected (no new content)")
            data['subtitle_analysis'] = {
                'has_subtitles': False,
                'extracted_text': '',
                'skipped': True,
                'skip_reason': 'freeze'
            }
            data['subtitle_ocr_pending'] = False
            with open(json_path + '.tmp', 'w') as f:
                json.dump(data, f, indent=2)
            os.rename(json_path + '.tmp', json_path)
            return
        
        # Skip OCR if blackscreen detected (no content = no subtitles)
        if data.get('blackscreen', False):
            logger.info(f"[{capture_folder}] ⊗ SKIP: Blackscreen (no content)")
            data['subtitle_analysis'] = {
                'has_subtitles': False,
                'extracted_text': '',
                'skipped': True,
                'skip_reason': 'blackscreen'
            }
            data['subtitle_ocr_pending'] = False
            with open(json_path + '.tmp', 'w') as f:
                json.dump(data, f, indent=2)
            os.rename(json_path + '.tmp', json_path)
            return
        
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
                logger.info(f"[{capture_folder}] ⊗ SKIP: No subtitle edges detected")
                logger.info(f"[{capture_folder}]    └─ Edge density: {subtitle_edge_density:.1f}% (need 1.5-8%)")
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
                
                # Downscale - reduces pixels for faster OCR
                start_down = time.perf_counter()
                crop = cv2.resize(crop, None, fx=DOWNSCALE_FACTOR, fy=DOWNSCALE_FACTOR, interpolation=cv2.INTER_AREA)
                down_h, down_w = crop.shape
                down_time = (time.perf_counter() - start_down) * 1000
                
                # Calculate actual pixel reduction
                original_pixels = w * h
                downscaled_pixels = down_w * down_h
                pixel_reduction_pct = ((original_pixels - downscaled_pixels) / original_pixels) * 100
                
                # Binarization (black/white only) - 20% faster OCR (OPTIONAL)
                start_binarize = time.perf_counter()
                if ENABLE_BINARIZATION:
                    _, crop = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                binarize_time = (time.perf_counter() - start_binarize) * 1000
                
                # Get cached language or use default (reuse language for 2 minutes)
                current_time = time.time()
                cached_lang = None
                lang_config = 'eng+deu+fra'  # Default
                lang_cached = False
                
                # Language mapping: langdetect (2-letter) -> Tesseract (3-letter)
                lang_map = {
                    'en': 'eng',
                    'fr': 'fra', 
                    'de': 'deu',
                    'es': 'spa',
                    'it': 'ita'
                }
                
                if capture_folder in self.language_cache:
                    cache_time, cached_lang = self.language_cache[capture_folder]
                    cache_age = current_time - cache_time
                    if cache_age < 120:  # 2 minutes
                        # Map detected language (en/fr/de) to Tesseract code (eng/fra/deu)
                        tesseract_lang = lang_map.get(cached_lang, 'eng')
                        lang_config = tesseract_lang
                        lang_cached = True
                        logger.info(f"[{capture_folder}] 🔄 Using cached language: {cached_lang} → {tesseract_lang} (age={cache_age:.0f}s)")
                
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
                
                # Apply shared regex-based filter
                text_before_spellcheck = text
                text = clean_transcript_text(text)
                
                # Spell checking (optional - measures time and shows corrections)
                spell_time = 0
                spell_corrections = 0
                spell_status = "disabled"
                
                if ENABLE_SPELLCHECK and SPELLCHECKER_AVAILABLE and text:
                    start_spell = time.perf_counter()
                    try:
                        # Initialize spell checker (cached after first use)
                        if not hasattr(self, '_spell_checker'):
                            self._spell_checker = SpellChecker()
                        
                        spell = self._spell_checker
                        words = text.split()
                        corrected_words = []
                        corrections_made = []
                        
                        for word in words:
                            # Only check words with letters (skip numbers, punctuation)
                            if any(c.isalpha() for c in word):
                                # Get correction
                                corrected = spell.correction(word.lower())
                                if corrected and corrected != word.lower():
                                    # Word was corrected
                                    corrected_words.append(corrected)
                                    corrections_made.append(f"{word}→{corrected}")
                                    spell_corrections += 1
                                else:
                                    corrected_words.append(word)
                            else:
                                corrected_words.append(word)
                        
                        text = ' '.join(corrected_words)
                        spell_time = (time.perf_counter() - start_spell) * 1000
                        spell_status = f"corrected {spell_corrections} words" if spell_corrections > 0 else "no corrections"
                        
                        if corrections_made:
                            logger.info(f"[{capture_folder}] ✏️  Spell corrections: {', '.join(corrections_made[:5])}")
                            
                    except Exception as e:
                        spell_time = (time.perf_counter() - start_spell) * 1000
                        spell_status = f"error: {str(e)[:30]}"
                        logger.warning(f"[{capture_folder}] Spell check error: {e}")
                elif ENABLE_SPELLCHECK and not SPELLCHECKER_AVAILABLE:
                    spell_status = "unavailable (install pyspellchecker)"
                
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
                
                # Calculate preprocessing time (everything except OCR)
                preprocess_time = crop_time + down_time + binarize_time
                
                data['subtitle_analysis'] = {
                    'has_subtitles': bool(text),
                    'extracted_text': text,
                    'detected_language': detected_language,
                    'subtitle_edge_density': round(subtitle_edge_density, 1),
                    'box': {'x': x, 'y': y, 'width': w, 'height': h},
                    'skipped': False,
                    'ocr_time_ms': round(ocr_time, 2),
                    'downscale_factor': DOWNSCALE_FACTOR,
                    'pixel_reduction_pct': round(pixel_reduction_pct, 1),
                    'binarized': ENABLE_BINARIZATION
                }
                
                # Clear, readable logging showing what happened
                binarize_status = "ON" if ENABLE_BINARIZATION else "OFF"
                downscale_pct = int(DOWNSCALE_FACTOR * 100)
                
                if text:
                    lang_str = f" [{detected_language}]" if detected_language else ""
                    if lang_cached:
                        lang_method = f" (cached, single lang)"
                        lang_info = f"lang={lang_config} ⚡"
                    else:
                        lang_method = f" (3 languages)"
                        lang_info = f"lang={lang_config}"
                    
                    logger.info(f"[{capture_folder}] 📝 TEXT FOUND{lang_str}:")
                    logger.info(f"[{capture_folder}]    └─ '{text[:70]}'")
                    logger.info(f"[{capture_folder}]    └─ Image: {w}x{h} → {down_w}x{down_h} (resize={downscale_pct}%, {pixel_reduction_pct:.0f}% fewer pixels)")
                    logger.info(f"[{capture_folder}]    └─ Preprocessing: crop={crop_time:.0f}ms + resize={down_time:.0f}ms + binarize={binarize_time:.0f}ms [bin={binarize_status}] = {preprocess_time:.0f}ms")
                    logger.info(f"[{capture_folder}]    └─ OCR{lang_method}: {ocr_time:.0f}ms (Tesseract {lang_info})")
                    if ENABLE_SPELLCHECK:
                        logger.info(f"[{capture_folder}]    └─ Spellcheck: {spell_time:.0f}ms ({spell_status})")
                    logger.info(f"[{capture_folder}]    └─ TOTAL: {total_time:.0f}ms ({len(text)} chars)")
                else:
                    if lang_cached:
                        lang_info = f" (cached {lang_config})"
                    else:
                        lang_info = f" ({lang_config})"
                    logger.info(f"[{capture_folder}] ⊗ NO TEXT")
                    logger.info(f"[{capture_folder}]    └─ Resize: {downscale_pct}% ({pixel_reduction_pct:.0f}% fewer pixels) | Preprocess: {preprocess_time:.0f}ms [bin={binarize_status}] | OCR{lang_info}: {ocr_time:.0f}ms | Total: {total_time:.0f}ms")
        
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
    
    binarize_status = "ENABLED" if ENABLE_BINARIZATION else "DISABLED"
    spellcheck_status = "ENABLED" if ENABLE_SPELLCHECK else "DISABLED"
    downscale_pct = int(DOWNSCALE_FACTOR * 100)
    pixel_reduction = int((1 - DOWNSCALE_FACTOR**2) * 100)
    
    logger.info("=" * 80)
    logger.info("Subtitle OCR Monitor - OPTIMIZED")
    logger.info(f"- Downscale: {downscale_pct}% ({pixel_reduction}% fewer pixels)")
    logger.info(f"- Binarization: {binarize_status} (black/white for faster OCR)")
    logger.info(f"- Spellcheck: {spellcheck_status} (corrects misspelled words)")
    logger.info("- Language caching (2min per device)")
    logger.info("=" * 80)
    logger.info(f"Monitoring {len(capture_dirs)} devices (queue: 10 most recent per device)")
    
    monitor = InotifySubtitleMonitor(capture_dirs)
    monitor.run()

if __name__ == '__main__':
    main()

