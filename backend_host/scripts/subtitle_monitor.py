#!/usr/bin/env python3
"""
Subtitle OCR Monitor - Single worker for OCR processing across all devices

Architecture:
- Single OCR worker thread (not per-device)
- Round-robin device processing
- Active queue (10 frames) + History queue (overflow)
- 0.5s delay between OCR operations
- Event-driven via inotify (no initial scan)

Performance:
- Prevents CPU spikes from concurrent OCR
- Fair distribution across devices
- Controlled rate limiting
- Graceful overflow handling
"""

# CRITICAL: Limit Tesseract/OpenCV threads BEFORE importing
import os
os.environ['OMP_NUM_THREADS'] = '1'          # OpenMP (Tesseract uses this)
os.environ['MKL_NUM_THREADS'] = '1'          # Intel MKL
os.environ['OPENBLAS_NUM_THREADS'] = '1'     # OpenBLAS (OpenCV)

import sys
import json
import logging
import queue
from queue import LifoQueue
import threading
import time
import cv2
import numpy as np
import inotify.adapters

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
    """Single OCR worker with round-robin device processing"""
    
    def __init__(self, capture_dirs):
        self.inotify = inotify.adapters.Inotify()
        self.path_to_folder = {}
        self.capture_dirs_map = {}
        
        self.active_queues = {}
        self.history_queues = {}
        
        self.ocr_worker = None
        self.worker_running = False
        
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
            
            self.active_queues[capture_folder] = queue.Queue(maxsize=10)
            self.history_queues[capture_folder] = []
        
        self._start_ocr_worker()
    
    def _start_ocr_worker(self):
        """Start single shared OCR worker"""
        self.worker_running = True
        self.ocr_worker = threading.Thread(
            target=self._round_robin_worker,
            daemon=True,
            name="ocr-worker"
        )
        self.ocr_worker.start()
        logger.info("Single OCR worker started (round-robin, 1s delay - optimized for CPU)")
    
    def _round_robin_worker(self):
        """Process OCR requests round-robin across devices"""
        devices = list(self.active_queues.keys())
        if not devices:
            return
        
        device_index = 0
        
        while self.worker_running:
            capture_folder = devices[device_index]
            work_queue = self.active_queues[capture_folder]
            captures_dir = self.capture_dirs_map[capture_folder]
            
            try:
                json_path = work_queue.get_nowait()
                queue_size = work_queue.qsize()
                
                try:
                    self.process_ocr(json_path, captures_dir, capture_folder, queue_size)
                except Exception as e:
                    logger.error(f"[{capture_folder}] OCR error: {e}")
                
                work_queue.task_done()
                
                if work_queue.empty():
                    self._refill_from_history(capture_folder)
                
                time.sleep(1.0)  # 1s delay (reduced CPU load vs 0.5s)
                
            except queue.Empty:
                pass
            
            device_index = (device_index + 1) % len(devices)
            time.sleep(0.1)
    
    def _refill_from_history(self, capture_folder):
        """Refill active queue from history"""
        history = self.history_queues[capture_folder]
        
        if not history:
            return
        
        refill = history[:10]
        self.history_queues[capture_folder] = history[10:]
        
        work_queue = self.active_queues[capture_folder]
        for json_path in refill:
            try:
                work_queue.put_nowait(json_path)
            except queue.Full:
                self.history_queues[capture_folder].insert(0, json_path)
                break
        
        if refill:
            logger.info(f"[{capture_folder}] Refilled {len(refill)} frames ({len(self.history_queues[capture_folder])} remaining)")
    
    def process_ocr(self, json_path, captures_dir, capture_folder, queue_size):
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        if not data.get('subtitle_ocr_pending', False):
            return
        
        frame_file = os.path.basename(json_path).replace('.json', '.jpg')
        frame_path = os.path.join(captures_dir, frame_file)
        
        if not os.path.exists(frame_path):
            return
        
        if queue_size > 50:
            data['subtitle_analysis'] = {
                'has_subtitles': False,
                'extracted_text': '',
                'skipped': True,
                'skip_reason': f'queue_overload_{queue_size}'
            }
        else:
            start = time.perf_counter()
            img = cv2.imread(frame_path, cv2.IMREAD_GRAYSCALE)
            
            if img is None:
                return
            
            img_height, img_width = img.shape
            edges = cv2.Canny(img, 50, 150)
            subtitle_y = int(img_height * 0.85)
            edges_subtitle = edges[subtitle_y:img_height, :]
            subtitle_edge_density = np.sum(edges_subtitle > 0) / edges_subtitle.size * 100
            
            if not (1.5 < subtitle_edge_density < 8):
                data['subtitle_analysis'] = {
                    'has_subtitles': False,
                    'extracted_text': '',
                    'subtitle_edge_density': round(subtitle_edge_density, 1),
                    'skipped': True,
                    'skip_reason': 'no_edges'
                }
            else:
                x = int(img_width * 0.10)
                y = int(img_height * 0.60)
                w = int(img_width * 0.80)
                h = int(img_height * 0.35)
                
                crop = img[y:y+h, x:x+w]
                crop = cv2.resize(crop, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
                
                try:
                    import pytesseract
                    # Optimized config: OEM 1 (faster legacy engine), 3 languages only, timeout
                    text = pytesseract.image_to_string(
                        crop,
                        config='--psm 6 --oem 1 -l eng+deu+fra',
                        timeout=2  # Prevent hanging on difficult images
                    ).strip()
                    
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
                    
                    ocr_time = (time.perf_counter() - start) * 1000
                    
                    data['subtitle_analysis'] = {
                        'has_subtitles': bool(text),
                        'extracted_text': text,
                        'subtitle_edge_density': round(subtitle_edge_density, 1),
                        'box': {'x': x, 'y': y, 'width': w, 'height': h},
                        'skipped': False,
                        'ocr_time_ms': round(ocr_time, 2)
                    }
                    
                    if text:
                        logger.info(f"[{capture_folder}] 📝 Subtitle: '{text[:80]}'")
                    
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
        logger.info("Starting inotify event loop (OCR pipeline)")
        
        try:
            for event in self.inotify.event_gen(yield_nones=False):
                (_, type_names, path, filename) = event
                
                # Watch for both IN_CLOSE_WRITE (direct write) and IN_MOVED_TO (atomic move)
                if 'IN_CLOSE_WRITE' not in type_names and 'IN_MOVED_TO' not in type_names:
                    continue
                
                if not filename.endswith('.json'):
                    continue
                
                if path in self.path_to_folder:
                    capture_folder = self.path_to_folder[path]['capture_folder']
                    json_path = os.path.join(path, filename)
                    
                    try:
                        self.active_queues[capture_folder].put_nowait(json_path)
                    except queue.Full:
                        self.history_queues[capture_folder].insert(0, json_path)
                        if len(self.history_queues[capture_folder]) % 50 == 1:
                            logger.warning(f"[{capture_folder}] Active queue full, history: {len(self.history_queues[capture_folder])}")
        
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
    
    logger.info("=" * 80)
    logger.info("Subtitle OCR Monitor - Event-driven processing")
    logger.info("=" * 80)
    
    base_dirs = get_capture_base_directories()
    capture_dirs = []
    
    for base_dir in base_dirs:
        device_folder = os.path.basename(base_dir)
        capture_path = get_captures_path(device_folder)
        capture_dirs.append(capture_path)
    
    logger.info(f"Monitoring {len(capture_dirs)} devices for OCR")
    
    monitor = InotifySubtitleMonitor(capture_dirs)
    monitor.run()

if __name__ == '__main__':
    main()

