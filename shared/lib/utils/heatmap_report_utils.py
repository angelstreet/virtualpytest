"""
Heatmap Report Utilities

Comprehensive HTML generation for heatmap display with timeline navigation.
"""

import json
from datetime import datetime
from typing import Dict, List
from .heatmap_template_utils import create_heatmap_html_template

def generate_comprehensive_heatmap_html(all_heatmap_data: List[Dict]) -> str:
    """Generate ONE comprehensive heatmap HTML report with all mosaics and timeline navigation."""
    try:
        template = create_heatmap_html_template()
        
        if not all_heatmap_data:
            return "<html><body><h1>No heatmap data available</h1></body></html>"
        
        # Calculate summary stats with null checks
        total_timestamps = len(all_heatmap_data)
        
        # Safe access to analysis_data with null checks
        first_data = all_heatmap_data[0] if all_heatmap_data else {}
        analysis_data = first_data.get('analysis_data', []) if first_data else []
        total_devices = len(analysis_data) if analysis_data else 0
        
        # Count incidents with null checks
        incidents_count = 0
        for data in all_heatmap_data:
            if data and isinstance(data, dict):
                incidents = data.get('incidents', [])
                if incidents:
                    incidents_count += len(incidents)
        
        generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Prepare data for JavaScript
        mosaic_data_for_js = []
        timeline_ticks = []
        
        for i, heatmap_data in enumerate(all_heatmap_data):
            # Skip if heatmap_data is None or not a dict
            if not heatmap_data or not isinstance(heatmap_data, dict):
                continue
                
            # Process analysis data - only include devices with actual analysis
            analysis_items = []
            has_incidents = False
            
            if heatmap_data and isinstance(heatmap_data, dict):
                analysis_data = heatmap_data.get('analysis_data', [])
                if analysis_data and isinstance(analysis_data, list):
                    for item in analysis_data:
                        if item and isinstance(item, dict):
                            # Host endpoint now guarantees all images have analysis_json
                            analysis_json = item.get('analysis_json')
                            
                            host_name = item.get('host_name', 'Unknown')
                            device_id = item.get('device_id', 'Unknown')
                            has_error = item.get('error') is not None
                            
                            # Safe access to analysis_json (guaranteed to exist from host)
                            if not analysis_json or not isinstance(analysis_json, dict):
                                analysis_json = {}
                            
                            # Check if this device has incidents
                            device_has_incidents = (
                                analysis_json.get('freeze', False) or
                                analysis_json.get('blackscreen', False) or
                                not analysis_json.get('audio', True)
                            )
                            
                            if device_has_incidents:
                                has_incidents = True
                            
                            # Generate table row (matching React component exactly)
                            has_video = not analysis_json.get('blackscreen', False) and not analysis_json.get('freeze', False)
                            has_audio = analysis_json.get('audio', True)
                            volume_percentage = analysis_json.get('volume_percentage', 0)
                            mean_volume_db = analysis_json.get('mean_volume_db', -100)
                            blackscreen_percentage = analysis_json.get('blackscreen_percentage', 0)
                            freeze_diffs = analysis_json.get('freeze_diffs', [])
                            
                            # Format freeze diffs as comma-separated string
                            freeze_diffs_str = ', '.join(map(str, freeze_diffs)) if freeze_diffs else ''
                            
                            analysis_items.append(f"""
                            <tr>
                                <td>{host_name}-{device_id}</td>
                                <td><span class="chip {'success' if has_audio else 'error'}">{'Yes' if has_audio else 'No'}</span></td>
                                <td><span class="chip {'success' if has_video else 'error'}">{'Yes' if has_video else 'No'}</span></td>
                                <td>{volume_percentage}%</td>
                                <td>{mean_volume_db} dB</td>
                                <td><span class="{'text-success' if not analysis_json.get('blackscreen', False) else 'text-error'}">{'No' if not analysis_json.get('blackscreen', False) else f'Yes ({blackscreen_percentage}%)'}</span></td>
                                <td><span class="{'text-success' if not analysis_json.get('freeze', False) else 'text-error'}">{'No' if not analysis_json.get('freeze', False) else f'Yes ({freeze_diffs_str})'}</span></td>
                            </tr>
                            """)
            
            # Add to JavaScript data
            mosaic_data_for_js.append({
                'mosaic_url': heatmap_data.get('mosaic_url', ''),
                'analysis_html': ''.join(analysis_items),
                'timestamp': heatmap_data.get('timestamp', ''),
                'has_incidents': has_incidents
            })
            
            # Create timeline tick
            tick_position = (i / max(1, total_timestamps - 1)) * 100
            tick_class = "incident" if has_incidents else "normal"
            timeline_ticks.append(f"""
            <div class="timeline-tick {tick_class}" style="left: {tick_position}%" title="{heatmap_data.get('timestamp', '')}"></div>
            """)
        
        # Get first frame data safely
        first_data = all_heatmap_data[0] if all_heatmap_data else {}
        first_mosaic_url = first_data.get('mosaic_url', '') if first_data else ''
        first_analysis_items = mosaic_data_for_js[0]['analysis_html'] if mosaic_data_for_js else ''
        
        # Create timeframe string
        if total_timestamps > 1 and all_heatmap_data:
            first_timestamp = all_heatmap_data[0].get('timestamp', '') if all_heatmap_data[0] else ''
            last_timestamp = all_heatmap_data[-1].get('timestamp', '') if all_heatmap_data[-1] else ''
            timeframe = f"{first_timestamp} - {last_timestamp}"
        else:
            timeframe = first_data.get('timestamp', '') if first_data else ''
        
        # Fill template
        html_content = template.format(
            timeframe=timeframe,
            generated_at=generated_at,
            total_devices=total_devices,
            total_timestamps=total_timestamps,
            incidents_count=incidents_count,
            first_mosaic_url=first_mosaic_url,
            max_frame=max(0, total_timestamps - 1),
            timeline_ticks=''.join(timeline_ticks),
            first_analysis_items=first_analysis_items,
            mosaic_data_json=json.dumps(mosaic_data_for_js)
        )
        
        return html_content
        
    except Exception as e:
        print(f"[@heatmap_report_utils] Error details: {str(e)}")
        return f"<html><body><h1>Error generating comprehensive heatmap HTML</h1><p>{str(e)}</p></body></html>" 