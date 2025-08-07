"""
Report Template JavaScript Functions

Contains all JavaScript functionality for the HTML validation reports.
"""

def get_report_javascript() -> str:
    """Get the complete JavaScript for the report template."""
    return """// Theme management system
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
        
        updateModalContent();
        
        const modal = document.getElementById('screenshot-modal');
        modal.classList.add('active');
    }} catch (e) {{
        console.error('Error opening screenshot modal:', e);
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

// HLS Video modal functions
function openHLSVideoModal(videoUrl, label) {{
    let videoModal = document.getElementById('hls-video-modal');
    if (!videoModal) {{
        videoModal = document.createElement('div');
        videoModal.id = 'hls-video-modal';
        videoModal.className = 'modal';
        videoModal.innerHTML = `
            <div class="modal-content video-modal-content">
                <div class="modal-header">
                    <h3 id="hls-video-modal-title">${{label}}</h3>
                    <button class="modal-close" onclick="closeHLSVideoModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <video id="hls-modal-video" controls style="width: 100%; max-width: 800px;">
                        Your browser does not support HLS video playback.
                    </video>
                </div>
            </div>
        `;
        document.body.appendChild(videoModal);
    }} else {{
        document.getElementById('hls-video-modal-title').textContent = label;
    }}
    
    // Setup HLS video playback
    const video = document.getElementById('hls-modal-video');
    
    // Clear any existing HLS instance
    if (window.currentHls) {{
        window.currentHls.destroy();
    }}
    
    if (Hls.isSupported()) {{
        const hls = new Hls({{
            debug: false,
            enableWorker: true,
            lowLatencyMode: false,
            backBufferLength: 90
        }});
        
        hls.loadSource(videoUrl);
        hls.attachMedia(video);
        
        hls.on(Hls.Events.MANIFEST_PARSED, function() {{
            video.play().catch(e => console.log('Autoplay prevented:', e));
        }});
        
        hls.on(Hls.Events.ERROR, function(event, data) {{
            console.error('HLS error:', data);
            if (data.fatal) {{
                switch(data.type) {{
                    case Hls.ErrorTypes.NETWORK_ERROR:
                        hls.startLoad();
                        break;
                    case Hls.ErrorTypes.MEDIA_ERROR:
                        hls.recoverMediaError();
                        break;
                    default:
                        hls.destroy();
                        break;
                }}
            }}
        }});
        
        window.currentHls = hls;
    }} else if (video.canPlayType('application/vnd.apple.mpegurl')) {{
        video.src = videoUrl;
        video.addEventListener('loadedmetadata', function() {{
            video.play().catch(e => console.log('Autoplay prevented:', e));
        }});
    }} else {{
        video.innerHTML = '<p style="color: red; text-align: center; padding: 20px;">HLS video playback is not supported in this browser.</p>';
    }}
    
    videoModal.classList.add('active');
}}

function closeHLSVideoModal() {{
    const videoModal = document.getElementById('hls-video-modal');
    if (videoModal) {{
        videoModal.classList.remove('active');
        const video = document.getElementById('hls-modal-video');
        if (video) {{
            video.pause();
        }}
        
        // Clean up HLS instance
        if (window.currentHls) {{
            window.currentHls.destroy();
            window.currentHls = null;
        }}
    }}
}}

// Verification image modal functions
function openVerificationImageModal(modalData) {{
    let verificationModal = document.getElementById('verification-image-modal');
    if (!verificationModal) {{
        verificationModal = document.createElement('div');
        verificationModal.id = 'verification-image-modal';
        verificationModal.className = 'modal';
        verificationModal.innerHTML = `
            <div class="modal-content verification-modal-content" style="width: 90%; max-width: 1200px;">
                <div class="modal-header">
                    <h3 id="verification-modal-title">Image Verification Comparison</h3>
                    <button class="modal-close" onclick="closeVerificationImageModal()">&times;</button>
                </div>
                <div class="modal-body" style="display: flex; flex-wrap: wrap; justify-content: center; gap: 20px;">
                    <div id="verification-images-container" style="display: flex; flex-wrap: wrap; justify-content: center; gap: 20px;"></div>
                </div>
            </div>
        `;
        document.body.appendChild(verificationModal);
    }}
    
    // Populate the modal with images
    const imagesContainer = document.getElementById('verification-images-container');
    imagesContainer.innerHTML = '';
    
    modalData.images.forEach(image => {{
        const imageDiv = document.createElement('div');
        imageDiv.style.textAlign = 'center';
        imageDiv.style.maxWidth = '32%';
        imageDiv.style.minWidth = '300px';
        
        const title = document.createElement('h4');
        title.textContent = image.label;
        title.style.marginBottom = '10px';
        title.style.color = 'var(--text-primary)';
        
        const img = document.createElement('img');
        img.src = image.url;
        img.style.maxWidth = '100%';
        img.style.maxHeight = '500px';
        img.style.objectFit = 'contain';
        img.style.border = '1px solid var(--border-color)';
        img.style.borderRadius = '4px';
        img.style.cursor = 'pointer';
        img.title = 'Click to open in new tab';
        img.onclick = () => window.open(image.url, '_blank');
        
        imageDiv.appendChild(title);
        imageDiv.appendChild(img);
        imagesContainer.appendChild(imageDiv);
    }});
    
    // Update modal title
    document.getElementById('verification-modal-title').textContent = modalData.title || 'Image Verification Comparison';
    
    // Show the modal
    verificationModal.classList.add('active');
}}

function closeVerificationImageModal() {{
    const verificationModal = document.getElementById('verification-image-modal');
    if (verificationModal) {{
        verificationModal.classList.remove('active');
    }}
}}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {{
    const modal = document.getElementById('screenshot-modal');
    if (modal) {{
        modal.addEventListener('click', function(e) {{
            if (e.target === modal) {{
                closeScreenshot();
            }}
        }});
    }}
    
    // Modal click-outside handlers
    document.addEventListener('click', function(e) {{
        const hlsModal = document.getElementById('hls-video-modal');
        if (hlsModal && e.target === hlsModal) {{
            closeHLSVideoModal();
        }}
        
        const verificationModal = document.getElementById('verification-image-modal');
        if (verificationModal && e.target === verificationModal) {{
            closeVerificationImageModal();
        }}
    }});
    
    // Keyboard navigation
    document.addEventListener('keydown', function(e) {{
        const hlsModal = document.getElementById('hls-video-modal');
        const verificationModal = document.getElementById('verification-image-modal');
        
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
        }} else if (hlsModal && hlsModal.classList.contains('active')) {{
            if (e.key === 'Escape') {{
                e.preventDefault();
                closeHLSVideoModal();
            }}
        }} else if (verificationModal && verificationModal.classList.contains('active')) {{
            if (e.key === 'Escape') {{
                e.preventDefault();
                closeVerificationImageModal();
            }}
        }}
    }});
}});"""