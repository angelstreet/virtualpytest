"""
Restart Video Report Template - Fixed Version

The key fix is in the getFrameSubtitles() JavaScript function which now properly
extracts frame-specific subtitle data instead of returning the same text for all frames.
"""

def create_restart_video_template() -> str:
    """Create the complete HTML template for restart video reports"""
    
    # Use string replacement instead of .format() to avoid CSS brace conflicts
    template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restart Video Report - {device_name}</title>
    <style>
        * {{{{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}}}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #000;
            color: #fff;
            overflow: hidden;
        }}

        .video-container {{
            position: relative;
            width: 100vw;
            height: 100vh;
            display: flex;
        }}

        .video-player {{
            flex: 1;
            position: relative;
            background: #000;
        }}

        .video-element {{
            width: 100%;
            height: 100%;
            object-fit: contain;
        }}

        .video-controls {{
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
        }}

        .play-button {{
            background: none;
            border: none;
            color: #fff;
            font-size: 18px;
            cursor: pointer;
            padding: 8px;
            border-radius: 4px;
        }}

        .play-button:hover {{
            background: rgba(255, 255, 255, 0.1);
        }}

        .time-display {{
            color: #fff;
            font-size: 14px;
            min-width: 80px;
        }}

        .progress-bar {{
            flex: 1;
            height: 4px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 2px;
            cursor: pointer;
            position: relative;
        }}

        .progress-fill {{
            height: 100%;
            background: #fff;
            border-radius: 2px;
            width: 0%;
            transition: width 0.1s;
        }}

        .analysis-panel {{
            width: 400px;
            background: rgba(0, 0, 0, 0.95);
            border-left: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            overflow-y: auto;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}

        .collapsible-section {{
            margin-bottom: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.03);
        }}

        .section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            cursor: pointer;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            transition: background-color 0.2s;
        }}

        .section-header:hover {{
            background: rgba(255, 255, 255, 0.05);
        }}

        .section-title {{
            font-size: 13px;
            font-weight: 600;
            color: #4CAF50;
        }}

        .collapse-icon {{
            font-size: 12px;
            color: rgba(255, 255, 255, 0.6);
            transition: transform 0.2s;
        }}

        .collapse-icon.collapsed {{
            transform: rotate(-90deg);
        }}

        .section-content {{
            padding: 10px 12px;
            font-size: 11px;
            line-height: 1.4;
            color: rgba(255, 255, 255, 0.9);
            max-height: 100px;
            overflow-y: auto;
            transition: all 0.3s ease;
        }}

        .section-content.collapsed {{
            display: none;
        }}

        .frame-item {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 8px;
            border-left: 2px solid rgba(255, 255, 255, 0.3);
            transition: all 0.3s ease;
            cursor: pointer;
        }}

        .frame-item.active {{
            background: rgba(76, 175, 80, 0.15);
            border-left-color: #4CAF50;
            box-shadow: 0 1px 4px rgba(76, 175, 80, 0.2);
        }}

        .frame-header {{
            font-size: 11px;
            font-weight: 600;
            color: #4CAF50;
            margin-bottom: 4px;
        }}

        .frame-content {{
            font-size: 10px;
            line-height: 1.3;
        }}

        .frame-subtitles {{
            color: #2196F3;
            margin-bottom: 3px;
            font-style: italic;
        }}

        .frame-summary {{
            color: rgba(255, 255, 255, 0.85);
        }}

        .no-content {{
            color: rgba(255, 255, 255, 0.5);
            font-style: italic;
        }}

        .report-header {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(0, 0, 0, 0.7);
            border-radius: 8px;
            padding: 12px 16px;
            z-index: 10;
        }}

        .report-title {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }}

        .report-meta {{
            font-size: 12px;
            color: rgba(255, 255, 255, 0.7);
        }}

        .hidden {{
            display: none !important;
        }}
    </style>
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
        </div>
        
        <!-- Analysis Panel -->
        <div class="analysis-panel">
            <!-- Video Summary Section -->
            <div class="collapsible-section">
                <div class="section-header" onclick="toggleSection('video-summary')">
                    <div class="section-title">Video Summary (EN)</div>
                    <div class="collapse-icon">▼</div>
                </div>
                <div id="video-summary" class="section-content">
                    {video_summary}
                </div>
            </div>
            
            <!-- Audio Transcript Section -->
            <div id="audio-section" class="collapsible-section" style="display: none;">
                <div class="section-header" onclick="toggleSection('audio-transcript')">
                    <div id="audio-title" class="section-title">Audio Transcript</div>
                    <div class="collapse-icon">▼</div>
                </div>
                <div id="audio-transcript" class="section-content">
                    {audio_transcript}
                </div>
            </div>
            
            <!-- Frame Analysis Section -->
            <div class="collapsible-section">
                <div class="section-header" onclick="toggleSection('frame-analysis')">
                    <div class="section-title">Frame Analysis</div>
                    <div class="collapse-icon">▼</div>
                </div>
                <div id="frame-analysis" class="section-content">
                    <div id="frame-analysis-container">
                        <!-- Frame items will be populated by JavaScript -->
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Analysis data for JavaScript
        window.ANALYSIS_DATA = {analysis_data_json};
    </script>
    <script>
        class RestartVideoReport {{
            constructor() {{
                this.video = document.getElementById('restart-video');
                this.playButton = document.getElementById('play-button');
                this.timeDisplay = document.getElementById('time-display');
                this.progressBar = document.getElementById('progress-bar');
                this.progressFill = document.getElementById('progress-fill');
                
                this.analysisData = window.ANALYSIS_DATA || {{}};
                this.currentFrameIndex = 0;
                
                this.init();
            }}
            
            init() {{
                console.log('RestartVideoReport initialized');
                console.log('Analysis data:', this.analysisData);
                this.setupVideoControls();
                this.setupAudioSection();
                this.setupFrameAnalysis();
            }}
            
            setupAudioSection() {{
                const audioSection = document.getElementById('audio-section');
                const audioTitle = document.getElementById('audio-title');
                
                // Use the EXACT same data structure as frontend: analysisResults.audio?.combined_transcript
                const audioTranscript = this.analysisData.audio_analysis?.combined_transcript;
                
                if (audioTranscript && audioTranscript.trim()) {{
                    // Show section with language if transcript exists
                    const language = this.analysisData.audio_analysis?.detected_language || 'EN';
                    audioTitle.textContent = `Audio Transcript (${{language.toUpperCase()}})`;
                    audioSection.style.display = 'block';
                }} else {{
                    // Hide section if no transcript
                    audioSection.style.display = 'none';
                }}
            }}
            
            setupVideoControls() {{
                this.playButton.addEventListener('click', () => {{
                    if (this.video.paused) {{
                        this.video.play();
                        this.playButton.textContent = '⏸';
                    }} else {{
                        this.video.pause();
                        this.playButton.textContent = '▶';
                    }}
                }});
                
                this.video.addEventListener('timeupdate', () => {{
                    const current = this.video.currentTime;
                    const duration = this.video.duration || 0;
                    const progress = duration > 0 ? (current / duration) * 100 : 0;
                    
                    this.progressFill.style.width = progress + '%';
                    this.timeDisplay.textContent = this.formatTime(current) + ' / ' + this.formatTime(duration);
                    
                    // Update active frame based on current time
                    const newFrameIndex = Math.floor(current);
                    if (newFrameIndex !== this.currentFrameIndex) {{
                        this.currentFrameIndex = newFrameIndex;
                        this.updateActiveFrame();
                    }}
                }});
                
                this.progressBar.addEventListener('click', (e) => {{
                    const rect = this.progressBar.getBoundingClientRect();
                    const pos = (e.clientX - rect.left) / rect.width;
                    this.video.currentTime = pos * this.video.duration;
                }});
            }}
            
            setupFrameAnalysis() {{
                const frameContainer = document.getElementById('frame-analysis-container');
                if (!frameContainer) return;
                
                // Get analysis data
                const frameDescriptions = this.analysisData.video_analysis?.frame_descriptions || [];
                const subtitleAnalysis = this.analysisData.subtitle_analysis || {{}};
                
                if (frameDescriptions.length === 0) {{
                    frameContainer.innerHTML = '<div class="frame-item"><div class="no-content">No frame analysis available</div></div>';
                    return;
                }}
                
                // Create comprehensive frame items
                frameDescriptions.forEach((description, index) => {{
                    const frameItem = document.createElement('div');
                    frameItem.className = 'frame-item';
                    frameItem.dataset.frameIndex = index;
                    
                    // Get subtitle for this frame (FIXED VERSION)
                    const frameSubtitles = this.getFrameSubtitles(index, subtitleAnalysis);
                    
                    frameItem.innerHTML = `
                        <div class="frame-header">Frame ${{index + 1}}:</div>
                        <div class="frame-content">
                            <div class="frame-subtitles">
                                Subtitles: ${{frameSubtitles || '<span class="no-content">None detected</span>'}}
                            </div>
                            <div class="frame-summary">
                                Summary: ${description}
                            </div>
                        </div>
                    `;
                    
                    // Add click handler to seek to frame
                    frameItem.addEventListener('click', () => {{
                        this.seekToFrame(index);
                    }});
                    
                    frameContainer.appendChild(frameItem);
                }});
                
                // Set initial active frame
                this.updateActiveFrame();
            }}
            
            getFrameSubtitles(frameIndex, subtitleAnalysis) {{
                // FIXED: Extract frame-specific subtitle from frame_subtitles array
                if (subtitleAnalysis.frame_subtitles && subtitleAnalysis.frame_subtitles.length > 0) {{
                    // Look for the specific frame in the frame_subtitles array
                    const frameSubtitle = subtitleAnalysis.frame_subtitles[frameIndex];
                    
                    if (frameSubtitle) {{
                        // Extract text after "Frame X: " prefix
                        const match = frameSubtitle.match(/^Frame \\d+:\\s*(.+)$/);
                        if (match && match[1] && match[1] !== 'No subtitles detected') {{
                            return match[1];
                        }}
                    }}
                }}
                
                // Fallback: if no frame-specific data, return null
                return null;
            }}
            
            seekToFrame(frameIndex) {{
                const targetTime = frameIndex;
                if (this.video.duration && targetTime <= this.video.duration) {{
                    this.video.currentTime = targetTime;
                    this.currentFrameIndex = frameIndex;
                    this.updateActiveFrame();
                }}
            }}
            
            updateActiveFrame() {{
                // Remove active class from all frames
                document.querySelectorAll('.frame-item').forEach(item => {{
                    item.classList.remove('active');
                }});
                
                // Add active class to current frame
                const currentFrame = document.querySelector(`[data-frame-index="${{this.currentFrameIndex}}"]`);
                if (currentFrame) {{
                    currentFrame.classList.add('active');
                    
                    // Scroll to active frame
                    const container = document.getElementById('frame-analysis-container');
                    if (container) {{
                        currentFrame.scrollIntoView({{ 
                            behavior: 'smooth', 
                            block: 'center',
                            inline: 'nearest'
                        }});
                    }}
                }}
            }}
            
            formatTime(seconds) {{
                const mins = Math.floor(seconds / 60);
                const secs = Math.floor(seconds % 60);
                return `${mins}:${{secs.toString().padStart(2, '0')}}`;
            }}
        }}
        
        // Global toggle function for collapsible sections
        function toggleSection(sectionId) {{
            const content = document.getElementById(sectionId);
            const header = content.previousElementSibling;
            const icon = header.querySelector('.collapse-icon');
            
            if (content.classList.contains('collapsed')) {{
                content.classList.remove('collapsed');
                icon.classList.remove('collapsed');
                icon.textContent = '▼';
            }} else {{
                content.classList.add('collapsed');
                icon.classList.add('collapsed');
                icon.textContent = '▶';
            }}
        }}
        
        // Initialize when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {{
            new RestartVideoReport();
        }});
    </script>
</body>
</html>"""
    
    return template
