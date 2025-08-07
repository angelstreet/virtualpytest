"""
Report Template CSS Styles

Contains all CSS styles for the HTML validation reports.
"""

def get_report_css() -> str:
    """Get the complete CSS styles for the report template."""
    return """
        :root {
            /* Light theme variables */
            --bg-primary: #f8f9fa;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f8f9fa;
            --text-primary: #333333;
            --text-secondary: #6c757d;
            --border-color: #dee2e6;
            --border-light: #e9ecef;
            --shadow: 0 1px 3px rgba(0,0,0,0.1);
            --shadow-hover: 0 2px 8px rgba(0,0,0,0.15);
            --success-color: #28a745;
            --success-bg: #d4edda;
            --success-text: #155724;
            --failure-color: #dc3545;
            --failure-bg: #f8d7da;
            --failure-text: #721c24;
            --header-bg: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
            --step-hover: #f8f9fa;
            --error-bg: #f8d7da;
            --error-border: #f5c6cb;
            --modal-bg: rgba(0,0,0,0.8);
        }
        
        [data-theme="dark"] {
            /* Dark theme variables */
            --bg-primary: #0a0a0a;
            --bg-secondary: #1a1a1a;
            --bg-tertiary: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #a0a0a0;
            --border-color: #404040;
            --border-light: #303030;
            --shadow: 0 4px 6px rgba(0,0,0,0.3);
            --shadow-hover: 0 8px 16px rgba(0,0,0,0.4);
            --success-color: #4ade80;
            --success-bg: #1a4a2a;
            --success-text: #86efac;
            --failure-color: #f87171;
            --failure-bg: #4a1a1a;
            --failure-text: #fca5a5;
            --header-bg: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
            --step-hover: #2a2a2a;
            --error-bg: #4a1a1a;
            --error-border: #6b2c2c;
            --modal-bg: rgba(0,0,0,0.9);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.4;
            color: var(--text-primary);
            background: var(--bg-primary);
            padding: 10px;
            font-size: 14px;
            transition: background-color 0.3s ease, color 0.3s ease;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: var(--bg-secondary);
            border-radius: 6px;
            box-shadow: var(--shadow);
            overflow: hidden;
            transition: background-color 0.3s ease, box-shadow 0.3s ease;
        }
        
        .header {
            background: var(--header-bg);
            color: white;
            padding: 8px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            min-height: 40px;
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .header h1 {
            font-size: 1.4em;
            font-weight: 600;
        }
        
        .header .time-info {
            font-size: 0.85em;
            opacity: 0.9;
            white-space: nowrap;
        }
        
        .theme-toggle {
            display: flex;
            align-items: center;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 20px;
            padding: 2px;
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
        }
        
        .theme-toggle:hover {
            background: rgba(255,255,255,0.2);
        }
        
        .theme-option {
            padding: 4px 10px;
            border-radius: 16px;
            font-size: 0.75em;
            font-weight: 500;
            transition: all 0.2s ease;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            position: relative;
            z-index: 2;
        }
        
        .theme-option.active {
            background: rgba(255,255,255,0.9);
            color: #1976d2;
        }
        
        .theme-slider {
            position: absolute;
            top: 2px;
            left: 2px;
            width: calc(33.33% - 2px);
            height: calc(100% - 4px);
            background: rgba(255,255,255,0.9);
            border-radius: 16px;
            transition: transform 0.2s ease;
            z-index: 1;
        }
        
        .theme-slider.light {
            transform: translateX(0);
        }
        
        .theme-slider.dark {
            transform: translateX(100%);
        }
        
        .theme-slider.system {
            transform: translateX(200%);
        }
        
        .summary {
            padding: 12px 20px;
            background: var(--bg-tertiary);
            border-bottom: 1px solid var(--border-color);
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 8px;
            align-items: center;
        }
        
        .summary-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            background: var(--bg-secondary);
            border-radius: 4px;
            border: 1px solid var(--border-light);
            font-size: 0.9em;
            transition: all 0.3s ease;
        }
        
        .summary-item .label {
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .summary-item .value {
            font-weight: 600;
        }
        
        .success {
            color: var(--success-color);
        }
        
        .failure {
            color: var(--failure-color);
        }
        
        .neutral {
            color: var(--text-secondary);
        }
        
        .content {
            padding: 15px 20px;
        }
        
        .section {
            margin-bottom: 20px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            cursor: pointer;
            padding: 8px 0;
            border-bottom: 1px solid var(--border-light);
            transition: border-color 0.3s ease;
        }
        
        .section-header h2 {
            color: var(--text-primary);
            font-size: 1.1em;
            font-weight: 600;
        }
        
        .toggle-btn {
            background: none;
            border: none;
            font-size: 1.2em;
            cursor: pointer;
            color: var(--text-secondary);
            transition: transform 0.2s, color 0.3s ease;
        }
        
        .toggle-btn.expanded {
            transform: rotate(90deg);
        }
        
        .collapsible-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease;
        }
        
        .collapsible-content.expanded {
            max-height: 2000px;
        }
        
        .steps-expanded {
            max-height: 2000px;
        }
        
        .step-list {
            border: 1px solid var(--border-light);
            border-radius: 4px;
            overflow: hidden;
            transition: border-color 0.3s ease;
        }
        
        .step-item {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-light);
            cursor: pointer;
            transition: background-color 0.2s, border-color 0.3s ease;
        }
        
        .step-item:last-child {
            border-bottom: none;
        }
        
        .step-item:hover {
            background: var(--step-hover);
        }
        
        .step-item.success {
            border-left: 3px solid var(--success-color);
        }
        
        .step-item.failure {
            border-left: 3px solid var(--failure-color);
        }
        
        .step-number {
            width: 30px;
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 0.9em;
        }
        
        .step-status {
            width: 50px;
            text-align: center;
        }
        
        .step-status-badge {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
            transition: all 0.3s ease;
        }
        
        .step-status-badge.success {
            background: var(--success-bg);
            color: var(--success-text);
        }
        
        .step-status-badge.failure {
            background: var(--failure-bg);
            color: var(--failure-text);
        }
        
        .step-message {
            flex: 1;
            padding-left: 12px;
            font-size: 0.9em;
        }
        
        .step-timing-inline {
            font-size: 0.8em;
            color: var(--text-secondary);
            margin-left: 10px;
            white-space: nowrap;
        }
        
        .step-details {
            display: none;
            padding: 12px;
            background: var(--bg-tertiary);
            border-top: 1px solid var(--border-light);
            transition: all 0.3s ease;
        }
        
        .step-details.expanded {
            display: block;
        }
        
        .step-details-content {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 15px;
            align-items: start;
        }
        
        .step-info {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .step-timing {
            display: flex;
            gap: 15px;
            font-size: 0.85em;
            color: var(--text-secondary);
        }
        
        .step-actions {
            font-size: 0.9em;
        }
        
        .step-actions strong {
            color: var(--text-primary);
        }
        
        .action-item, .verification-item {
            margin: 4px 0;
            padding: 4px 8px;
            background: var(--bg-secondary);
            border-radius: 4px;
            border-left: 3px solid var(--border-color);
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
        }
        
        .action-item {
            border-left-color: #17a2b8;
        }
        
        .verification-item {
            border-left-color: #6f42c1;
        }
        
        .verification-result-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.75em;
            font-weight: bold;
            margin-left: 8px;
        }
        
        .verification-result-badge.success {
            background-color: var(--success-bg);
            color: var(--success-color);
        }
        
        .verification-result-badge.failure {
            background-color: var(--failure-bg);
            color: var(--failure-color);
        }
        
        .verification-error {
            color: var(--failure-color);
            font-style: italic;
            font-size: 0.8em;
            margin-left: 4px;
        }
        
        .verification-score {
            font-family: 'Courier New', monospace;
            font-size: 0.8em;
            margin-left: 8px;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: bold;
        }
        
        .verification-score.success {
            background-color: var(--success-bg);
            color: var(--success-color);
        }
        
        .verification-score.failure {
            background-color: var(--failure-bg);
            color: var(--failure-color);
        }
        
        @media (max-width: 768px) {
            .summary-grid {
                grid-template-columns: 1fr;
            }
            
            .header {
                flex-direction: column;
                gap: 8px;
                text-align: center;
                padding: 12px 20px;
            }
            
            .header-left {
                flex-direction: column;
                gap: 8px;
            }
            
            .theme-toggle {
                order: -1;
                margin-bottom: 8px;
            }
            
            .step-details-content {
                grid-template-columns: 1fr;
                gap: 10px;
            }
            
            .step-screenshot-container {
                text-align: center;
            }
            
            .step-timing-inline {
                display: block;
                margin-top: 5px;
                margin-left: 0;
            }
        }
    """