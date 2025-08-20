# Backend Discard Service Implementation Plan

## 🎯 **Overview**

Minimalist AI-powered service to analyze test execution results and alerts for false positives using Redis queues and OpenRouter AI.

**Priority Processing**: p1 (alerts) → p2 (test executions) → p3 (future use)
**AI Model**: `qwen/qwen-2.5-vl-7b-instruct` for image analysis, `moonshotai/kimi-k2:free` for text
**Tables**: `alerts` and `script_results` only

## 🏗️ **Simple Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Alert/Test    │    │  Redis Queues   │    │ Backend Discard │
│   Generation    │───►│  p1: alerts     │◄───│   (Minimal)     │
│                 │    │  p2: scripts    │    │                 │
│ alerts_db.py    │    │  p3: reserved   │    │ • AI Analysis   │
│ script_results  │    │                 │    │ • Queue Monitor │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📊 **Database Schema (Minimal)**

### **Add to existing tables only:**

```sql
-- alerts table extensions
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS checked BOOLEAN DEFAULT FALSE;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS check_type VARCHAR(10); -- 'ai' or 'user'
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS discard BOOLEAN DEFAULT FALSE;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS discard_type VARCHAR(20); -- 'false_positive', 'valid'
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS discard_comment TEXT;

-- script_results table extensions  
ALTER TABLE script_results ADD COLUMN IF NOT EXISTS checked BOOLEAN DEFAULT FALSE;
ALTER TABLE script_results ADD COLUMN IF NOT EXISTS check_type VARCHAR(10); -- 'ai' or 'user'
ALTER TABLE script_results ADD COLUMN IF NOT EXISTS discard BOOLEAN DEFAULT FALSE;
ALTER TABLE script_results ADD COLUMN IF NOT EXISTS discard_type VARCHAR(20); -- 'false_positive', 'valid'
ALTER TABLE script_results ADD COLUMN IF NOT EXISTS discard_comment TEXT;
```

## 🚀 **Service Structure (Minimal)**

```
backend_discard/
├── Dockerfile              # Simple Docker deployment
├── requirements.txt         # Minimal dependencies
├── README.md
├── src/
│   ├── app.py              # Main service (200 lines max)
│   ├── queue_processor.py  # Queue monitoring (100 lines)
│   ├── ai_analyzer.py      # AI analysis (150 lines)
│   └── .env.example
└── scripts/
    └── start.sh
```

## 🔧 **Core Components**

### **1. Queue Processor (`queue_processor.py`)**

```python
import requests
import json
import os
import time
from typing import Optional, Dict

class SimpleQueueProcessor:
    def __init__(self):
        # Use Upstash Redis REST API (from root .env)
        self.redis_url = os.getenv('UPSTASH_REDIS_REST_URL')
        self.redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
        self.headers = {
            'Authorization': f'Bearer {self.redis_token}',
            'Content-Type': 'application/json'
        }
        self.queues = ['p1_alerts', 'p2_scripts', 'p3_reserved']
    
    def _redis_command(self, command: list) -> Optional[dict]:
        """Execute Redis command via REST API"""
        try:
            response = requests.post(
                self.redis_url,
                headers=self.headers,
                json=command,
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Redis command failed: {e}")
        return None
    
    def add_alert_to_queue(self, alert_id: str, alert_data: Dict):
        """Add alert to p1 queue"""
        task = {'type': 'alert', 'id': alert_id, 'data': alert_data}
        self._redis_command(['LPUSH', 'p1_alerts', json.dumps(task)])
    
    def add_script_to_queue(self, script_id: str, script_data: Dict):
        """Add script result to p2 queue"""
        task = {'type': 'script', 'id': script_id, 'data': script_data}
        self._redis_command(['LPUSH', 'p2_scripts', json.dumps(task)])
    
    def get_next_task(self) -> Optional[Dict]:
        """Get next task in priority order: p1 → p2 → p3"""
        for queue in self.queues:
            result = self._redis_command(['RPOP', queue])
            if result and result.get('result'):
                return json.loads(result['result'])
        return None
```

### **2. AI Analyzer (`ai_analyzer.py`)**

```python
import requests
import json
import os
import base64
from typing import Dict, List

class SimpleAIAnalyzer:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.text_model = 'moonshotai/kimi-k2:free'
        self.vision_model = 'qwen/qwen-2.5-vl-7b-instruct'
    
    def analyze_alert(self, alert_data: Dict) -> Dict:
        """Analyze alert for false positive"""
        prompt = f"""Alert Analysis:
Type: {alert_data.get('incident_type')}
Host: {alert_data.get('host_name')}
Device: {alert_data.get('device_id')}
Count: {alert_data.get('consecutive_count')}

Is this a false positive? Reply JSON:
{{"discard": true/false, "reason": "explanation"}}"""
        
        return self._call_text_ai(prompt)
    
    def analyze_script_result(self, script_data: Dict) -> Dict:
        """Analyze script result with report images"""
        # If has report URL, analyze images
        report_url = script_data.get('html_report_r2_url')
        if report_url and self._has_images_in_report(report_url):
            return self._analyze_with_images(script_data, report_url)
        else:
            return self._analyze_text_only(script_data)
    
    def _analyze_with_images(self, script_data: Dict, report_url: str) -> Dict:
        """Analyze using vision model for report images"""
        # Extract images from report (simplified)
        images = self._extract_report_images(report_url)
        
        if not images:
            return self._analyze_text_only(script_data)
        
        # Use first image for analysis
        image_b64 = self._image_to_base64(images[0])
        
        prompt = f"""Test Result Analysis:
Script: {script_data.get('script_name')}
Success: {script_data.get('success')}
Error: {script_data.get('error_msg', 'None')}

Analyze the screenshot. Is this test failure a false positive?
Reply JSON: {{"discard": true/false, "reason": "explanation"}}"""

        return self._call_vision_ai(prompt, image_b64)
    
    def _call_text_ai(self, prompt: str) -> Dict:
        """Call text AI model"""
        try:
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.text_model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 150,
                    'temperature': 0.1
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                return json.loads(content)
            
        except Exception as e:
            print(f"AI analysis failed: {e}")
        
        return {'discard': False, 'reason': 'AI analysis failed'}
    
    def _call_vision_ai(self, prompt: str, image_b64: str) -> Dict:
        """Call vision AI model"""
        try:
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.vision_model,
                    'messages': [{
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt},
                            {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{image_b64}'}}
                        ]
                    }],
                    'max_tokens': 150,
                    'temperature': 0.1
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                return json.loads(content)
                
        except Exception as e:
            print(f"Vision AI analysis failed: {e}")
        
        return {'discard': False, 'reason': 'Vision AI analysis failed'}
```

### **3. Main Service (`app.py`)**

```python
#!/usr/bin/env python3
"""
Backend Discard Service - Minimalist Implementation
AI-powered false positive detection for alerts and test results
"""

import sys
import os
import time
import signal

# Add project paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from shared.lib.utils.supabase_utils import get_supabase_client
from queue_processor import SimpleQueueProcessor
from ai_analyzer import SimpleAIAnalyzer

class BackendDiscardService:
    def __init__(self):
        self.running = False
        self.queue_processor = SimpleQueueProcessor()
        self.ai_analyzer = SimpleAIAnalyzer()
        self.supabase = get_supabase_client()
    
    def process_task(self, task: dict) -> bool:
        """Process single task"""
        try:
            task_type = task['type']
            task_id = task['id']
            task_data = task['data']
            
            print(f"Processing {task_type} task: {task_id}")
            
            if task_type == 'alert':
                analysis = self.ai_analyzer.analyze_alert(task_data)
                return self.update_alert(task_id, analysis)
            
            elif task_type == 'script':
                analysis = self.ai_analyzer.analyze_script_result(task_data)
                return self.update_script_result(task_id, analysis)
            
            return False
            
        except Exception as e:
            print(f"Error processing task: {e}")
            return False
    
    def update_alert(self, alert_id: str, analysis: dict) -> bool:
        """Update alert with AI analysis"""
        try:
            result = self.supabase.table('alerts').update({
                'checked': True,
                'check_type': 'ai',
                'discard': analysis['discard'],
                'discard_type': 'false_positive' if analysis['discard'] else 'valid',
                'discard_comment': analysis['reason']
            }).eq('id', alert_id).execute()
            
            return len(result.data) > 0
        except Exception as e:
            print(f"Error updating alert {alert_id}: {e}")
            return False
    
    def update_script_result(self, script_id: str, analysis: dict) -> bool:
        """Update script result with AI analysis"""
        try:
            result = self.supabase.table('script_results').update({
                'checked': True,
                'check_type': 'ai',
                'discard': analysis['discard'],
                'discard_type': 'false_positive' if analysis['discard'] else 'valid',
                'discard_comment': analysis['reason']
            }).eq('id', script_id).execute()
            
            return len(result.data) > 0
        except Exception as e:
            print(f"Error updating script result {script_id}: {e}")
            return False
    
    def run(self):
        """Main service loop"""
        self.running = True
        print("🤖 Backend Discard Service started")
        
        while self.running:
            try:
                task = self.queue_processor.get_next_task()
                
                if task:
                    success = self.process_task(task)
                    status = "✅ SUCCESS" if success else "❌ FAILED"
                    print(f"Task {task['id']}: {status}")
                else:
                    time.sleep(1)  # No tasks, short sleep
                    
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(5)
        
        print("🛑 Backend Discard Service stopped")
    
    def stop(self):
        self.running = False

# Global service instance
service = None

def signal_handler(signum, frame):
    global service
    print(f"Received signal {signum}, shutting down...")
    if service:
        service.stop()

def main():
    global service
    
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    service = BackendDiscardService()
    service.run()

if __name__ == '__main__':
    main()
```

## 🔌 **Integration Points**

### **1. Modify `alerts_db.py`**

```python
# Add after create_alert function
def create_alert_with_queue(host_name, device_id, incident_type, consecutive_count=3, metadata=None):
    """Create alert and add to processing queue"""
    result = create_alert(host_name, device_id, incident_type, consecutive_count, metadata)
    
    if result.get('success'):
        # Add to queue for AI analysis
        try:
            from backend_discard.src.queue_processor import SimpleQueueProcessor
            queue_processor = SimpleQueueProcessor()
            queue_processor.add_alert_to_queue(result['alert_id'], result['alert'])
            print(f"Added alert {result['alert_id']} to processing queue")
        except Exception as e:
            print(f"Failed to add alert to queue: {e}")
    
    return result
```

### **2. Modify `script_framework.py`**

```python
# Add after update_script_execution_result
def update_script_execution_result_with_queue(script_result_id, success, **kwargs):
    """Update script result and add to processing queue"""
    result = update_script_execution_result(script_result_id, success, **kwargs)
    
    if result:
        # Add to queue for AI analysis
        try:
            from backend_discard.src.queue_processor import SimpleQueueProcessor
            queue_processor = SimpleQueueProcessor()
            
            # Get script data for analysis
            script_data = {
                'id': script_result_id,
                'success': success,
                'html_report_r2_url': kwargs.get('html_report_r2_url'),
                'error_msg': kwargs.get('error_msg')
            }
            
            queue_processor.add_script_to_queue(script_result_id, script_data)
            print(f"Added script {script_result_id} to processing queue")
        except Exception as e:
            print(f"Failed to add script to queue: {e}")
    
    return result
```

## 🐳 **Docker Deployment**

### **Dockerfile**

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared library
COPY shared/ shared/
ENV PYTHONPATH="/app/shared:/app/shared/lib"

# Copy and install requirements
COPY backend_discard/requirements.txt backend_discard/
RUN pip install --no-cache-dir -r backend_discard/requirements.txt

# Copy source
COPY backend_discard/src/ backend_discard/src/

WORKDIR /app/backend_discard

# Health check
HEALTHCHECK --interval=30s --timeout=10s CMD python -c "import requests; requests.get('http://localhost:6209/health')" || exit 1

# Create non-root user
RUN useradd -m -u 1000 discarduser && chown -R discarduser:discarduser /app
USER discarduser

CMD ["python", "src/app.py"]
```

### **requirements.txt**

```
requests>=2.28.0
supabase>=2.0.0
python-dotenv>=1.0.0
pillow>=10.0.0
```

### **Environment Configuration**

Uses existing environment variables from project root `.env`:

```bash
# Already in root .env file:
UPSTASH_REDIS_REST_URL=your_upstash_redis_url
UPSTASH_REDIS_REST_TOKEN=your_upstash_redis_token
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

## 🚀 **Deployment Options**

### **Standalone**
```bash
cd backend_discard
pip install -r requirements.txt
python src/app.py
```

### **Docker**
```bash
docker build -t backend_discard .
docker run -d --env-file .env backend_discard
```

### **Docker Compose** (add to existing)
```yaml
  backend_discard:
    build:
      context: .
      dockerfile: backend_discard/Dockerfile
    environment:
      - REDIS_HOST=redis
      - SUPABASE_URL=${SUPABASE_URL}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    depends_on:
      - redis
```

## 📊 **Simple Monitoring**

### **Basic Metrics**
- Queue lengths: Monitor via service logs
- Processing rate: Log analysis
- AI success rate: Database queries

### **Health Check**
```bash
# Check service health
curl http://localhost:6209/health

# Check queue status via Upstash console or service logs
```

## 🎯 **Success Criteria**

1. **Queue Processing**: P1 → P2 → P3 priority respected
2. **AI Integration**: Vision model analyzes report images
3. **Database Updates**: Checked/discard flags properly set
4. **Deployment**: Works standalone and in Docker
5. **Minimalist**: < 500 lines total code

## 📝 **Implementation Order**

1. ✅ Create plan document
2. ⏳ Database schema extensions
3. ⏳ Core service implementation
4. ⏳ Queue integration points
5. ⏳ Docker deployment
6. ⏳ Testing and validation

---

This minimalist plan provides a focused, production-ready implementation that follows the existing patterns while being simple to deploy and maintain.

