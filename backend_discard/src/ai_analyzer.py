"""
AI Analyzer for Backend Discard Service

Uses OpenRouter AI models to analyze alerts and script results for false positives.
- Text Analysis: moonshotai/kimi-k2:free
- Image Analysis: qwen/qwen-2-vl-7b-instruct (for report screenshots)
"""

import requests
import json
import os
import base64
import tempfile
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
from PIL import Image
import re


class AnalysisResult:
    """Result of AI analysis"""
    
    def __init__(self, success: bool = False, discard: bool = False, 
                 category: str = 'unknown', confidence: float = 0.0, 
                 explanation: str = '', error: str = ''):
        self.success = success
        self.discard = discard
        self.category = category
        self.confidence = confidence
        self.explanation = explanation
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'discard': self.discard,
            'category': self.category,
            'confidence': self.confidence,
            'explanation': self.explanation,
            'error': self.error
        }


class SimpleAIAnalyzer:
    """Simple AI analyzer using OpenRouter models"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("Missing OPENROUTER_API_KEY in environment")
        
        self.text_model = 'moonshotai/kimi-k2:free'
        self.vision_model = 'qwen/qwen-2-vl-7b-instruct'
        self.base_url = 'https://openrouter.ai/api/v1/chat/completions'
        
        print(f"[@ai_analyzer] Initialized with OpenRouter API")
    
    def analyze_alert(self, alert_data: Dict[str, Any]) -> AnalysisResult:
        """Analyze alert for false positive detection"""
        try:
            incident_type = alert_data.get('incident_type', 'Unknown')
            host_name = alert_data.get('host_name', 'Unknown')
            device_id = alert_data.get('device_id', 'Unknown')
            consecutive_count = alert_data.get('consecutive_count', 0)
            metadata = alert_data.get('metadata', {})
            
            prompt = f"""Alert Analysis Task:

Incident Details:
- Type: {incident_type}
- Host: {host_name}
- Device: {device_id}
- Consecutive Count: {consecutive_count}
- Metadata: {json.dumps(metadata, indent=2)}

Your task: Determine if this is a false positive alert based on monitoring patterns.

Common false positive patterns:
- Brief blackscreen during channel changes (< 5 seconds)
- Audio glitches during streaming startup
- Temporary connection issues
- Expected system restarts
- Test environment artifacts

Respond ONLY in this JSON format:
{{
    "discard": true/false,
    "category": "false_positive" or "valid_incident",
    "confidence": 0-100,
    "explanation": "Brief reason (max 50 words)"
}}"""

            print(f"[@ai_analyzer] Analyzing alert {alert_data.get('id', 'unknown')} ({incident_type})")
            return self._call_text_ai(prompt)
            
        except Exception as e:
            print(f"[@ai_analyzer] Error analyzing alert: {e}")
            return AnalysisResult(success=False, error=str(e))
    
    def analyze_script_result(self, script_data: Dict[str, Any]) -> AnalysisResult:
        """Analyze script result with optional report image analysis"""
        try:
            script_name = script_data.get('script_name', 'Unknown')
            success = script_data.get('success', False)
            error_msg = script_data.get('error_msg', '')
            execution_time = script_data.get('execution_time_ms', 0)
            report_url = script_data.get('html_report_r2_url', '')
            
            print(f"[@ai_analyzer] Analyzing script {script_data.get('id', 'unknown')} ({script_name})")
            
            # Try image analysis first if report URL available
            if report_url and self._is_valid_report_url(report_url):
                print(f"[@ai_analyzer] Attempting image analysis for {script_name}")
                image_result = self._analyze_with_images(script_data, report_url)
                if image_result.success:
                    return image_result
                else:
                    print(f"[@ai_analyzer] Image analysis failed, falling back to text analysis")
            
            # Fallback to text-only analysis
            return self._analyze_text_only(script_data)
            
        except Exception as e:
            print(f"[@ai_analyzer] Error analyzing script result: {e}")
            return AnalysisResult(success=False, error=str(e))
    
    def _analyze_with_images(self, script_data: Dict[str, Any], report_url: str) -> AnalysisResult:
        """Analyze using vision model for report images"""
        try:
            # Extract images from report (simplified approach)
            images = self._extract_report_images(report_url)
            
            if not images:
                print(f"[@ai_analyzer] No images found in report")
                return AnalysisResult(success=False, error="No images found in report")
            
            # Use first image for analysis
            image_b64 = self._image_to_base64(images[0])
            if not image_b64:
                return AnalysisResult(success=False, error="Failed to encode image")
            
            script_name = script_data.get('script_name', 'Unknown')
            success = script_data.get('success', False)
            error_msg = script_data.get('error_msg', 'None')
            
            prompt = f"""Test Result Analysis:

Script: {script_name}
Reported Success: {success}
Error Message: {error_msg}

Analyze the screenshot to determine if this test failure is a false positive.

Common false positive patterns in test screenshots:
- UI loading states or animations
- Expected error dialogs
- Environment-specific styling differences
- Timing-related UI states
- Browser rendering variations

Respond ONLY in this JSON format:
{{
    "discard": true/false,
    "category": "false_positive" or "valid_failure",
    "confidence": 0-100,
    "explanation": "Brief reason based on screenshot (max 50 words)"
}}"""

            return self._call_vision_ai(prompt, image_b64)
            
        except Exception as e:
            print(f"[@ai_analyzer] Error in image analysis: {e}")
            return AnalysisResult(success=False, error=str(e))
    
    def _analyze_text_only(self, script_data: Dict[str, Any]) -> AnalysisResult:
        """Analyze using text-only approach"""
        try:
            script_name = script_data.get('script_name', 'Unknown')
            success = script_data.get('success', False)
            error_msg = script_data.get('error_msg', 'None')
            execution_time = script_data.get('execution_time_ms', 0)
            
            prompt = f"""Test Result Analysis:

Script: {script_name}
Success: {success}
Error Message: {error_msg}
Execution Time: {execution_time}ms

Determine if this test failure is a false positive based on common patterns.

Common false positive patterns:
- Network timeouts during heavy load
- Selenium element not found during page transitions
- Timing issues in automation
- Environment-specific configuration issues
- Infrastructure problems

Respond ONLY in this JSON format:
{{
    "discard": true/false,
    "category": "false_positive" or "valid_failure",
    "confidence": 0-100,
    "explanation": "Brief reason (max 50 words)"
}}"""

            return self._call_text_ai(prompt)
            
        except Exception as e:
            print(f"[@ai_analyzer] Error in text analysis: {e}")
            return AnalysisResult(success=False, error=str(e))
    
    def _call_text_ai(self, prompt: str) -> AnalysisResult:
        """Call text AI model"""
        try:
            response = requests.post(
                self.base_url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://automai.dev',
                    'X-Title': 'AutomAI-VirtualPyTest-Discard'
                },
                json={
                    'model': self.text_model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 200,
                    'temperature': 0.1
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse JSON response
                ai_result = json.loads(content)
                
                return AnalysisResult(
                    success=True,
                    discard=ai_result.get('discard', False),
                    category=ai_result.get('category', 'unknown'),
                    confidence=ai_result.get('confidence', 0) / 100.0,
                    explanation=ai_result.get('explanation', 'No explanation provided')
                )
            else:
                print(f"[@ai_analyzer] Text AI API error: {response.status_code}")
                return AnalysisResult(success=False, error=f'AI API error: {response.status_code}')
                
        except json.JSONDecodeError as e:
            print(f"[@ai_analyzer] Failed to parse AI JSON response: {e}")
            return AnalysisResult(success=False, error='AI returned invalid JSON')
        except Exception as e:
            print(f"[@ai_analyzer] Text AI analysis failed: {e}")
            return AnalysisResult(success=False, error=str(e))
    
    def _call_vision_ai(self, prompt: str, image_b64: str) -> AnalysisResult:
        """Call vision AI model"""
        try:
            response = requests.post(
                self.base_url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://automai.dev',
                    'X-Title': 'AutomAI-VirtualPyTest-Discard'
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
                    'max_tokens': 200,
                    'temperature': 0.1
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse JSON response
                ai_result = json.loads(content)
                
                return AnalysisResult(
                    success=True,
                    discard=ai_result.get('discard', False),
                    category=ai_result.get('category', 'unknown'),
                    confidence=ai_result.get('confidence', 0) / 100.0,
                    explanation=ai_result.get('explanation', 'No explanation provided')
                )
            else:
                print(f"[@ai_analyzer] Vision AI API error: {response.status_code}")
                return AnalysisResult(success=False, error=f'Vision AI API error: {response.status_code}')
                
        except json.JSONDecodeError as e:
            print(f"[@ai_analyzer] Failed to parse vision AI JSON response: {e}")
            return AnalysisResult(success=False, error='Vision AI returned invalid JSON')
        except Exception as e:
            print(f"[@ai_analyzer] Vision AI analysis failed: {e}")
            return AnalysisResult(success=False, error=str(e))
    
    def _is_valid_report_url(self, url: str) -> bool:
        """Check if URL looks like a valid report URL"""
        try:
            parsed = urlparse(url)
            return (parsed.scheme in ['http', 'https'] and 
                    parsed.netloc and 
                    url.endswith('.html'))
        except Exception:
            return False
    
    def _extract_report_images(self, report_url: str) -> List[str]:
        """Extract image paths from HTML report (simplified)"""
        try:
            # For now, return empty list - would need actual HTML parsing
            # In a real implementation, this would fetch the HTML and extract image URLs
            print(f"[@ai_analyzer] Note: Image extraction not fully implemented for {report_url}")
            return []
        except Exception as e:
            print(f"[@ai_analyzer] Error extracting images from report: {e}")
            return []
    
    def _image_to_base64(self, image_path: str) -> Optional[str]:
        """Convert image to base64 string"""
        try:
            if image_path.startswith('http'):
                # Download image
                response = requests.get(image_path, timeout=10)
                if response.status_code == 200:
                    return base64.b64encode(response.content).decode()
            else:
                # Local file
                with open(image_path, 'rb') as f:
                    return base64.b64encode(f.read()).decode()
        except Exception as e:
            print(f"[@ai_analyzer] Error converting image to base64: {e}")
        
        return None


# Global instance for easy import
ai_analyzer = None

def get_ai_analyzer() -> SimpleAIAnalyzer:
    """Get or create global AI analyzer instance"""
    global ai_analyzer
    if ai_analyzer is None:
        ai_analyzer = SimpleAIAnalyzer()
    return ai_analyzer
