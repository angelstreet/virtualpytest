#!/usr/bin/env python3

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
        logger.info("OCR worker started (1s delay per device)")
    
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
        
        if not data.get('subtitle_ocr_pending', False):
            return
        
        frame_file = os.path.basename(json_path).replace('.json', '.jpg')
        frame_path = os.path.join(captures_dir, frame_file)
        
        if not os.path.exists(frame_path):
            return
        
        try:
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
                
                import pytesseract
                text = pytesseract.image_to_string(
                    crop,
                    config='--psm 6 --oem 1 -l eng+deu+fra',
                    timeout=2
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
    
    logger.info(f"Monitoring {len(capture_dirs)} devices (queue: 10 most recent per device)")
    
    monitor = InotifySubtitleMonitor(capture_dirs)
    monitor.run()

if __name__ == '__main__':
    main()

