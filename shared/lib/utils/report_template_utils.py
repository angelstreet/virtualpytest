"""
Report Template Utilities

This module contains the HTML template for validation reports with embedded CSS and JavaScript.
Separated from main report_utils.py for better maintainability.
"""

def create_themed_html_template() -> str:
    """Create the themed HTML template with embedded CSS and theme system."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validation Report - {script_name}</title>
    <style>
        :root {{
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
        }}
        
        [data-theme="dark"] {{
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
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.4;
            color: var(--text-primary);
            background: var(--bg-primary);
            padding: 10px;
            font-size: 14px;
            transition: background-color 0.3s ease, color 0.3s ease;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: var(--bg-secondary);
            border-radius: 6px;
            box-shadow: var(--shadow);
            overflow: hidden;
            transition: background-color 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .header {{
            background: var(--header-bg);
            color: white;
            padding: 8px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            min-height: 40px;
        }}
        
        .header-left {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .header h1 {{
            font-size: 1.4em;
            font-weight: 600;
        }}
        
        .header .time-info {{
            font-size: 0.85em;
            opacity: 0.9;
            white-space: nowrap;
        }}
        
        .theme-toggle {{
            display: flex;
            align-items: center;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 20px;
            padding: 2px;
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
        }}
        
        .theme-toggle:hover {{
            background: rgba(255,255,255,0.2);
        }}
        
        .theme-option {{
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
        }}
        
        .theme-option.active {{
            background: rgba(255,255,255,0.9);
            color: #1976d2;
        }}
        
        .theme-slider {{
            position: absolute;
            top: 2px;
            left: 2px;
            width: calc(33.33% - 2px);
            height: calc(100% - 4px);
            background: rgba(255,255,255,0.9);
            border-radius: 16px;
            transition: transform 0.2s ease;
            z-index: 1;
        }}
        
        .theme-slider.light {{
            transform: translateX(0);
        }}
        
        .theme-slider.dark {{
            transform: translateX(100%);
        }}
        
        .theme-slider.system {{
            transform: translateX(200%);
        }}
        
        .summary {{
            padding: 12px 20px;
            background: var(--bg-tertiary);
            border-bottom: 1px solid var(--border-color);
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 8px;
            align-items: center;
        }}
        
        .summary-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            background: var(--bg-secondary);
            border-radius: 4px;
            border: 1px solid var(--border-light);
            font-size: 0.9em;
            transition: all 0.3s ease;
        }}
        
        .summary-item .label {{
            color: var(--text-secondary);
            font-weight: 500;
        }}
        
        .summary-item .value {{
            font-weight: 600;
        }}
        
        .success {{
            color: var(--success-color);
        }}
        
        .failure {{
            color: var(--failure-color);
        }}
        
        .neutral {{
            color: var(--text-secondary);
        }}
        
        .content {{
            padding: 15px 20px;
        }}
        
        .section {{
            margin-bottom: 20px;
        }}
        
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            cursor: pointer;
            padding: 8px 0;
            border-bottom: 1px solid var(--border-light);
            transition: border-color 0.3s ease;
        }}
        
        .section-header h2 {{
            color: var(--text-primary);
            font-size: 1.1em;
            font-weight: 600;
        }}
        
        .toggle-btn {{
            background: none;
            border: none;
            font-size: 1.2em;
            cursor: pointer;
            color: var(--text-secondary);
            transition: transform 0.2s, color 0.3s ease;
        }}
        
        .toggle-btn.expanded {{
            transform: rotate(90deg);
        }}
        
        .collapsible-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease;
        }}
        
        .collapsible-content.expanded {{
            max-height: 2000px;
        }}
        
        .steps-expanded {{
            max-height: 2000px;
        }}
        
        .step-list {{
            border: 1px solid var(--border-light);
            border-radius: 4px;
            overflow: hidden;
            transition: border-color 0.3s ease;
        }}
        
        .step-item {{
            display: flex;
            align-items: center;
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-light);
            cursor: pointer;
            transition: background-color 0.2s, border-color 0.3s ease;
        }}
        
        .step-item:last-child {{
            border-bottom: none;
        }}
        
        .step-item:hover {{
            background: var(--step-hover);
        }}
        
        .step-item.success {{
            border-left: 3px solid var(--success-color);
        }}
        
        .step-item.failure {{
            border-left: 3px solid var(--failure-color);
        }}
        
        .step-number {{
            width: 30px;
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 0.9em;
        }}
        
        .step-status {{
            width: 50px;
            text-align: center;
        }}
        
        .step-status-badge {{
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
            transition: all 0.3s ease;
        }}
        
        .step-status-badge.success {{
            background: var(--success-bg);
            color: var(--success-text);
        }}
        
        .step-status-badge.failure {{
            background: var(--failure-bg);
            color: var(--failure-text);
        }}
        
        .step-message {{
            flex: 1;
            padding-left: 12px;
            font-size: 0.9em;
        }}
        
        .step-timing-inline {{
            font-size: 0.8em;
            color: var(--text-secondary);
            margin-left: 10px;
            white-space: nowrap;
        }}
        
        .step-details {{
            display: none;
            padding: 12px;
            background: var(--bg-tertiary);
            border-top: 1px solid var(--border-light);
            transition: all 0.3s ease;
        }}
        
        .step-details.expanded {{
            display: block;
        }}
        
        .step-details-content {{
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 15px;
            align-items: start;
        }}
        
        .step-info {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .step-timing {{
            display: flex;
            gap: 15px;
            font-size: 0.85em;
            color: var(--text-secondary);
        }}
        
        .step-actions {{
            font-size: 0.9em;
        }}
        
        .step-actions strong {{
            color: var(--text-primary);
        }}
        
        .action-item, .verification-item {{
            margin: 4px 0;
            padding: 4px 8px;
            background: var(--bg-secondary);
            border-radius: 4px;
            border-left: 3px solid var(--border-color);
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
        }}
        
        .action-item {{
            border-left-color: #17a2b8;
        }}
        
        .verification-item {{
            border-left-color: #6f42c1;
        }}
        
        .verification-result-badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.75em;
            font-weight: bold;
            margin-left: 8px;
        }}
        
        .verification-result-badge.success {{
            background-color: var(--success-bg);
            color: var(--success-color);
        }}
        
        .verification-result-badge.failure {{
            background-color: var(--failure-bg);
            color: var(--failure-color);
        }}
        
        .verification-error {{
            color: var(--failure-color);
            font-style: italic;
            font-size: 0.8em;
            margin-left: 4px;
        }}
        
        /* Analysis results styles */
        .analysis-item {{
            margin: 4px 0;
            padding: 4px 8px;
            background: var(--bg-secondary);
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        
        .analysis-item.motion {{
            border-left: 3px solid #28a745;
        }}
        
        .analysis-item.subtitle {{
            border-left: 3px solid #007bff;
        }}
        
        .analysis-item.audio-menu {{
            border-left: 3px solid #6f42c1;
        }}
        
        .analysis-detail {{
            margin: 2px 0 2px 16px;
            padding: 2px 4px;
            font-size: 0.8em;
            font-weight: normal;
            color: var(--text-secondary);
            font-family: 'Courier New', monospace;
        }}
        
        /* Summary state container styles */
        .summary-state-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            align-items: start;
        }}
        
        .execution-summary {{
            background: var(--bg-tertiary);
            border: 1px solid var(--border-light);
            border-radius: 6px;
            padding: 15px;
        }}
        
        .execution-summary h3 {{
            margin: 0 0 10px 0;
            color: var(--text-primary);
            font-size: 1.1em;
            border-bottom: 1px solid var(--border-light);
            padding-bottom: 8px;
        }}
        
        .summary-stats {{
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.6;
            color: var(--text-primary);
        }}
        
        .summary-stats .stat-line {{
            margin: 4px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .summary-stats .stat-emoji {{
            width: 20px;
            text-align: center;
        }}
        
        .summary-stats .stat-success {{
            color: var(--success-color);
            font-weight: bold;
        }}
        
        .summary-stats .stat-failure {{
            color: var(--failure-color);
            font-weight: bold;
        }}
        
        .summary-stats .stat-warning {{
            color: #ffc107;
            font-weight: bold;
        }}
        
        .state-screenshots {{
            text-align: center;
        }}
        
        .state-screenshots h3 {{
            margin: 0 0 15px 0;
            color: var(--text-primary);
            font-size: 1.1em;
        }}
        
        .test-video-section {{
            margin-top: 20px;
            text-align: center;
        }}
        
        .test-video-section h4 {{
            margin: 0 0 10px 0;
            color: var(--text-primary);
            font-size: 1em;
        }}
        
        .video-thumbnail {{
            position: relative;
            border-radius: 8px;
            overflow: hidden;
            background: var(--bg-secondary);
            cursor: pointer;
            transition: transform 0.2s ease;
        }}
        
        .video-thumbnail:hover {{
            transform: scale(1.02);
        }}
        
        .video-thumbnail video {{
            width: 100%;
            height: auto;
            display: block;
        }}
        
        .video-thumbnail .play-overlay {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.7);
            border-radius: 50%;
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 20px;
        }}
        
        .video-label {{
            position: absolute;
            bottom: 5px;
            left: 5px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.8em;
        }}
        
        @media (max-width: 768px) {{
            .summary-state-container {{
                grid-template-columns: 1fr;
                gap: 15px;
            }}
        }}
        
        /* Retry action styles */
        .retry-action-item {{
            margin: 4px 0;
            padding: 4px 8px;
            background: var(--bg-secondary);
            border-radius: 4px;
            border-left: 3px solid #ffc107;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
        }}
        
        .retry-action-item.executed {{
            border-left-color: #fd7e14;
            background: rgba(253, 126, 20, 0.1);
        }}
        
        .retry-action-item.available {{
            border-left-color: #ffc107;
            background: rgba(255, 193, 7, 0.1);
            opacity: 0.7;
        }}
        
        .retry-status {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.75em;
            font-weight: bold;
            margin-left: 8px;
        }}
        
        .retry-status.executed {{
            background-color: rgba(253, 126, 20, 0.2);
            color: #fd7e14;
        }}
        
        .retry-status.available {{
            background-color: rgba(255, 193, 7, 0.2);
            color: #856404;
        }}
        
        .step-screenshot-container {{
            text-align: right;
        }}
        
        .screenshot-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }}
        
        .screenshot-container {{
            text-align: center;
        }}
        
        .screenshot-label {{
            display: none;
        }}
        
        .screenshot-thumbnail {{
            width: 100%;
            max-width: 200px;
            height: 120px;
            object-fit: cover;
            border-radius: 4px;
            border: 2px solid var(--border-color);
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .screenshot-thumbnail:hover {{
            border-color: #4a90e2;
            transform: scale(1.02);
            box-shadow: var(--shadow-hover);
        }}
        
        .screenshot-row {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: flex-start;
        }}
        
        .screenshot-row .screenshot-container {{
            flex: 0 0 auto;
        }}
        
        .screenshot-row .screenshot-thumbnail {{
            max-width: 150px;
            height: 90px;
        }}
        
        .screenshot-modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: var(--modal-bg);
            transition: background-color 0.3s ease;
        }}
        
        .screenshot-modal.active {{
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        
        .modal-content {{
            position: relative;
            max-width: 95%;
            max-height: 95%;
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        
        .modal-header {{
            text-align: center;
            margin-bottom: 15px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }}
        
        .modal-header h3 {{
            margin: 0;
            color: var(--text-primary);
            font-size: 1.2em;
        }}
        
        .action-info {{
            margin-top: 8px;
            color: var(--text-secondary);
            font-size: 0.9em;
            font-family: monospace;
            background: var(--bg-tertiary);
            padding: 5px 10px;
            border-radius: 4px;
        }}
        
        .modal-body {{
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .modal-body img {{
            width: 800px;
            height: 450px;
            max-width: 85vw;
            max-height: 75vh;
            object-fit: contain;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            background: #f8f9fa;
        }}
        
        .nav-arrow {{
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(0,0,0,0.7);
            color: white;
            border: none;
            font-size: 30px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            cursor: pointer;
            z-index: 1001;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .nav-arrow:hover {{
            background: rgba(0,0,0,0.9);
        }}
        
        .nav-arrow:disabled {{
            opacity: 0.3;
            cursor: not-allowed;
        }}
        
        .nav-prev {{
            left: -60px;
        }}
        
        .nav-next {{
            right: -60px;
        }}
        
        .modal-footer {{
            text-align: center;
            margin-top: 15px;
            padding-top: 10px;
            border-top: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 0.9em;
        }}
        
        .screenshot-modal .close {{
            position: absolute;
            top: -10px;
            right: -10px;
            color: var(--text-primary);
            background: var(--bg-secondary);
            border: 2px solid var(--border-color);
            border-radius: 50%;
            width: 30px;
            height: 30px;
            font-size: 20px;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .screenshot-modal .close:hover {{
            background: var(--failure-color);
            color: white;
            border-color: var(--failure-color);
        }}
        
        .error-section {{
            background: var(--error-bg);
            border: 1px solid var(--error-border);
            border-radius: 4px;
            padding: 12px;
            margin-top: 15px;
            transition: all 0.3s ease;
        }}
        
        .error-section h3 {{
            color: var(--failure-text);
            margin-bottom: 8px;
            font-size: 1em;
        }}
        
        .error-message {{
            font-family: 'Courier New', monospace;
            background: var(--bg-secondary);
            padding: 10px;
            border-radius: 4px;
            border: 1px solid var(--border-color);
            white-space: pre-wrap;
            overflow-x: auto;
            font-size: 0.85em;
            transition: all 0.3s ease;
        }}
        
        @media (max-width: 768px) {{
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
            
            .screenshot-grid {{
                grid-template-columns: 1fr;
            }}
            
            .header {{
                flex-direction: column;
                gap: 8px;
                text-align: center;
                padding: 12px 20px;
            }}
            
                         .header-left {{
                 flex-direction: column;
                 gap: 8px;
             }}
             
             .theme-toggle {{
                 order: -1;
                 margin-bottom: 8px;
             }}
             
             .step-details-content {{
                 grid-template-columns: 1fr;
                 gap: 10px;
             }}
             
             .step-screenshot-container {{
                 text-align: center;
             }}
             
             .step-timing-inline {{
                 display: block;
                 margin-top: 5px;
                 margin-left: 0;
             }}
        }}
    </style>
    <script>
        // Theme management system
        class ThemeManager {{
            constructor() {{
                this.currentMode = this.getSavedTheme() || 'system';
                this.systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                this.init();
            }}
            
            init() {{
                this.applyTheme();
                this.setupSystemThemeListener();
                this.setupThemeToggle();
            }}
            
            getSavedTheme() {{
                return localStorage.getItem('validation-report-theme');
            }}
            
            saveTheme(mode) {{
                localStorage.setItem('validation-report-theme', mode);
            }}
            
            getActualTheme() {{
                if (this.currentMode === 'system') {{
                    return this.systemPrefersDark ? 'dark' : 'light';
                }}
                return this.currentMode;
            }}
            
            applyTheme() {{
                const actualTheme = this.getActualTheme();
                document.documentElement.setAttribute('data-theme', actualTheme);
                this.updateToggleButtons();
                this.updateSlider();
            }}
            
            setTheme(mode) {{
                this.currentMode = mode;
                this.saveTheme(mode);
                this.applyTheme();
            }}
            
            setupSystemThemeListener() {{
                const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
                mediaQuery.addEventListener('change', (e) => {{
                    this.systemPrefersDark = e.matches;
                    if (this.currentMode === 'system') {{
                        this.applyTheme();
                    }}
                }});
            }}
            
            setupThemeToggle() {{
                const themeOptions = document.querySelectorAll('.theme-option');
                themeOptions.forEach(option => {{
                    option.addEventListener('click', (e) => {{
                        const mode = e.target.dataset.theme;
                        this.setTheme(mode);
                    }});
                }});
            }}
            
            updateToggleButtons() {{
                const themeOptions = document.querySelectorAll('.theme-option');
                themeOptions.forEach(option => {{
                    option.classList.toggle('active', option.dataset.theme === this.currentMode);
                }});
            }}
            
            updateSlider() {{
                const slider = document.querySelector('.theme-slider');
                if (slider) {{
                    slider.className = `theme-slider ${{this.currentMode}}`;
                }}
            }}
        }}
        
        // Initialize theme manager when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {{
            window.themeManager = new ThemeManager();
        }});
        
        function toggleSection(sectionId) {{
            const content = document.getElementById(sectionId);
            const button = document.querySelector(`[onclick="toggleSection('${{sectionId}}')"] .toggle-btn`);
            
            if (content.classList.contains('expanded')) {{
                content.classList.remove('expanded');
                button.classList.remove('expanded');
                button.textContent = '▶';
            }} else {{
                content.classList.add('expanded');
                button.classList.add('expanded');
                button.textContent = '▼';
            }}
        }}
        
        function toggleStep(stepId) {{
            const details = document.getElementById(stepId);
            if (details.classList.contains('expanded')) {{
                details.classList.remove('expanded');
            }} else {{
                details.classList.add('expanded');
            }}
        }}
        
        let currentModalData = null;
        let currentScreenshotIndex = 0;
        
        function openScreenshotModal(modalDataJson) {{
            try {{
                currentModalData = JSON.parse(modalDataJson.replace(/&quot;/g, '"').replace(/&#x27;/g, "'"));
                currentScreenshotIndex = currentModalData.current_index || 0;
                
                console.log('Modal data:', currentModalData);
                console.log('Screenshots:', currentModalData.screenshots);
                
                updateModalContent();
                
                const modal = document.getElementById('screenshot-modal');
                modal.classList.add('active');
            }} catch (e) {{
                console.error('Error opening screenshot modal:', e);
                console.error('Modal data JSON:', modalDataJson);
            }}
        }}
        
        function updateModalContent() {{
            if (!currentModalData || !currentModalData.screenshots) return;
            
            const screenshots = currentModalData.screenshots;
            const current = screenshots[currentScreenshotIndex];
            
            // Update image
            const img = document.getElementById('modal-img');
            img.src = current.url;
            
            // Update step title
            const title = document.getElementById('modal-step-title');
            title.textContent = currentModalData.step_title;
            
            // Update action info
            const actionInfo = document.getElementById('modal-action-info');
            if (current.command) {{
                const cmd = current.command;
                const params = current.params || {{}};
                const paramsStr = Object.keys(params).length > 0 ? 
                    ' ' + Object.entries(params).map(([k,v]) => `${{k}}="${{v}}"`).join(' ') : '';
                actionInfo.textContent = `${{current.label}}: ${{cmd}}${{paramsStr}}`;
                actionInfo.style.display = 'block';
            }} else {{
                actionInfo.textContent = current.label;
                actionInfo.style.display = 'block';
            }}
            
            // Update counter
            const counter = document.getElementById('modal-counter');
            counter.textContent = `${{currentScreenshotIndex + 1}} / ${{screenshots.length}}`;
            
            // Update navigation buttons
            const prevBtn = document.getElementById('modal-prev');
            const nextBtn = document.getElementById('modal-next');
            
            prevBtn.disabled = currentScreenshotIndex === 0;
            nextBtn.disabled = currentScreenshotIndex === screenshots.length - 1;
            
            // Hide arrows if only one screenshot
            if (screenshots.length <= 1) {{
                prevBtn.style.display = 'none';
                nextBtn.style.display = 'none';
            }} else {{
                prevBtn.style.display = 'flex';
                nextBtn.style.display = 'flex';
            }}
        }}
        
        function navigateScreenshot(direction) {{
            if (!currentModalData || !currentModalData.screenshots) return;
            
            const newIndex = currentScreenshotIndex + direction;
            if (newIndex >= 0 && newIndex < currentModalData.screenshots.length) {{
                currentScreenshotIndex = newIndex;
                updateModalContent();
            }}
        }}
        
        function closeScreenshot() {{
            const modal = document.getElementById('screenshot-modal');
            modal.classList.remove('active');
            currentModalData = null;
            currentScreenshotIndex = 0;
        }}
        
        // Legacy function for backward compatibility
        function openScreenshot(src) {{
            const modalData = {{
                step_title: 'Screenshot',
                screenshots: [{{
                    label: 'Screenshot',
                    url: src,
                    command: null,
                    params: {{}}
                }}],
                current_index: 0
            }};
            openScreenshotModal(JSON.stringify(modalData));
        }}
        
        // Video functionality: Opens in new tab (no modal needed)
        
        // Close modal when clicking outside the image
        document.addEventListener('DOMContentLoaded', function() {{
            const modal = document.getElementById('screenshot-modal');
            if (modal) {{
                modal.addEventListener('click', function(e) {{
                    if (e.target === modal) {{
                        closeScreenshot();
                    }}
                }});
            }}
            
            // Keyboard navigation
            document.addEventListener('keydown', function(e) {{
                if (modal && modal.classList.contains('active')) {{
                    switch(e.key) {{
                        case 'ArrowLeft':
                            e.preventDefault();
                            navigateScreenshot(-1);
                            break;
                        case 'ArrowRight':
                            e.preventDefault();
                            navigateScreenshot(1);
                            break;
                        case 'Escape':
                            e.preventDefault();
                            closeScreenshot();
                            break;
                    }}
                }}
            }});
        }});
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <h1>{script_name}</h1>
                <div class="time-info">
                    Start: {start_time} | End: {end_time}
                </div>
            </div>
            <div class="theme-toggle">
                <div class="theme-slider light"></div>
                <div class="theme-option" data-theme="light">Light</div>
                <div class="theme-option" data-theme="dark">Dark</div>
                <div class="theme-option" data-theme="system">System</div>
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-grid">
                <div class="summary-item">
                    <span class="label">Status:</span>
                    <span class="value {success_class}">{success_status}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Duration:</span>
                    <span class="value neutral">{execution_time}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Device:</span>
                    <span class="value neutral">{device_name}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Host:</span>
                    <span class="value neutral">{host_name}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Steps:</span>
                    <span class="value neutral">{passed_steps}/{total_steps}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Failed:</span>
                    <span class="value failure">{failed_steps}</span>
                </div>
            </div>
        </div>
        
        <div class="content">
            <div class="section">
                <div class="section-header" onclick="toggleSection('screenshots-content')">
                <h2>Execution Summary & State</h2>
                    <button class="toggle-btn">▶</button>
                </div>
                <div id="screenshots-content" class="collapsible-content">
                    <div class="summary-state-container">
                        <div class="execution-summary">
                            {execution_summary}
                        </div>
                        <div class="state-screenshots">
                            <h3>Initial & Final State</h3>
                            <div class="screenshot-grid">
                                {initial_screenshot}
                                {final_screenshot}
                            </div>
                            <div class="test-video-section">
                                <h4>Test Execution Video</h4>
                                {test_video}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                                <div class="section-header" onclick="toggleSection('steps-content')">
                    <h2>Test Steps ({passed_steps}/{total_steps} passed)</h2>
                    <button class="toggle-btn expanded">▼</button>
                </div>
                <div id="steps-content" class="collapsible-content steps-expanded">
                    {step_results_html}
                </div>
            </div>
            
            {error_section}
        </div>
    </div>
    
    <div id="screenshot-modal" class="screenshot-modal">
        <div class="modal-content">
            <span class="close" onclick="closeScreenshot()">&times;</span>
            <div class="modal-header">
                <h3 id="modal-step-title">Screenshot</h3>
                <div id="modal-action-info" class="action-info"></div>
            </div>
            <div class="modal-body">
                <button id="modal-prev" class="nav-arrow nav-prev" onclick="navigateScreenshot(-1)">‹</button>
                <img id="modal-img" src="" alt="Screenshot">
                <button id="modal-next" class="nav-arrow nav-next" onclick="navigateScreenshot(1)">›</button>
            </div>
            <div class="modal-footer">
                <span id="modal-counter">1 / 1</span>
            </div>
        </div>
    </div>
</body>
</html>""" 