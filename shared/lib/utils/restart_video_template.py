"""
Restart Video Report Template

Dedicated HTML template for restart video reports that focuses on video playback
and AI analysis results, similar to the frontend restart video player UI.
"""

def get_restart_video_css() -> str:
    """CSS styling for restart video report"""
    return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #000;
            color: #fff;
            overflow: hidden;
        }

        .video-container {
            position: relative;
            width: 100vw;
            height: 100vh;
            display: flex;
        }

        .video-player {
            flex: 1;
            position: relative;
            background: #000;
        }

        .video-element {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .video-controls {
            position: absolute;
            bottom: 20px;
            left: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.7);
            border-radius: 8px;
            padding: 12px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .play-button {
            background: none;
            border: none;
            color: #fff;
            font-size: 18px;
            cursor: pointer;
            padding: 8px;
            border-radius: 4px;
        }

        .play-button:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        .time-display {
            color: #fff;
            font-size: 14px;
            min-width: 80px;
        }

        .progress-bar {
            flex: 1;
            height: 4px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 2px;
            cursor: pointer;
            position: relative;
        }

        .progress-fill {
            height: 100%;
            background: #fff;
            border-radius: 2px;
            width: 0%;
            transition: width 0.1s;
        }

        .settings-panel {
            width: 400px;
            background: rgba(0, 0, 0, 0.95);
            border-left: 1px solid rgba(255, 255, 255, 0.1);
            padding: 24px;
            overflow-y: auto;
        }

        .settings-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }

        .settings-title {
            font-size: 18px;
            font-weight: 600;
        }

        .close-button {
            background: none;
            border: none;
            color: #fff;
            font-size: 20px;
            cursor: pointer;
            padding: 4px;
        }

        .analysis-section {
            margin-bottom: 24px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 24px;
        }

        .analysis-section:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }

        .section-header {
            display: flex;
            align-items: center;
            margin-bottom: 12px;
            cursor: pointer;
        }

        .section-title {
            font-size: 14px;
            font-weight: 600;
            margin-left: 8px;
            flex: 1;
        }

        .expand-icon {
            font-size: 12px;
            transition: transform 0.2s;
        }

        .expand-icon.expanded {
            transform: rotate(90deg);
        }

        .checkbox {
            width: 16px;
            height: 16px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 2px;
            background: transparent;
            cursor: pointer;
        }

        .checkbox.checked {
            background: #4CAF50;
            border-color: #4CAF50;
        }

        .language-select {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 4px;
            color: #fff;
            padding: 6px 8px;
            font-size: 12px;
            margin-left: 8px;
            min-width: 80px;
        }

        .analysis-content {
            margin-left: 24px;
            display: none;
        }

        .analysis-content.expanded {
            display: block;
        }

        .analysis-text {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            padding: 12px;
            font-size: 12px;
            line-height: 1.4;
            margin-bottom: 8px;
            border-left: 3px solid #2196F3;
        }

        .analysis-text.audio {
            border-left-color: #FF9800;
        }

        .analysis-text.subtitle {
            border-left-color: #2196F3;
        }

        .analysis-text.translated {
            border-left-color: #4CAF50;
        }

        .language-info {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.7);
            margin-bottom: 4px;
        }

        .report-header {
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(0, 0, 0, 0.7);
            border-radius: 8px;
            padding: 12px 16px;
            z-index: 10;
        }

        .report-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .report-meta {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.7);
        }

        .overlay {
            position: absolute;
            left: 0;
            right: 400px;
            z-index: 5;
            pointer-events: none;
        }

        .summary-overlay {
            top: 80px;
            text-align: center;
            padding: 8px 16px;
            background: rgba(0, 0, 0, 0.8);
            border-radius: 4px;
            font-size: 14px;
            margin: 0 20px;
        }

        .subtitle-overlay {
            bottom: 80px;
            text-align: center;
            padding: 8px 16px;
            background: rgba(0, 0, 0, 0.9);
            border-radius: 4px;
            font-size: 16px;
            font-weight: 600;
            margin: 0 20px;
        }

        .hidden {
            display: none !important;
        }
    """

def get_restart_video_js() -> str:
    """JavaScript for restart video report functionality"""
    return """
        class RestartVideoReport {
            constructor() {
                this.video = document.getElementById('restart-video');
                this.playButton = document.getElementById('play-button');
                this.timeDisplay = document.getElementById('time-display');
                this.progressBar = document.getElementById('progress-bar');
                this.progressFill = document.getElementById('progress-fill');
                
                this.analysisData = window.ANALYSIS_DATA || {};
                this.currentLanguages = {
                    summary: 'en',
                    subtitle: 'en',
                    audio: 'en'
                };
                
                this.init();
            }
            
            init() {
                this.setupVideoControls();
                this.setupAnalysisToggles();
                this.setupLanguageSelects();
                this.updateOverlays();
            }
            
            setupVideoControls() {
                this.playButton.addEventListener('click', () => {
                    if (this.video.paused) {
                        this.video.play();
                        this.playButton.textContent = '⏸';
                    } else {
                        this.video.pause();
                        this.playButton.textContent = '▶';
                    }
                });
                
                this.video.addEventListener('timeupdate', () => {
                    const current = this.video.currentTime;
                    const duration = this.video.duration || 0;
                    const progress = duration > 0 ? (current / duration) * 100 : 0;
                    
                    this.progressFill.style.width = progress + '%';
                    this.timeDisplay.textContent = this.formatTime(current) + ' / ' + this.formatTime(duration);
                    
                    this.updateOverlays();
                });
                
                this.progressBar.addEventListener('click', (e) => {
                    const rect = this.progressBar.getBoundingClientRect();
                    const pos = (e.clientX - rect.left) / rect.width;
                    this.video.currentTime = pos * this.video.duration;
                });
            }
            
            setupAnalysisToggles() {
                document.querySelectorAll('.section-header').forEach(header => {
                    header.addEventListener('click', () => {
                        const section = header.dataset.section;
                        const content = document.getElementById(section + '-content');
                        const icon = header.querySelector('.expand-icon');
                        const checkbox = header.querySelector('.checkbox');
                        
                        if (content.classList.contains('expanded')) {
                            content.classList.remove('expanded');
                            icon.classList.remove('expanded');
                            checkbox.classList.remove('checked');
                            this.hideOverlay(section);
                        } else {
                            content.classList.add('expanded');
                            icon.classList.add('expanded');
                            checkbox.classList.add('checked');
                            this.showOverlay(section);
                        }
                    });
                });
            }
            
            setupLanguageSelects() {
                document.querySelectorAll('.language-select').forEach(select => {
                    select.addEventListener('change', (e) => {
                        const section = e.target.dataset.section;
                        this.currentLanguages[section] = e.target.value;
                        this.updateAnalysisText(section);
                    });
                });
            }
            
            showOverlay(section) {
                const overlay = document.getElementById(section + '-overlay');
                if (overlay) {
                    overlay.classList.remove('hidden');
                }
            }
            
            hideOverlay(section) {
                const overlay = document.getElementById(section + '-overlay');
                if (overlay) {
                    overlay.classList.add('hidden');
                }
            }
            
            updateOverlays() {
                // Update summary overlay based on video time
                if (this.analysisData.video_analysis && this.analysisData.video_analysis.frame_descriptions) {
                    const currentTime = this.video.currentTime;
                    const frameIndex = Math.floor(currentTime);
                    const descriptions = this.analysisData.video_analysis.frame_descriptions;
                    
                    if (frameIndex < descriptions.length) {
                        const summaryOverlay = document.getElementById('summary-overlay');
                        if (summaryOverlay && !summaryOverlay.classList.contains('hidden')) {
                            summaryOverlay.textContent = descriptions[frameIndex];
                        }
                    }
                }
            }
            
            updateAnalysisText(section) {
                const data = this.analysisData[section + '_analysis'];
                if (!data) return;
                
                const originalElement = document.getElementById(section + '-original');
                const translatedElement = document.getElementById(section + '-translated');
                
                if (originalElement && data.extracted_text) {
                    originalElement.innerHTML = `
                        <div class="language-info">Original (${this.getLanguageName(data.detected_language)}, ${Math.round(data.confidence * 100)}% confidence):</div>
                        ${data.extracted_text || data.combined_transcript}
                    `;
                }
                
                if (translatedElement && this.currentLanguages[section] !== data.detected_language) {
                    translatedElement.innerHTML = `
                        <div class="language-info">Translated (${this.getLanguageName(this.currentLanguages[section])}):</div>
                        ${this.translateText(data.extracted_text || data.combined_transcript, this.currentLanguages[section])}
                    `;
                    translatedElement.classList.remove('hidden');
                } else if (translatedElement) {
                    translatedElement.classList.add('hidden');
                }
            }
            
            translateText(text, targetLang) {
                // Placeholder translation - in real implementation would use translation API
                return `[${targetLang.toUpperCase()}] ${text}`;
            }
            
            getLanguageName(code) {
                const names = {
                    'en': 'English',
                    'es': 'Spanish',
                    'fr': 'French',
                    'de': 'German',
                    'it': 'Italian',
                    'pt': 'Portuguese'
                };
                return names[code] || code.toUpperCase();
            }
            
            formatTime(seconds) {
                const mins = Math.floor(seconds / 60);
                const secs = Math.floor(seconds % 60);
                return `${mins}:${secs.toString().padStart(2, '0')}`;
            }
        }
        
        // Initialize when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {
            new RestartVideoReport();
        });
    """

def create_restart_video_template() -> str:
    """Create the complete HTML template for restart video reports"""
    css_content = get_restart_video_css()
    js_content = get_restart_video_js()
    
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restart Video Report - {device_name}</title>
    <style>
""" + css_content + """
    </style>
</head>
<body>
    <div class="video-container">
        <!-- Video Player Section -->
        <div class="video-player">
            <!-- Report Header -->
            <div class="report-header">
                <div class="report-title">Restart Video Analysis</div>
                <div class="report-meta">{{host_name}} • {{device_name}} • {{timestamp}}</div>
            </div>
            
            <!-- Video Element -->
            <video id="restart-video" class="video-element" preload="metadata">
                <source src="{{video_url}}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            
            <!-- Video Controls -->
            <div class="video-controls">
                <button id="play-button" class="play-button">▶</button>
                <div id="time-display" class="time-display">0:00 / 0:00</div>
                <div id="progress-bar" class="progress-bar">
                    <div id="progress-fill" class="progress-fill"></div>
                </div>
            </div>
            
            <!-- Video Summary Overlay -->
            <div id="summary-overlay" class="overlay summary-overlay hidden">
                Frame description will appear here
            </div>
            
            <!-- Subtitle Overlay -->
            <div id="subtitle-overlay" class="overlay subtitle-overlay hidden">
                Subtitle text will appear here
            </div>
        </div>
        
        <!-- Settings Panel -->
        <div class="settings-panel">
            <div class="settings-header">
                <div class="settings-title">Settings</div>
                <button class="close-button">✕</button>
            </div>
            
            <!-- Video Summary Section -->
            <div class="analysis-section">
                <div class="section-header" data-section="summary">
                    <div class="checkbox"></div>
                    <div class="section-title">Video Summary</div>
                    <select class="language-select" data-section="summary">
                        <option value="en">English</option>
                        <option value="es">Spanish</option>
                        <option value="fr">French</option>
                    </select>
                    <div class="expand-icon">▶</div>
                </div>
                <div id="summary-content" class="analysis-content">
                    <div class="analysis-text">{{video_summary}}</div>
                </div>
            </div>
            
            <!-- Subtitles Section -->
            <div class="analysis-section">
                <div class="section-header" data-section="subtitle">
                    <div class="checkbox"></div>
                    <div class="section-title">Subtitles</div>
                    <select class="language-select" data-section="subtitle">
                        <option value="en">English</option>
                        <option value="es">Spanish</option>
                        <option value="fr">French</option>
                    </select>
                    <div class="expand-icon">▶</div>
                </div>
                <div id="subtitle-content" class="analysis-content">
                    <div id="subtitle-original" class="analysis-text subtitle">{{subtitle_text}}</div>
                    <div id="subtitle-translated" class="analysis-text translated hidden"></div>
                </div>
            </div>
            
            <!-- Audio Transcript Section -->
            <div class="analysis-section">
                <div class="section-header" data-section="audio">
                    <div class="checkbox"></div>
                    <div class="section-title">Audio Transcript</div>
                    <select class="language-select" data-section="audio">
                        <option value="en">English</option>
                        <option value="es">Spanish</option>
                        <option value="fr">French</option>
                    </select>
                    <div class="expand-icon">▶</div>
                </div>
                <div id="audio-content" class="analysis-content">
                    <div id="audio-original" class="analysis-text audio">{{audio_transcript}}</div>
                    <div id="audio-translated" class="analysis-text translated hidden"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Analysis data for JavaScript
        window.ANALYSIS_DATA = {analysis_data_json};
    </script>
    <script>
""" + js_content + """
    </script>
</body>
</html>"""
