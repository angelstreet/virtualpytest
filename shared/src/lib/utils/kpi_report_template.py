"""
KPI Report Template

Minimal HTML template for KPI measurement reports with thumbnail evidence.
"""

def create_verification_card(index: int, verification: dict) -> str:
    """Create HTML for a single verification evidence card"""
    v_type = verification.get('type', 'image')
    command = verification.get('command', 'N/A')
    success = verification.get('success', False)
    
    if v_type == 'image':
        ref_url = verification.get('reference_url', '')
        src_url = verification.get('source_url', '')
        score = verification.get('matching_score', 0.0)
        threshold = verification.get('threshold', 0.8)
        area = verification.get('area', {})
        image_filter = verification.get('image_filter', 'none')
        
        area_str = f"x:{area.get('x', 0)}, y:{area.get('y', 0)}, w:{area.get('width', 'full')}, h:{area.get('height', 'full')}" if area else 'full screen'
        
        return f"""
        <div class="verification-card {'success' if success else ''}">
            <div class="verification-header">
                <span>#{index}: {command}</span>
                <span class="verification-status">{'✓ MATCH' if success else '✗ NO MATCH'}</span>
            </div>
            <div class="comparison-grid">
                <div class="comparison-image">
                    <img src="{src_url}" onclick="openModal(this.src)" alt="Source">
                    <div class="comparison-label">Source (cropped)</div>
                </div>
                <div class="comparison-vs">VS</div>
                <div class="comparison-image">
                    <img src="{ref_url}" onclick="openModal(this.src)" alt="Reference">
                    <div class="comparison-label">Reference (cropped)</div>
                </div>
                <div class="comparison-result">
                    <div class="score">{score:.3f}</div>
                    <div class="threshold">threshold: {threshold}</div>
                </div>
            </div>
        </div>
        """
    
    elif v_type == 'text':
        src_url = verification.get('source_url', '')
        searched_text = verification.get('searched_text', '')
        extracted_text = verification.get('extracted_text', '')
        confidence = verification.get('confidence', 0)
        language = verification.get('language', 'unknown')
        
        return f"""
        <div class="verification-card {'success' if success else ''}">
            <div class="verification-header">
                <span>#{index}: {command}</span>
                <span class="verification-status">{'✓ FOUND' if success else '✗ NOT FOUND'}</span>
            </div>
            <div style="display: grid; grid-template-columns: 200px 1fr; gap: 20px; margin: 15px 0;">
                <div class="comparison-image">
                    <img src="{src_url}" onclick="openModal(this.src)" alt="Source OCR">
                    <div class="comparison-label">Source (OCR)</div>
                </div>
                <div style="padding: 10px;">
                    <div class="param-row">
                        <span class="param-key">Searched Text:</span>
                        <span class="param-value">"{searched_text}"</span>
                    </div>
                    <div class="param-row">
                        <span class="param-key">Extracted Text:</span>
                        <span class="param-value">"{extracted_text[:100]}"</span>
                    </div>
                    <div class="param-row">
                        <span class="param-key">Language:</span>
                        <span class="param-value">{language} ({confidence}% confidence)</span>
                    </div>
                </div>
            </div>
        </div>
        """
    
    return ""


def create_kpi_report_template() -> str:
    """Create simple KPI report with 3 thumbnails and modal zoom."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KPI Report - {execution_result_id}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
            padding: 15px 25px;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin: 0 0 8px 0;
            font-weight: 600;
        }}
        
        .header .meta {{
            font-size: 13px;
            opacity: 0.95;
            line-height: 1.6;
            margin: 5px 0 0 0;
        }}
        
        .header .meta-line {{
            margin: 2px 0;
            font-size: 12px;
        }}
        
        .header .meta-inline {{
            display: inline-block;
            margin-right: 20px;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .section {{
            margin-bottom: 30px;
        }}
        
        .section h2 {{
            font-size: 18px;
            color: #666;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .thumbnails {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .thumb-card {{
            background: #fafafa;
            border-radius: 8px;
            padding: 15px;
            border: 2px solid #e0e0e0;
            transition: all 0.2s;
        }}
        
        .thumb-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .thumb-card h3 {{
            font-size: 13px;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            font-weight: 600;
        }}
        
        .thumb-card.match {{
            border-color: #4CAF50;
            background: #f1f8f4;
        }}
        
        .thumb-card.match h3 {{
            color: #4CAF50;
        }}
        
        .thumb-card img {{
            width: 100%;
            border-radius: 4px;
            cursor: pointer;
            display: block;
            border: 1px solid #ddd;
        }}
        
        .thumb-card img:hover {{
            opacity: 0.9;
        }}
        
        .thumb-card .timestamp {{
            font-size: 12px;
            color: #999;
            margin-top: 8px;
            font-family: 'Courier New', monospace;
        }}
        
        .details {{
            background: #fafafa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
        }}
        
        .details h2 {{
            color: #333;
            font-size: 16px;
            margin-bottom: 15px;
        }}
        
        .details-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        
        .detail-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .detail-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 4px;
            font-weight: 600;
        }}
        
        .detail-value {{
            font-size: 14px;
            color: #333;
            font-family: 'Courier New', monospace;
        }}
        
        /* Modal styles */
        .modal {{
            display: none;
            position: fixed;
            z-index: 9999;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            cursor: pointer;
        }}
        
        .modal.active {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .modal img {{
            max-width: 95%;
            max-height: 95%;
            box-shadow: 0 4px 24px rgba(0,0,0,0.5);
            cursor: default;
        }}
        
        .close {{
            position: absolute;
            top: 20px;
            right: 40px;
            color: white;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
            z-index: 10000;
        }}
        
        .close:hover {{
            color: #ccc;
        }}
        
        .hint {{
            text-align: center;
            color: #999;
            font-size: 13px;
            margin-top: 10px;
        }}
        
        /* Collapsible sections */
        details {{
            background: #fafafa;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        
        details[open] {{
            padding-bottom: 20px;
        }}
        
        details.action-details {{
            border-left: 4px solid #2196F3;
        }}
        
        details.verification-evidence {{
            border-left: 4px solid #FF9800;
        }}
        
        summary {{
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            padding: 5px 0;
            user-select: none;
            list-style: none;
        }}
        
        summary::-webkit-details-marker {{
            display: none;
        }}
        
        summary::before {{
            content: '▶ ';
            display: inline-block;
            transition: transform 0.2s;
        }}
        
        details[open] summary::before {{
            transform: rotate(90deg);
        }}
        
        .action-params {{
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }}
        
        .param-row {{
            display: flex;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        .param-row:last-child {{
            border-bottom: none;
        }}
        
        .param-key {{
            font-weight: 600;
            color: #666;
            min-width: 120px;
            font-size: 13px;
        }}
        
        .param-value {{
            color: #333;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        
        .verification-card {{
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
        }}
        
        .verification-card.success {{
            border-color: #4CAF50;
            background: #f1f8f4;
        }}
        
        .verification-header {{
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .verification-status {{
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 4px;
            background: #4CAF50;
            color: white;
        }}
        
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr auto 1fr auto;
            gap: 15px;
            align-items: center;
            margin: 15px 0;
        }}
        
        .comparison-image {{
            text-align: center;
        }}
        
        .comparison-image img {{
            max-width: 180px;
            border: 2px solid #ddd;
            border-radius: 6px;
            cursor: zoom-in;
        }}
        
        .comparison-image img:hover {{
            border-color: #2196F3;
        }}
        
        .comparison-label {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            font-weight: 600;
        }}
        
        .comparison-vs {{
            font-size: 18px;
            color: #999;
            font-weight: bold;
        }}
        
        .comparison-result {{
            text-align: center;
            font-size: 14px;
        }}
        
        .score {{
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }}
        
        .threshold {{
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✓ KPI: <span id="kpiDisplay" data-ms="{kpi_ms}">{kpi_ms}ms</span></h1>
            <div class="meta">
                <div class="meta-line">
                    <strong>Navigation:</strong> {from_node_label} → {to_node_label} &nbsp;|&nbsp; <strong>Last Action:</strong> {last_action}
                </div>
                <div class="meta-line">
                    <strong>Host:</strong> {host_name} &nbsp;|&nbsp; <strong>Device:</strong> {device_name} ({device_model}) &nbsp;|&nbsp; <strong>UI:</strong> {navigation_path}
                </div>
                <div class="meta-line">
                    <strong>Tree:</strong> {tree_id} &nbsp;|&nbsp; <strong>Action Set:</strong> {action_set_id} &nbsp;|&nbsp; <strong>Algorithm:</strong> {algorithm} &nbsp;|&nbsp; <strong>Scanned:</strong> {captures_scanned} frames
                </div>
            </div>
        </div>
        
        <div class="content">
            <div class="section">
                <div class="thumbnails">
                    <div class="thumb-card">
                        <h3>Before Action</h3>
                        <img src="{before_action_thumb}" onclick="openModal(this.src)" alt="Before action pressed">
                        <div class="timestamp">{before_action_time}</div>
                    </div>
                    <div class="thumb-card">
                        <h3>After Action</h3>
                        <img src="{after_action_thumb}" onclick="openModal(this.src)" alt="After action pressed">
                        <div class="timestamp">{after_action_time}</div>
                    </div>
                    <div class="thumb-card">
                        <h3>Before Match</h3>
                        <img src="{before_match_thumb}" onclick="openModal(this.src)" alt="Before match">
                        <div class="timestamp">{before_time}</div>
                    </div>
                    <div class="thumb-card match">
                        <h3>✓ Match Found</h3>
                        <img src="{match_thumb}" onclick="openModal('{match_original}')" alt="Match found" style="cursor: zoom-in;">
                        <div class="timestamp">{match_time}</div>
                        <div class="hint" style="font-size: 11px; margin-top: 4px; color: #4CAF50;">Click to view original</div>
                    </div>
                </div>
            </div>
            
            <!-- Action Details Section (Collapsible) -->
            <div class="section">
                <details class="action-details" open>
                    <summary>Last Action Executed</summary>
                    <div class="action-params">
                        <div class="param-row">
                            <span class="param-key">Command:</span>
                            <span class="param-value">{action_command}</span>
                        </div>
                        <div class="param-row">
                            <span class="param-key">Action Type:</span>
                            <span class="param-value">{action_type}</span>
                        </div>
                        <div class="param-row">
                            <span class="param-key">Parameters:</span>
                            <span class="param-value">{action_params}</span>
                        </div>
                        <div class="param-row">
                            <span class="param-key">Execution Time:</span>
                            <span class="param-value">{action_execution_time}ms</span>
                        </div>
                        <div class="param-row">
                            <span class="param-key">Wait Time:</span>
                            <span class="param-value">{action_wait_time}ms</span>
                        </div>
                        <div class="param-row">
                            <span class="param-key">Total Time:</span>
                            <span class="param-value">{action_total_time}ms</span>
                        </div>
                    </div>
                </details>
            </div>
            
            <!-- Verification Evidence Section (Collapsible) -->
            <div class="section">
                <details class="verification-evidence" open>
                    <summary>Verification ({verification_count})</summary>
                    {verification_cards}
                </details>
            </div>
            
            <div class="section">
                <div class="details">
                    <h2>📊 Measurement Details</h2>
                    <div class="details-grid">
                        <div class="detail-item">
                            <span class="detail-label">Execution Result ID</span>
                            <span class="detail-value">{execution_result_id}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">KPI Duration</span>
                            <span class="detail-value">{kpi_ms}ms</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Action Timestamp</span>
                            <span class="detail-value">{action_timestamp}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Match Timestamp</span>
                            <span class="detail-value">{match_timestamp}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Scan Window</span>
                            <span class="detail-value">{scan_window}s</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Captures Scanned</span>
                            <span class="detail-value">{captures_scanned} frames</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div id="modal" class="modal" onclick="closeModal()">
        <span class="close" onclick="closeModal()">&times;</span>
        <img id="modalImg" src="" alt="Full size">
    </div>
    
    <script>
        // Format milliseconds to smart format (only show non-zero units)
        function formatKPI() {{
            const kpiEl = document.getElementById('kpiDisplay');
            const ms = parseInt(kpiEl.dataset.ms);
            
            const minutes = Math.floor(ms / 60000);
            const seconds = Math.floor((ms % 60000) / 1000);
            const milliseconds = ms % 1000;
            
            let parts = [];
            if (minutes > 0) parts.push(minutes + 'm');
            if (seconds > 0) parts.push(seconds + 's');
            if (milliseconds > 0 || parts.length === 0) parts.push(milliseconds + 'ms');
            
            kpiEl.textContent = parts.join(' ');
        }}
        
        // Format on page load
        formatKPI();
        
        function openModal(src) {{
            event.stopPropagation();
            document.getElementById('modal').classList.add('active');
            document.getElementById('modalImg').src = src;
        }}
        
        function closeModal() {{
            document.getElementById('modal').classList.remove('active');
        }}
        
        // Close modal on ESC key
        document.addEventListener('keydown', function(event) {{
            if (event.key === 'Escape') {{
                closeModal();
            }}
        }});
    </script>
</body>
</html>"""

