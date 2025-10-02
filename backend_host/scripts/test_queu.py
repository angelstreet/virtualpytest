#!/usr/bin/env python3
"""
Modified test script to enqueue dummy KPI and start a temporary worker for processing.
This runs the full executor in this process to verify queueing + processing end-to-end.
Watch the console for logs (or check /tmp/kpi_executor.log if configured).
"""

import time
import logging
import sys
import os

# Set PYTHONPATH to include project root (for backend_host.src imports)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)  # Makes backend_host.src.* imports work

from backend_host.src.services.kpi.kpi_executor import get_kpi_executor, KPIMeasurementRequest

# Setup basic logging to console for this test
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Dummy data for testing
dummy_request = KPIMeasurementRequest(
    execution_result_id="test_id_123",  # Fake UUID - DB update will fail but verification logic will work
    team_id="7fdeb4bb-3639-4ec3-959f-b54769a219ce",  # Real team_id for DB queries
    capture_dir="/var/www/html/stream/capture3/captures",  # Use a real dir from your setup
    action_timestamp=time.time(),
    kpi_references=[{"verification_type": "image", "command": "waitForImageToAppear", "params": {"image_path": "home", "threshold": 0.9}}],
    timeout_ms=5000,
    device_id="device1",  # Required to get device's verification_executor
    device_model="android_tv"  # Required for finding references
)

# Get executor and enqueue
executor = get_kpi_executor()
if executor.enqueue_measurement(dummy_request):
    print("✅ Dummy KPI enqueued successfully! Starting temporary worker to process...")
else:
    print("❌ Failed to enqueue dummy KPI (queue full?)")
    exit(1)

# Start the worker thread (like the service)
executor.start()

# Run the main loop for 10 seconds to allow processing, then stop
print("🕒 Running worker for 10 seconds to process queue... Watch for processing logs!")
try:
    time.sleep(10)  # Give time for worker to process
except KeyboardInterrupt:
    pass
finally:
    executor.stop()
    print("🛑 Test complete. Check for processing logs above.")