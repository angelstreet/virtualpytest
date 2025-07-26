#!/bin/bash

# VirtualPyTest - Host Environment Setup
# Configure the host system for capture and monitoring

echo "🔧 Setting up VirtualPyTest host environment..."

# Create required directories
echo "📁 Creating directories..."
sudo mkdir -p /var/www/html/stream/capture1/captures
sudo mkdir -p /var/www/html/stream/capture2/captures
sudo mkdir -p /var/www/html/stream/capture3/captures
sudo mkdir -p /var/www/html/stream/capture4/captures

# Set proper permissions
echo "🔐 Setting permissions..."
sudo chown -R $USER:$USER /var/www/html/stream/
sudo chmod -R 755 /var/www/html/stream/

# Check required packages
echo "📦 Checking system packages..."
packages=("ffmpeg" "imagemagick" "inotify-tools" "v4l-utils" "alsa-utils")
missing_packages=()

for package in "${packages[@]}"; do
    if ! dpkg -l | grep -q "^ii  $package "; then
        missing_packages+=("$package")
    fi
done

if [ ${#missing_packages[@]} -gt 0 ]; then
    echo "Installing missing packages: ${missing_packages[*]}"
    sudo apt update
    sudo apt install -y "${missing_packages[@]}"
else
    echo "✅ All required packages are installed"
fi

# Check video/audio devices
echo "🎥 Checking video devices..."
if ls /dev/video* &>/dev/null; then
    echo "✅ Video devices found:"
    ls -la /dev/video*
else
    echo "⚠️  No video devices found"
fi

echo "🔊 Checking audio devices..."
if arecord -l &>/dev/null; then
    echo "✅ Audio devices found:"
    arecord -l
else
    echo "⚠️  No audio devices found"
fi

# Add user to required groups
echo "👤 Adding user to required groups..."
sudo usermod -a -G video,audio,dialout $USER

# Create log rotation
echo "📜 Setting up log rotation..."
sudo tee /etc/logrotate.d/virtualpytest-host > /dev/null << 'LOGROTATE_EOF'
/tmp/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    copytruncate
}
LOGROTATE_EOF

echo "✅ Host environment setup completed!"
echo ""
echo "🔄 Please reboot or log out/in for group changes to take effect"
echo "🚀 Then run: ./manage_services.sh start" 