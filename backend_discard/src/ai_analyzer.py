"""
AI Analyzer for Backend Discard Service

Uses OpenRouter AI models to analyze alerts and script results for false positives.
- Text Analysis: moonshotai/kimi-k2:free
- Image Analysis: qwen/qwen-2.5-vl-7b-instruct (for report screenshots)
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
    """Simple AI analyzer using centralized AI service"""
    
    def __init__(self):
        # Check if AI utilities are available
        try:
            from shared.src.lib.utils.ai_utils import call_text_ai, call_vision_ai
            self.call_text_ai = call_text_ai
            self.call_vision_ai = call_vision_ai
            print(f"[@ai_analyzer] Initialized with centralized AI utilities")
        except ImportError:
            raise ValueError("AI utilities not available")
        
        print(f"[@ai_analyzer] Initialized with OpenRouter API (database access via shared utilities)")
    
    def analyze_alert(self, alert_data: Dict[str, Any]) -> AnalysisResult:
        """Analyze alert for false positive detection"""
        try:
            alert_id = alert_data.get('id')
            if not alert_id:
                return AnalysisResult(success=False, error="No alert ID provided")
            
            # Get complete alert data from database
            complete_alert_data = self._get_alert_from_database(alert_id)
            if not complete_alert_data:
                return AnalysisResult(success=False, error=f"Alert {alert_id} not found in database")
            
            incident_type = complete_alert_data.get('incident_type', 'Unknown')
            host_name = complete_alert_data.get('host_name', 'Unknown')
            device_id = complete_alert_data.get('device_id', 'Unknown')
            consecutive_count = complete_alert_data.get('consecutive_count', 0)
            metadata = complete_alert_data.get('metadata', {})
            
            print(f"[@ai_analyzer] Analyzing alert {alert_id} ({incident_type})")
            
            # For now, use text-only analysis (visual analysis needs debugging)
            # TODO: Re-enable visual analysis after fixing vision AI response parsing
            # if self._alert_has_images(metadata):
            #     print(f"[@ai_analyzer] Attempting visual analysis for {incident_type} alert")
            #     image_result = self._analyze_alert_with_images(complete_alert_data)
            #     if image_result.success:
            #         return image_result
            #     else:
            #         print(f"[@ai_analyzer] Image analysis failed, falling back to text analysis")
            
            # Text-only analysis with rich metadata
            prompt = self._create_alert_analysis_prompt(complete_alert_data)
            return self._call_text_ai(prompt)
            
        except Exception as e:
            print(f"[@ai_analyzer] Error analyzing alert: {e}")
            return AnalysisResult(success=False, error=str(e))
    
    def analyze_script_result(self, script_data: Dict[str, Any]) -> AnalysisResult:
        """Analyze script result with optional report image analysis"""
        try:
            script_id = script_data.get('id')
            if not script_id:
                return AnalysisResult(success=False, error="No script ID provided")
            
            # Get complete script data from database
            complete_script_data = self._get_script_from_database(script_id)
            if not complete_script_data:
                return AnalysisResult(success=False, error=f"Script {script_id} not found in database")
            
            script_name = complete_script_data.get('script_name', 'Unknown')
            success = complete_script_data.get('success', False)
            error_msg = complete_script_data.get('error_msg', '')
            execution_time = complete_script_data.get('execution_time_ms', 0)
            report_url = complete_script_data.get('html_report_r2_url', '')
            
            print(f"[@ai_analyzer] Analyzing script {script_id} ({script_name})")
            
            # Try image analysis first if report URL available
            if report_url and self._is_valid_report_url(report_url):
                print(f"[@ai_analyzer] Attempting image analysis for {script_name}")
                image_result = self._analyze_with_images(complete_script_data, report_url)
                if image_result.success:
                    return image_result
                else:
                    print(f"[@ai_analyzer] Image analysis failed, falling back to text analysis")
            
            # Fallback to text-only analysis
            return self._analyze_text_only(complete_script_data)
            
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
            
            prompt = f"""Test Script Visual Analysis:

Script: {script_name}
Execution Result: {"PASSED" if success else "FAILED"}
Error Message: {error_msg}

TASK: Analyze the screenshot to determine if this script result should be discarded as a false positive or kept as valid.

ANALYSIS RULES:
1. SUCCESSFUL SCRIPTS (success=true):
   - NEVER discard successful scripts based on visual appearance alone
   - Focus on confirming the test achieved its intended goal
   - Minor UI variations are acceptable if core functionality works

2. FAILED SCRIPTS (success=false):
   - Look for clear evidence the failure is environmental/infrastructure related
   - Common false positive visual patterns:
     * UI loading states or animations in progress
     * Expected error dialogs that are part of normal flow
     * Environment-specific styling differences
     * Timing-related UI states (elements still loading)
     * Browser rendering variations

3. VALIDATION APPROACH:
   - Does the screenshot show the expected final state?
   - Are any errors shown actually application bugs vs environment issues?
   - Is the UI in a reasonable state given the test context?

CRITICAL: Success=true should almost never be discarded based on screenshots.

Respond ONLY in this JSON format:
{{
    "discard": true/false,
    "category": "valid_success" or "valid_failure" or "false_positive",
    "confidence": 0-100,
    "explanation": "Brief reason based on screenshot (max 50 words)"
}}"""

            return self._call_vision_ai(prompt, image_b64)
            
        except Exception as e:
            print(f"[@ai_analyzer] Error in image analysis: {e}")
            return AnalysisResult(success=False, error=str(e))
    
    def _analyze_text_only(self, script_data: Dict[str, Any]) -> AnalysisResult:
        """Analyze using text-only approach with step-by-step verification if report available"""
        try:
            script_name = script_data.get('script_name', 'Unknown')
            script_type = script_data.get('script_type', 'Unknown')
            userinterface_name = script_data.get('userinterface_name', 'Unknown')
            device_name = script_data.get('device_name', 'Unknown')
            host_name = script_data.get('host_name', 'Unknown')
            success = script_data.get('success', False)
            error_msg = script_data.get('error_msg', 'None')
            execution_time = script_data.get('execution_time_ms', 0)
            report_url = script_data.get('html_report_r2_url', '')
            
            # Convert execution time to seconds for clearer analysis
            execution_seconds = execution_time / 1000.0
            
            # Try to get detailed report content for step-by-step analysis
            report_content = ""
            if report_url and self._is_valid_report_url(report_url):
                report_content = self._fetch_report_content(report_url)
            
            prompt = self._create_script_analysis_prompt(script_data, report_content)
            return self._call_text_ai(prompt)
            
        except Exception as e:
            print(f"[@ai_analyzer] Error in text analysis: {e}")
            return AnalysisResult(success=False, error=str(e))
    
    def _call_text_ai(self, prompt: str) -> AnalysisResult:
        """Call text AI model using centralized AI utilities"""
        try:
            result = self.call_text_ai(prompt, max_tokens=200, temperature=0.1)
            
            if result['success']:
                print(f"[@ai_analyzer] Text AI success with provider: {result.get('provider_used', 'unknown')}")
                
                # Parse JSON response
                content = result['content'].strip()
                
                # Clean up markdown code blocks if present
                if content.startswith('```json'):
                    content = content.replace('```json', '').replace('```', '').strip()
                elif content.startswith('```'):
                    content = content.replace('```', '').strip()
                
                ai_result = json.loads(content)
                
                return AnalysisResult(
                    success=True,
                    discard=ai_result.get('discard', False),
                    category=ai_result.get('category', 'unknown'),
                    confidence=ai_result.get('confidence', 0) / 100.0,
                    explanation=ai_result.get('explanation', 'No explanation provided')
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                provider_used = result.get('provider_used', 'none')
                print(f"[@ai_analyzer] Text AI analysis failed with {provider_used}: {error_msg}")
                return AnalysisResult(success=False, error=error_msg)
                
        except json.JSONDecodeError as e:
            print(f"[@ai_analyzer] Failed to parse AI JSON response: {e}")
            return AnalysisResult(success=False, error='AI returned invalid JSON')
        except Exception as e:
            print(f"[@ai_analyzer] Text AI analysis failed: {e}")
            return AnalysisResult(success=False, error=str(e))
    
    def _call_vision_ai(self, prompt: str, image_b64: str) -> AnalysisResult:
        """Call vision AI model using centralized AI utilities"""
        try:
            result = self.call_vision_ai(prompt, image_b64, max_tokens=200, temperature=0.1)
            
            if result['success']:
                print(f"[@ai_analyzer] Vision AI success with provider: {result.get('provider_used', 'unknown')}")
                
                content = result['content'].strip()
                print(f"[@ai_analyzer] Vision AI raw response: {content[:200]}...")
                
                # Clean up markdown code blocks if present
                if content.startswith('```json'):
                    content = content.replace('```json', '').replace('```', '').strip()
                elif content.startswith('```'):
                    content = content.replace('```', '').strip()
                
                # Parse JSON response
                try:
                    ai_result = json.loads(content)
                    
                    return AnalysisResult(
                        success=True,
                        discard=ai_result.get('discard', False),
                        category=ai_result.get('category', 'unknown'),
                        confidence=ai_result.get('confidence', 0) / 100.0,
                        explanation=ai_result.get('explanation', 'No explanation provided')
                    )
                except json.JSONDecodeError as e:
                    print(f"[@ai_analyzer] Failed to parse vision AI JSON response: {e}")
                    return AnalysisResult(success=False, error='Vision AI returned invalid JSON')
            else:
                error_msg = result.get('error', 'Unknown error')
                provider_used = result.get('provider_used', 'none')
                print(f"[@ai_analyzer] Vision AI analysis failed with {provider_used}: {error_msg}")
                return AnalysisResult(success=False, error=error_msg)
                
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
    
    def _fetch_report_content(self, report_url: str) -> str:
        """Fetch and parse HTML report content for step-by-step analysis"""
        try:
            print(f"[@ai_analyzer] Fetching report content from: {report_url[:50]}...")
            
            # Fetch the HTML report
            response = requests.get(report_url, timeout=30)
            if response.status_code != 200:
                print(f"[@ai_analyzer] Failed to fetch report: HTTP {response.status_code}")
                return ""
            
            html_content = response.text
            
            # Parse HTML to extract relevant content
            # Look for test steps, actions, verifications, and results
            parsed_content = self._parse_report_html(html_content)
            
            print(f"[@ai_analyzer] Successfully parsed report content ({len(parsed_content)} chars)")
            return parsed_content
            
        except Exception as e:
            print(f"[@ai_analyzer] Error fetching report content: {e}")
            return ""
    
    def _parse_report_html(self, html_content: str) -> str:
        """Parse HTML report to extract structured test execution information"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract key sections from the report
            sections = []
            
            # Remove script tags and style tags first
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get all text content for parsing
            all_text = soup.get_text()
            
            # Look for specific report structure patterns from your example
            sections.append("=== SCRIPT EXECUTION REPORT ===")
            
            # Extract status information
            status_info = []
            if 'Status:' in all_text:
                for line in all_text.split('\n'):
                    line = line.strip()
                    if any(keyword in line for keyword in ['Status:', 'Duration:', 'Device:', 'Host:', 'Steps:', 'Target:']):
                        if line:
                            status_info.append(line)
            
            if status_info:
                sections.append("\n=== EXECUTION STATUS ===")
                sections.extend(status_info[:10])  # Limit status lines
            
            # Extract execution summary
            if 'EXECUTION SUMMARY' in all_text:
                summary_start = all_text.find('EXECUTION SUMMARY')
                summary_end = all_text.find('Test Steps', summary_start)
                if summary_end == -1:
                    summary_end = summary_start + 1000  # Fallback limit
                
                summary_text = all_text[summary_start:summary_end].strip()
                if summary_text:
                    sections.append("\n=== EXECUTION SUMMARY ===")
                    sections.append(summary_text[:800])  # Limit summary length
            
            # Extract test steps information
            if 'Test Steps' in all_text or 'Navigation step' in all_text:
                sections.append("\n=== TEST STEPS ===")
                
                # Look for step patterns
                step_patterns = [
                    r'Navigation step \d+:.*?(?=Navigation step|\n\n|$)',
                    r'Step \d+.*?(?=Step \d+|\n\n|$)',
                    r'\d+\s+PASS.*?(?=\d+\s+PASS|\n\n|$)',
                    r'\d+\s+FAIL.*?(?=\d+\s+FAIL|\n\n|$)'
                ]
                
                steps_found = []
                for pattern in step_patterns:
                    matches = re.findall(pattern, all_text, re.DOTALL | re.IGNORECASE)
                    steps_found.extend(matches[:10])  # Limit steps
                
                if steps_found:
                    for i, step in enumerate(steps_found):
                        clean_step = ' '.join(step.split())  # Clean whitespace
                        sections.append(f"Step {i+1}: {clean_step[:400]}")  # Limit step length
            
            # Extract actions and verifications
            action_patterns = [
                r'Actions?:\s*(.*?)(?=Verifications?:|$)',
                r'click_element\([^)]*\)',
                r'waitForElementToAppear\([^)]*\)',
                r'swipe_[a-z]+\([^)]*\)',
                r'type_text\([^)]*\)'
            ]
            
            actions_found = []
            for pattern in action_patterns:
                matches = re.findall(pattern, all_text, re.DOTALL | re.IGNORECASE)
                actions_found.extend([match.strip() for match in matches if match.strip()])
            
            if actions_found:
                sections.append("\n=== ACTIONS EXECUTED ===")
                for i, action in enumerate(actions_found[:8]):  # Limit actions
                    sections.append(f"Action {i+1}: {action[:200]}")
            
            # Extract verification results
            verification_patterns = [
                r'Verifications?:\s*(.*?)(?=Actions?:|$)',
                r'waitForElementToAppear.*?PASS',
                r'waitForElementToAppear.*?FAIL',
                r'verify.*?PASS',
                r'verify.*?FAIL',
                r'assert.*?PASS',
                r'assert.*?FAIL'
            ]
            
            verifications_found = []
            for pattern in verification_patterns:
                matches = re.findall(pattern, all_text, re.DOTALL | re.IGNORECASE)
                verifications_found.extend([match.strip() for match in matches if match.strip()])
            
            if verifications_found:
                sections.append("\n=== VERIFICATIONS ===")
                for i, verification in enumerate(verifications_found[:8]):  # Limit verifications
                    sections.append(f"Verification {i+1}: {verification[:200]}")
            
            # Extract timing information
            timing_patterns = [
                r'Duration:\s*[\d.]+s',
                r'Start:\s*\d{2}:\d{2}:\d{2}',
                r'End:\s*\d{2}:\d{2}:\d{2}',
                r'Total Time:\s*[\d.]+s',
                r'[\d.]+s\s*$'
            ]
            
            timing_found = []
            for pattern in timing_patterns:
                matches = re.findall(pattern, all_text, re.IGNORECASE)
                timing_found.extend(matches)
            
            if timing_found:
                sections.append("\n=== TIMING INFORMATION ===")
                for timing in timing_found[:5]:  # Limit timing entries
                    sections.append(timing)
            
            # If no structured content found, extract key lines
            if len(sections) <= 1:
                sections.append("\n=== REPORT CONTENT ===")
                
                # Extract meaningful lines (skip empty and very short lines)
                meaningful_lines = []
                for line in all_text.split('\n'):
                    clean_line = line.strip()
                    if (len(clean_line) > 5 and 
                        not clean_line.isdigit() and 
                        clean_line not in ['▶', '×', '‹', '›', '▼']):
                        meaningful_lines.append(clean_line)
                
                # Take first 30 meaningful lines
                sections.extend(meaningful_lines[:30])
            
            return '\n'.join(sections)
            
        except ImportError:
            # Fallback if BeautifulSoup not available - use simple regex parsing
            return self._parse_report_html_simple(html_content)
        except Exception as e:
            print(f"[@ai_analyzer] Error parsing HTML report: {e}")
            return html_content[:2000]  # Return raw content as fallback
    
    def _parse_report_html_simple(self, html_content: str) -> str:
        """Simple HTML parsing fallback without BeautifulSoup"""
        try:
            # Remove HTML tags using regex
            import re
            
            # Remove script and style elements
            html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove HTML tags
            clean_text = re.sub(r'<[^>]+>', ' ', html_content)
            
            # Clean up whitespace
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            # Look for key patterns in the text
            sections = []
            
            # Look for step patterns
            step_matches = re.findall(r'(step\s*\d+[^.]*[.!])', clean_text, re.IGNORECASE)
            if step_matches:
                sections.append("=== EXECUTION STEPS ===")
                for i, step in enumerate(step_matches[:10]):
                    sections.append(f"Step {i+1}: {step[:200]}")
            
            # Look for verification patterns
            verify_matches = re.findall(r'(verif[^.]*[.!]|check[^.]*[.!]|assert[^.]*[.!])', clean_text, re.IGNORECASE)
            if verify_matches:
                sections.append("\n=== VERIFICATION RESULTS ===")
                for i, verify in enumerate(verify_matches[:5]):
                    sections.append(f"Verification {i+1}: {verify[:150]}")
            
            # Look for error patterns
            error_matches = re.findall(r'(error[^.]*[.!]|fail[^.]*[.!]|exception[^.]*[.!])', clean_text, re.IGNORECASE)
            if error_matches:
                sections.append("\n=== ERROR DETAILS ===")
                for error in error_matches[:3]:
                    sections.append(error[:200])
            
            # If no patterns found, return cleaned text
            if not sections:
                sections.append("=== REPORT CONTENT ===")
                sections.append(clean_text[:2000])
            
            return '\n'.join(sections)
            
        except Exception as e:
            print(f"[@ai_analyzer] Error in simple HTML parsing: {e}")
            return html_content[:1000]  # Return raw content as last resort
    
    def _get_script_from_database(self, script_id: str) -> Optional[Dict[str, Any]]:
        """Get complete script result data from database"""
        try:
            from shared.src.lib.database.script_results_db import get_script_by_id
            return get_script_by_id(script_id)
        except Exception as e:
            print(f"[@ai_analyzer] Error retrieving script from database: {e}")
            return None
    
    def _get_alert_from_database(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get complete alert data from database"""
        try:
            from shared.src.lib.database.alerts_db import get_alert_by_id
            return get_alert_by_id(alert_id)
        except Exception as e:
            print(f"[@ai_analyzer] Error retrieving alert from database: {e}")
            return None
    
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
    
    def _alert_has_images(self, metadata: Dict[str, Any]) -> bool:
        """Check if alert has accessible images for visual analysis"""
        try:
            r2_images = metadata.get('r2_images', {})
            original_urls = r2_images.get('original_urls', [])
            thumbnail_urls = r2_images.get('thumbnail_urls', [])
            
            return len(original_urls) > 0 or len(thumbnail_urls) > 0
        except Exception:
            return False
    
    def _analyze_alert_with_images(self, alert_data: Dict[str, Any]) -> AnalysisResult:
        """Analyze alert using visual analysis of alert images"""
        try:
            alert_id = alert_data.get('id', 'Unknown')
            incident_type = alert_data.get('incident_type', 'Unknown')
            metadata = alert_data.get('metadata', {})
            
            # Get image URLs from metadata
            r2_images = metadata.get('r2_images', {})
            original_urls = r2_images.get('original_urls', [])
            thumbnail_urls = r2_images.get('thumbnail_urls', [])
            
            # Use thumbnail for faster analysis (smaller images)
            if thumbnail_urls:
                image_url = thumbnail_urls[0]  # Use first thumbnail
                print(f"[@ai_analyzer] Using thumbnail image: {image_url[:50]}...")
            elif original_urls:
                image_url = original_urls[0]  # Use first original image
                print(f"[@ai_analyzer] Using original image: {image_url[:50]}...")
            else:
                return AnalysisResult(success=False, error="No image URLs found in alert metadata")
            
            # Convert image to base64
            image_b64 = self._image_to_base64(image_url)
            if not image_b64:
                return AnalysisResult(success=False, error="Failed to download or encode alert image")
            
            # Create visual analysis prompt for alerts
            prompt = self._create_alert_visual_analysis_prompt(alert_data)
            
            return self._call_vision_ai(prompt, image_b64)
            
        except Exception as e:
            print(f"[@ai_analyzer] Error in alert image analysis: {e}")
            return AnalysisResult(success=False, error=str(e))
    
    def _create_alert_visual_analysis_prompt(self, alert_data: Dict[str, Any]) -> str:
        """Create specialized visual analysis prompt for alerts"""
        alert_id = alert_data.get('id', 'Unknown')
        incident_type = alert_data.get('incident_type', 'Unknown')
        host_name = alert_data.get('host_name', 'Unknown')
        device_id = alert_data.get('device_id', 'Unknown')
        consecutive_count = alert_data.get('consecutive_count', 0)
        status = alert_data.get('status', 'Unknown')
        metadata = alert_data.get('metadata', {})
        
        # Extract key metadata for context
        freeze_diffs = metadata.get('freeze_diffs', [])
        blackscreen = metadata.get('blackscreen', False)
        audio = metadata.get('audio', False)
        volume_percentage = metadata.get('volume_percentage', 0)
        blackscreen_percentage = metadata.get('blackscreen_percentage', 0)
        
        return f"""ALERT VISUAL ANALYSIS

ALERT DETAILS:
- Alert ID: {alert_id}
- Incident Type: {incident_type}
- Host: {host_name}
- Device: {device_id}
- Status: {status}
- Consecutive Count: {consecutive_count}

TECHNICAL METADATA:
- Freeze Diffs: {freeze_diffs}
- Blackscreen: {blackscreen}
- Audio Present: {audio}
- Volume %: {volume_percentage}
- Blackscreen %: {blackscreen_percentage}

TASK: Analyze the alert screenshot to determine if this is a false positive or valid incident.

VISUAL ANALYSIS CRITERIA:

1. **FREEZE INCIDENT ANALYSIS**:
   - Is the screen actually frozen/stuck or showing normal content?
   - Does the image show identical frames that indicate technical freeze?
   - Could this be paused content, menu screen, or loading state?
   - Are there visible UI elements suggesting normal operation?

2. **BLACKSCREEN INCIDENT ANALYSIS**:
   - Is the screen completely black or just dark content?
   - Are there any UI elements, logos, or text visible?
   - Could this be normal content transition or loading screen?
   - Is this expected behavior (channel change, app launch)?

3. **CONTENT CONTEXT EVALUATION**:
   - What type of content is displayed (TV show, menu, app, loading)?
   - Does the content suggest normal viewing vs technical issue?
   - Are there timestamps, progress bars, or other dynamic elements?
   - Does the screen layout suggest active vs frozen state?

4. **DEVICE STATE INDICATORS**:
   - Are there visible device status indicators?
   - Do channel numbers, volume indicators, or UI overlays suggest normal operation?
   - Is this a streaming app, live TV, or system interface?
   - Are there any error messages or technical indicators visible?

5. **FALSE POSITIVE PATTERNS**:
   - Static content during pause/menu navigation
   - Loading screens or buffering states
   - Dark scenes in movies/shows that trigger blackscreen detection
   - Identical frames during content pauses or user inactivity
   - App launch screens or interface transitions

DECISION CRITERIA:
- **DISCARD (false positive)** if: Normal content pause, menu screen, loading state, or expected user interface behavior
- **KEEP (valid incident)** if: Clear technical freeze, unexpected blackscreen, or obvious system malfunction

Respond ONLY in this JSON format:
{{
    "discard": true/false,
    "category": "false_positive" or "valid_incident",
    "confidence": 0-100,
    "explanation": "Visual analysis summary (max 80 words)"
}}"""
    
    def _create_alert_analysis_prompt(self, alert_data: Dict[str, Any]) -> str:
        """Create specialized prompt for alert analysis"""
        incident_type = alert_data.get('incident_type', 'Unknown')
        host_name = alert_data.get('host_name', 'Unknown')
        device_id = alert_data.get('device_id', 'Unknown')
        consecutive_count = alert_data.get('consecutive_count', 0)
        metadata = alert_data.get('metadata', {})
        started_at = alert_data.get('started_at', 'Unknown')
        status = alert_data.get('status', 'Unknown')
        
        return f"""EXPERT LIVE TV MONITORING ANALYSIS

You are an expert TV broadcast monitoring specialist with deep understanding of live television content and technical systems. Your goal is to identify REAL technical issues affecting live broadcasts and differentiate them from normal content patterns.

ALERT DETAILS:
- Alert ID: {alert_data.get('id', 'Unknown')}
- Incident Type: {incident_type}
- Host Name: {host_name}
- Device ID: {device_id}
- Status: {status}
- Started At: {started_at}
- Consecutive Count: {consecutive_count}
- Technical Metadata: {json.dumps(metadata, indent=2)}

EXPERT ANALYSIS FRAMEWORK:
Your broadcast monitoring expertise allows you to differentiate between:

**1. REAL TECHNICAL ISSUES (KEEP - Genuine Problems)**:
- Persistent stream freezes (multiple consecutive alerts, high freeze_diffs)
- Complete signal loss or blackouts (extended blackscreen, no audio)
- Hardware malfunctions (device unresponsive, capture failure)
- Encoding/transmission errors affecting broadcast quality
- Infrastructure failures (network, power, equipment)
- Persistent audio loss or sync issues

**2. NORMAL CONTENT PATTERNS (DISCARD - Expected Behavior)**:
- **Weather Programs**: Often show static maps, satellite images, or radar loops
- **News Broadcasting**: Journalists talking with minimal background change
- **Breaking News**: Static graphics, emergency broadcasts, or standby screens
- **Commercial Breaks**: May include static sponsor cards or paused content
- **Program Transitions**: Brief blackscreens, loading screens, or channel idents
- **Live Events**: Natural pauses, audience shots, or static event graphics

**3. CONTENT-RELATED "FREEZES" (DISCARD - Not Technical Issues)**:
- Paused video content during news analysis or sports replays
- Static infographics, charts, or data displays
- Live camera shots of stationary subjects (buildings, landscapes)
- Presenter talking without camera movement
- Single-frame differences (freeze_diffs close to 0.0) during content pause

**4. TRANSIENT TECHNICAL ARTIFACTS (DISCARD - Temporary Glitches)**:
- Brief buffering during high network load
- Momentary capture delays (single occurrence, low consecutive_count)
- Short audio dropouts during channel switching
- Brief blackscreens during legitimate content transitions

**5. BLACKSCREEN ANALYSIS**:
- **REAL ISSUE**: Unexpected complete signal loss, equipment failure
- **NORMAL**: Channel changes, program transitions, commercial breaks, "zapping" between channels

BROADCAST EXPERTISE ANALYSIS: Determine if this alert represents a genuine technical issue affecting live broadcast quality or normal content/operational behavior.

TASK: Determine if this monitoring alert is a false positive or a valid incident requiring attention.

ALERT-SPECIFIC ANALYSIS CRITERIA:

1. **INCIDENT TYPE PATTERNS**:
   - **blackscreen**: Normal during channel changes (< 5s), app launches, or content transitions
   - **audio_loss**: Expected during stream startup, channel switching, or mute operations  
   - **connection_issues**: Temporary network fluctuations, WiFi handoffs, or brief connectivity drops
   - **system_restart**: Scheduled maintenance, firmware updates, or expected device reboots
   - **performance_degradation**: Brief CPU/memory spikes during intensive operations

2. **CONSECUTIVE COUNT EVALUATION**:
   - Count 1-2: Likely transient issue, high probability of false positive
   - Count 3-5: Possible real issue, but check for patterns
   - Count 6+: Strong indication of genuine problem

3. **TEMPORAL PATTERNS**:
   - Alerts during scheduled maintenance windows
   - Alerts coinciding with known system operations
   - Brief duration alerts (< 30 seconds total)

4. **DEVICE/HOST CONTEXT**:
   - Test environment vs production environment
   - Device model-specific known issues
   - Host-specific maintenance or configuration changes

5. **METADATA ANALYSIS**:
   - Check for system logs indicating expected operations
   - Look for error patterns that suggest infrastructure vs application issues
   - Analyze timing correlation with other system events

DECISION CRITERIA:
- **DISCARD (false positive)** if: Transient issue, expected system behavior, test environment artifact, or infrastructure-related
- **KEEP (valid incident)** if: Persistent problem, unexpected system failure, or genuine application/service issue

Respond ONLY in this JSON format:
{{
    "discard": true/false,
    "category": "false_positive" or "valid_incident",
    "confidence": 0-100,
    "explanation": "Alert-specific reasoning (max 80 words)"
}}"""
    
    def _create_script_analysis_prompt(self, script_data: Dict[str, Any], report_content: str = "") -> str:
        """Create specialized prompt for script execution analysis"""
        script_name = script_data.get('script_name', 'Unknown')
        script_type = script_data.get('script_type', 'Unknown')
        userinterface_name = script_data.get('userinterface_name', 'Unknown')
        device_name = script_data.get('device_name', 'Unknown')
        host_name = script_data.get('host_name', 'Unknown')
        success = script_data.get('success', False)
        error_msg = script_data.get('error_msg', 'None')
        execution_time = script_data.get('execution_time_ms', 0)
        started_at = script_data.get('started_at', 'Unknown')
        completed_at = script_data.get('completed_at', 'Unknown')
        
        execution_seconds = execution_time / 1000.0
        
        if report_content:
            return f"""EXPERT TEST AUTOMATION ANALYSIS

You are an expert test automation engineer specializing in interface/application testing. Your primary goal is to identify REAL interface/app bugs and differentiate between different types of issues to ensure only genuine user-facing problems are escalated.

SCRIPT EXECUTION DETAILS:
- Script ID: {script_data.get('id', 'Unknown')}
- Script Name: {script_name}
- Script Type: {script_type}
- Interface: {userinterface_name}
- Device: {device_name}
- Host: {host_name}
- Execution Result: {"PASSED" if success else "FAILED"}
- Error Message: {error_msg}
- Execution Time: {execution_seconds:.1f} seconds ({execution_time}ms)
- Started At: {started_at}
- Completed At: {completed_at}

DETAILED EXECUTION REPORT:
{report_content[:8000]}
{"..." if len(report_content) > 8000 else ""}

EXPERT ANALYSIS FRAMEWORK:
Your expertise allows you to differentiate between:

**1. USER INTERFACE/APP BUGS (KEEP - Real Issues)**:
- App crashes, freezes, or unresponsive interfaces
- Navigation failures (buttons not working, incorrect page loads)
- Content not loading properly in apps
- UI elements missing, malformed, or positioned incorrectly
- Functionality broken (search, login, playback controls, settings)
- Unexpected app behavior, error screens, or crashes
- Real performance issues affecting user experience

**2. PLATFORM/SCRIPT/AUTOMATION BUGS (DISCARD - Our Issues)**:
- Test script logic errors or incorrect timing
- Outdated element selectors or script dependencies
- Script timeouts due to slow execution, not app issues
- Automation framework errors or connection problems
- Incorrect test data or setup issues
- Script race conditions or synchronization problems

**3. INFRASTRUCTURE ISSUES (DISCARD - Environment Problems)**:
- Network connectivity problems affecting test execution
- Device/host hardware issues or resource constraints
- ADB connection failures or device communication errors
- Stream capture, video pipeline, or monitoring issues
- Environment setup problems or configuration errors

**4. EXPECTED BEHAVIORS (DISCARD - Normal Operations)**:
- Long execution times for complex navigation (goto scripts taking 20-60s is normal)
- Successful operations that naturally take time (app launches, page loads, transitions)
- Valid error states that scripts correctly detect and handle
- Normal app loading screens, buffering states, or transitions

COMPREHENSIVE ANALYSIS TASK: Perform detailed step-by-step analysis to determine if this represents a genuine interface/app issue or should be discarded.

SCRIPT-SPECIFIC ANALYSIS REQUIREMENTS:

1. **STEP-BY-STEP EXECUTION VERIFICATION**:
   - Examine each navigation step in the report
   - Verify each action (click, swipe, type, wait) executed correctly
   - Check each verification/assertion passed or failed appropriately
   - Identify any step sequence inconsistencies or unexpected jumps
   - Analyze action timing and response delays

2. **ACTION EXECUTION VALIDATION**:
   - **Navigation actions**: Did each navigation command reach the intended target?
   - **Input actions**: Were text inputs, button clicks, and gestures executed properly?
   - **Wait actions**: Did waits complete appropriately for UI loading?
   - **Timing analysis**: Are action execution times reasonable for the device/interface?

3. **VERIFICATION AND ASSERTION ANALYSIS**:
   - **UI verifications**: Do screenshots match expected interface states?
   - **Content verifications**: Is displayed content correct for the navigation path?
   - **State verifications**: Are device/app states as expected after each step?
   - **Error handling**: Are verification failures due to real issues or false positives?

4. **SCRIPT TYPE-SPECIFIC LOGIC**:
   - **goto/navigation**: Focus on successful path completion and final destination
   - **validation**: Emphasize verification accuracy and content correctness
   - **performance**: Analyze timing thresholds and response patterns
   - **regression**: Compare against expected baseline behaviors

5. **INFRASTRUCTURE VS APPLICATION ISSUES**:
   - **Infrastructure failures**: Network timeouts, device connectivity, test framework issues
   - **Application failures**: UI bugs, functional regressions, content errors
   - **Environmental factors**: Test data issues, configuration problems, timing dependencies

6. **EXECUTION CONTEXT EVALUATION**:
   - **Success with long execution**: Normal for complex navigation sequences
   - **Failure patterns**: Distinguish between systematic issues and transient problems
   - **Device-specific behaviors**: Account for device model performance characteristics

DECISION CRITERIA:
- **DISCARD (false positive)** if: Infrastructure/environment issues, test framework problems, timing-related transient failures
- **KEEP (valid result)** if: Legitimate functional issues, real application bugs, or successful test completion

CRITICAL RULES:
- SUCCESS=true should almost NEVER be discarded unless clear infrastructure evidence
- Long execution times alone (30s-120s) are NOT grounds for discard if steps completed successfully
- Only discard failures if you can clearly identify infrastructure/environment root cause from step analysis

Respond ONLY in this JSON format:
{{
    "discard": true/false,
    "category": "valid_success" or "valid_failure" or "false_positive",
    "confidence": 0-100,
    "explanation": "Step-by-step analysis summary (max 120 words)"
}}"""
        else:
            return f"""EXPERT TEST AUTOMATION ANALYSIS (Basic Analysis)

You are an expert test automation engineer specializing in interface/application testing. Even without detailed execution reports, your expertise helps identify genuine issues vs false positives.

SCRIPT EXECUTION DETAILS:
- Script ID: {script_data.get('id', 'Unknown')}
- Script Name: {script_name}
- Script Type: {script_type}
- Interface: {userinterface_name}
- Device: {device_name}
- Host: {host_name}
- Execution Result: {"PASSED" if success else "FAILED"}
- Error Message: {error_msg}
- Execution Time: {execution_seconds:.1f} seconds ({execution_time}ms)
- Started At: {started_at}
- Completed At: {completed_at}

EXPERT ANALYSIS GUIDELINES:
Focus on differentiating between:
- **User Interface/App Bugs** (KEEP): Real functionality issues affecting users
- **Platform/Script Issues** (DISCARD): Test automation or timing problems  
- **Infrastructure Problems** (DISCARD): Environment, network, or device issues
- **Expected Behaviors** (DISCARD): Normal operation patterns (long goto scripts, etc.)

ANALYSIS TASK: Determine if this represents a genuine interface/app issue or should be discarded.

BASIC ANALYSIS CRITERIA:

1. **SUCCESS ANALYSIS**:
   - Successful scripts (success=true) should almost NEVER be discarded
   - Long execution times (30s-120s) are acceptable for navigation/goto scripts
   - Only discard successful scripts if error message indicates clear infrastructure issues

2. **FAILURE ANALYSIS**:
   - **Script Type Context**: {script_type} scripts have specific expected behaviors
   - **Error Message Patterns**: Analyze error for infrastructure vs application indicators
   - **Execution Time Context**: Very short failures (< 5s) often indicate infrastructure issues

3. **COMMON FALSE POSITIVE PATTERNS**:
   - Network connectivity timeouts
   - "Element not found" during page/UI transitions  
   - Device communication failures
   - Test framework initialization errors
   - Configuration or environment setup issues

4. **SCRIPT TYPE-SPECIFIC EXPECTATIONS**:
   - **goto**: Should reach target destination, timing varies by complexity
   - **validation**: Should verify specific conditions, focus on verification logic
   - **navigation**: Should complete path traversal, timing depends on UI responsiveness

DECISION CRITERIA:
- **DISCARD (false positive)** if: Clear infrastructure/environment error patterns
- **KEEP (valid result)** if: Functional test results or successful execution

CRITICAL: Success=true results should almost never be discarded regardless of execution time.

Respond ONLY in this JSON format:
{{
    "discard": true/false,
    "category": "valid_success" or "valid_failure" or "false_positive",
    "confidence": 0-100,
    "explanation": "Basic analysis reasoning (max 60 words)"
}}"""


# Global instance for easy import
ai_analyzer = None

def get_ai_analyzer() -> SimpleAIAnalyzer:
    """Get or create global AI analyzer instance"""
    global ai_analyzer
    if ai_analyzer is None:
        ai_analyzer = SimpleAIAnalyzer()
    return ai_analyzer
