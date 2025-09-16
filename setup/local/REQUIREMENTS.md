# System Requirements for VirtualPyTest

This document lists all system-level dependencies required for VirtualPyTest on **Ubuntu/Linux** that are **NOT** installed by the existing `install_*.sh` scripts.

## 🖥️ **Operating System**

- **Ubuntu 18.04+** (Recommended)
- **Debian 10+** (Compatible)
- **Other Linux** (May work with package name adjustments)

## 📋 **System Dependencies**

### **Already Installed by VirtualPyTest Scripts:**
- ✅ **Python 3.8+** - Installed by `install_shared.sh`
- ✅ **Node.js 18+** - Installed by `install_frontend.sh` 
- ✅ **PostgreSQL** - Installed by `install_db.sh` (with complete VirtualPyTest schema)
- ✅ **Grafana** - Installed by `install_grafana.sh`

### **Required System Packages (NOT installed by scripts):**

#### **🔧 Build Tools & Development**
```bash
sudo apt-get install -y build-essential git curl wget software-properties-common
```

#### **🎥 Video & Audio Processing**
```bash
sudo apt-get install -y ffmpeg imagemagick
```

#### **🔤 OCR & Text Recognition**
```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-fra tesseract-ocr-deu tesseract-ocr-ita
```

#### **🖥️ VNC & Remote Desktop (for backend_host)**
```bash
# Clean installation - removes conflicting VNC packages first
sudo apt-get remove -y realvnc-vnc-server realvnc-vnc-viewer vnc4server tightvncserver 2>/dev/null || true
sudo apt-get install -y tigervnc-standalone-server xvfb fluxbox novnc websockify
```

#### **🌐 Web Browser (for browser automation)**
```bash
sudo apt-get install -y epiphany-browser chromium-browser
```

#### **📁 File System Monitoring**
```bash
sudo apt-get install -y inotify-tools
```

#### **🔗 Network & System Tools**
```bash
sudo apt-get install -y lsof net-tools psmisc
```

## 🎯 **Hardware-Specific Requirements**

### **For Video Capture (HDMI devices):**
- **Video4Linux drivers** (`/dev/video*` devices)
- **ALSA audio drivers** (`plughw:*` devices)
- **USB capture cards** (compatible with V4L2)

### **For Mobile Device Testing:**
- **ADB (Android Debug Bridge)** - For Android devices
- **USB drivers** - For device connectivity
- **Appium Server** - Installed via Python requirements

## 🚀 **Quick Install (One Command)**

```bash
# Clean VNC installation (remove conflicts first)
sudo apt-get remove -y realvnc-vnc-server realvnc-vnc-viewer vnc4server tightvncserver 2>/dev/null || true

# Install all requirements
sudo apt-get update && sudo apt-get install -y \
    build-essential git curl wget software-properties-common \
    ffmpeg imagemagick \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-fra tesseract-ocr-deu tesseract-ocr-ita \
    tigervnc-standalone-server xvfb fluxbox novnc websockify \
    epiphany-browser chromium-browser \
    inotify-tools lsof net-tools psmisc
```

## 🔍 **Verification**

After installation, verify key components:
```bash
# Check video processing
ffmpeg -version

# Check OCR
tesseract --version

# Check VNC (should show TigerVNC)
vncserver -help | head -1

# Check file monitoring
which inotifywait
```

## 💡 **Notes**

- **Optional Components**: Video capture and VNC are only needed for hardware testing
- **Browser Dependencies**: Web browsers are only needed for browser automation tests
- **Package Search**: Use `apt-cache search <package>` to find alternatives
