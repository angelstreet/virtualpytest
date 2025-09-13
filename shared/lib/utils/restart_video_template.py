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
            margin-bottom: 24px;
        }

        .settings-title {
            font-size: 18px;
            font-weight: 600;
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

        .frame-analysis-title {
            font-size: 12px;
            font-weight: 600;
            color: #fff;
            margin: 16px 0 8px 0;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding-top: 16px;
        }

        .frame-analysis-container {
            max-height: 300px;
            overflow-y: auto;
        }

        .frame-item {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 6px;
            font-size: 11px;
            line-height: 1.4;
            border-left: 3px solid #4CAF50;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        .frame-item:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        .frame-item.active {
            background: rgba(76, 175, 80, 0.2);
            border-left-color: #4CAF50;
        }

        .frame-number {
            font-weight: 600;
            color: #4CAF50;
            margin-bottom: 4px;
        }

        .frame-description {
            color: rgba(255, 255, 255, 0.9);
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

        .summary-area {
            position: absolute;
            top: 80px;
            left: 20px;
            right: 420px;
            background: rgba(0, 0, 0, 0.8);
            border-radius: 8px;
            padding: 16px;
            z-index: 10;
            max-height: 120px;
            overflow-y: auto;
        }

        .summary-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #fff;
        }

        .summary-content {
            font-size: 12px;
            line-height: 1.4;
            color: rgba(255, 255, 255, 0.9);
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
                
                this.init();
            }
            
            init() {
                console.log('RestartVideoReport initialized');
                console.log('Analysis data:', this.analysisData);
                this.setupVideoControls();
                this.setupAnalysisToggles();
                this.setupFrameAnalysis();
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
                    
                    // Update active frame based on current time
                    const currentFrameIndex = Math.floor(current);
                    this.updateActiveFrame(currentFrameIndex);
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
            
            setupFrameAnalysis() {
                const frameContainer = document.getElementById('frame-analysis-container');
                if (!frameContainer) return;
                
                // Get frame descriptions from analysis data
                const frameDescriptions = this.analysisData.video_analysis?.frame_descriptions || [];
                
                if (frameDescriptions.length === 0) {
                    frameContainer.innerHTML = '<div class="frame-item">No frame analysis available</div>';
                    return;
                }
                
                // Create frame items
                frameDescriptions.forEach((description, index) => {
                    const frameItem = document.createElement('div');
                    frameItem.className = 'frame-item';
                    frameItem.dataset.frameIndex = index;
                    
                    frameItem.innerHTML = `
                        <div class="frame-number">Frame ${index + 1}:</div>
                        <div class="frame-description">${description}</div>
                    `;
                    
                    // Add click handler to seek to frame
                    frameItem.addEventListener('click', () => {
                        this.seekToFrame(index);
                        this.updateActiveFrame(index);
                    });
                    
                    frameContainer.appendChild(frameItem);
                });
            }
            
            seekToFrame(frameIndex) {
                // Assuming 1 second per frame for simplicity
                // In real implementation, this would use actual frame timing
                const targetTime = frameIndex;
                if (this.video.duration && targetTime <= this.video.duration) {
                    this.video.currentTime = targetTime;
                }
            }
            
            updateActiveFrame(currentFrameIndex) {
                // Remove active class from all frames
                document.querySelectorAll('.frame-item').forEach(item => {
                    item.classList.remove('active');
                });
                
                // Add active class to current frame
                const currentFrame = document.querySelector(`[data-frame-index="${currentFrameIndex}"]`);
                if (currentFrame) {
                    currentFrame.classList.add('active');
                    
                    // Scroll to active frame if needed
                    const container = document.getElementById('frame-analysis-container');
                    if (container) {
                        const containerRect = container.getBoundingClientRect();
                        const frameRect = currentFrame.getBoundingClientRect();
                        
                        if (frameRect.top < containerRect.top || frameRect.bottom > containerRect.bottom) {
                            currentFrame.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                    }
                }
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
                
                // Update subtitle overlay
                if (this.analysisData.subtitle_analysis && this.analysisData.subtitle_analysis.extracted_text) {
                    const subtitleOverlay = document.getElementById('subtitle-overlay');
                    if (subtitleOverlay && !subtitleOverlay.classList.contains('hidden')) {
                        subtitleOverlay.textContent = this.analysisData.subtitle_analysis.extracted_text;
                    }
                }
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
    
    # Escape braces in CSS and JS content to avoid format() conflicts
    css_content = get_restart_video_css().replace('{', '{{').replace('}', '}}')
    js_content = get_restart_video_js().replace('{', '{{').replace('}', '}}')
    
    # Build the template using string replacement instead of format() to avoid brace conflicts
    template_parts = []
    
    template_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restart Video Report - {device_name}</title>
    <style>""")
    
    template_parts.append(css_content)
    
    template_parts.append("""    </style>
</head>
<body>
    <div class="video-container">
        <!-- Video Player Section -->
        <div class="video-player">
            <!-- Report Header -->
            <div class="report-header">
                <div class="report-title">Restart Video Analysis</div>
                <div class="report-meta">{host_name} - {device_name} {timestamp}</div>
            </div>
            
            <!-- Summary Area -->
            <div class="summary-area">
                <div class="summary-title">Video Summary</div>
                <div class="summary-content">{video_summary}</div>
            </div>
            
            <!-- Video Element -->
            <video id="restart-video" class="video-element" preload="metadata">
                <source src="{video_url}" type="video/mp4">
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
            </div>
            
            <!-- Video Summary Section -->
            <div class="analysis-section">
                <div class="section-header" data-section="summary">
                    <div class="checkbox"></div>
                    <div class="section-title">Video Summary</div>
                    <div class="expand-icon">▶</div>
                </div>
                <div id="summary-content" class="analysis-content">
                    <div class="analysis-text">{video_summary}</div>
                    <div class="frame-analysis-title">Frame Analysis:</div>
                    <div id="frame-analysis-container" class="frame-analysis-container">
                        <!-- Frame descriptions will be populated by JavaScript -->
                    </div>
                </div>
            </div>
            
            <!-- Subtitles Section -->
            <div class="analysis-section">
                <div class="section-header" data-section="subtitle">
                    <div class="checkbox"></div>
                    <div class="section-title">Subtitles</div>
                    <div class="expand-icon">▶</div>
                </div>
                <div id="subtitle-content" class="analysis-content">
                    <div id="subtitle-original" class="analysis-text subtitle">{subtitle_text}</div>
                </div>
            </div>
            
            <!-- Audio Transcript Section -->
            <div class="analysis-section">
                <div class="section-header" data-section="audio">
                    <div class="checkbox"></div>
                    <div class="section-title">Audio Transcript</div>
                    <div class="expand-icon">▶</div>
                </div>
                <div id="audio-content" class="analysis-content">
                    <div id="audio-original" class="analysis-text audio">{audio_transcript}</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Analysis data for JavaScript
        window.ANALYSIS_DATA = {analysis_data_json};
    </script>
    <script>""")
    
    template_parts.append(js_content)
    
    template_parts.append("""    </script>
</body>
</html>""")
    
    return ''.join(template_parts)
