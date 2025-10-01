#!/usr/bin/env python3
import time
from kpi_executor import get_kpi_executor, KPIMeasurementRequest

# Dummy data for testing
dummy_request = KPIMeasurementRequest(
    execution_result_id="test_id_123",
    team_id="test_team",
    capture_dir="/var/www/html/stream/capture3/captures",  # Use a real dir from your setup
    action_timestamp=time.time(),
    kpi_references=[{"verification_type": "image", "reference_name": "home", "timeout": 5000}],
    timeout_ms=5000
)

# Enqueue the dummy request
executor = get_kpi_executor()
if executor.enqueue_measurement(dummy_request):
    print("✅ Dummy KPI enqueued successfully! Check /tmp/kpi_executor.log for processing.")
else:
    print("❌ Failed to enqueue dummy KPI (queue full?)")