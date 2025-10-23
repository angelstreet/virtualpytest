"""
KPI Report Template

Minimal HTML template for KPI measurement reports with thumbnail evidence.
"""

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
            padding: 20px 30px;
        }}
        
        .header h1 {{
            font-size: 36px;
            margin: 0 0 10px 0;
            font-weight: 600;
        }}
        
        .header .meta {{
            font-size: 14px;
            opacity: 0.95;
            line-height: 1.8;
            margin: 10px 0 5px 0;
        }}
        
        .header .meta-line {{
            margin: 3px 0;
            font-size: 13px;
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✓ KPI: {kpi_ms}ms</h1>
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

