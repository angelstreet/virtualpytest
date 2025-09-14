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

        .analysis-panel {
            width: 400px;
            background: rgba(0, 0, 0, 0.95);
            border-left: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            overflow-y: auto;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .full-analysis-section {
            margin-bottom: 24px;
            padding-bottom: 20px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
        }

        .analysis-header {
            font-size: 14px;
            font-weight: 600;
            color: #4CAF50;
            margin-bottom: 8px;
        }

        .analysis-content {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            padding: 12px;
            font-size: 12px;
            line-height: 1.5;
            color: rgba(255, 255, 255, 0.9);
            max-height: 120px;
            overflow-y: auto;
        }

        .frame-by-frame-section {
            margin-top: 20px;
        }

        .frame-by-frame-title {
            font-size: 16px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 16px;
            text-align: center;
        }

        .frame-item {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 12px;
            border-left: 3px solid rgba(255, 255, 255, 0.3);
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .frame-item.active {
            background: rgba(76, 175, 80, 0.15);
            border-left-color: #4CAF50;
            box-shadow: 0 2px 8px rgba(76, 175, 80, 0.2);
        }

        .frame-header {
            font-size: 13px;
            font-weight: 600;
            color: #4CAF50;
            margin-bottom: 8px;
        }

        .frame-content {
            font-size: 11px;
            line-height: 1.4;
        }

        .frame-subtitles {
            color: #2196F3;
            margin-bottom: 6px;
            font-style: italic;
        }

        .frame-summary {
            color: rgba(255, 255, 255, 0.85);
        }

        .no-content {
            color: rgba(255, 255, 255, 0.5);
            font-style: italic;
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
                this.currentFrameIndex = 0;
                
                this.init();
            }
            
            init() {
                console.log('RestartVideoReport initialized');
                console.log('Analysis data:', this.analysisData);
                this.setupVideoControls();
                this.setupFrameAnalysis();
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
                    
                    // Update active frame based on current time
                    const newFrameIndex = Math.floor(current);
                    if (newFrameIndex !== this.currentFrameIndex) {
                        this.currentFrameIndex = newFrameIndex;
                        this.updateActiveFrame();
                    }
                });
                
                this.progressBar.addEventListener('click', (e) => {
                    const rect = this.progressBar.getBoundingClientRect();
                    const pos = (e.clientX - rect.left) / rect.width;
                    this.video.currentTime = pos * this.video.duration;
                });
            }
            
            setupFrameAnalysis() {
                const frameContainer = document.getElementById('frame-analysis-container');
                if (!frameContainer) return;
                
                // Get analysis data
                const frameDescriptions = this.analysisData.video_analysis?.frame_descriptions || [];
                const subtitleAnalysis = this.analysisData.subtitle_analysis || {};
                
                if (frameDescriptions.length === 0) {
                    frameContainer.innerHTML = '<div class="frame-item"><div class="no-content">No frame analysis available</div></div>';
                    return;
                }
                
                // Create comprehensive frame items
                frameDescriptions.forEach((description, index) => {
                    const frameItem = document.createElement('div');
                    frameItem.className = 'frame-item';
                    frameItem.dataset.frameIndex = index;
                    
                    // Get subtitle for this frame (if available)
                    const frameSubtitles = this.getFrameSubtitles(index, subtitleAnalysis);
                    
                    frameItem.innerHTML = `
                        <div class="frame-header">Frame ${index + 1}:</div>
                        <div class="frame-content">
                            <div class="frame-subtitles">
                                Subtitles: ${frameSubtitles || '<span class="no-content">None detected</span>'}
                            </div>
                            <div class="frame-summary">
                                Summary: ${description}
                            </div>
                        </div>
                    `;
                    
                    // Add click handler to seek to frame
                    frameItem.addEventListener('click', () => {
                        this.seekToFrame(index);
                    });
                    
                    frameContainer.appendChild(frameItem);
                });
                
                // Set initial active frame
                this.updateActiveFrame();
            }
            
            getFrameSubtitles(frameIndex, subtitleAnalysis) {
                // For now, return the general subtitle text if available
                // In a more advanced implementation, this could be frame-specific
                if (subtitleAnalysis.extracted_text && subtitleAnalysis.extracted_text.trim()) {
                    return subtitleAnalysis.extracted_text;
                }
                return null;
            }
            
            seekToFrame(frameIndex) {
                const targetTime = frameIndex;
                if (this.video.duration && targetTime <= this.video.duration) {
                    this.video.currentTime = targetTime;
                    this.currentFrameIndex = frameIndex;
                    this.updateActiveFrame();
                }
            }
            
            updateActiveFrame() {
                // Remove active class from all frames
                document.querySelectorAll('.frame-item').forEach(item => {
                    item.classList.remove('active');
                });
                
                // Add active class to current frame
                const currentFrame = document.querySelector(`[data-frame-index="${this.currentFrameIndex}"]`);
                if (currentFrame) {
                    currentFrame.classList.add('active');
                    
                    // Scroll to active frame
                    const container = document.getElementById('frame-analysis-container');
                    if (container) {
                        currentFrame.scrollIntoView({ 
                            behavior: 'smooth', 
                            block: 'center',
                            inline: 'nearest'
                        });
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
        
        <!-- Analysis Panel -->
        <div class="analysis-panel">
            <!-- Full Video Analysis Section -->
            <div class="full-analysis-section">
                <div class="analysis-header">Video Summary (EN):</div>
                <div class="analysis-content">{video_summary}</div>
            </div>
            
            <div class="full-analysis-section">
                <div class="analysis-header">Audio Transcript (EN):</div>
                <div class="analysis-content">{audio_transcript}</div>
            </div>
            
            <!-- Frame-by-Frame Analysis Section -->
            <div class="frame-by-frame-section">
                <div class="frame-by-frame-title">Frame Analysis</div>
                <div id="frame-analysis-container">
                    <!-- Frame items will be populated by JavaScript -->
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