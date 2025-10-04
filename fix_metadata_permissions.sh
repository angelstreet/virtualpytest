#!/bin/bash
# Fix metadata directory permissions on all capture devices
# Run this on each Raspberry Pi to fix the permission issue

echo "============================================"
echo "Fixing Metadata Directory Permissions"
echo "============================================"
echo ""

FIXED_COUNT=0

for capture_dir in /var/www/html/stream/capture*; do
    if [ ! -d "$capture_dir" ]; then
        continue
    fi
    
    device=$(basename "$capture_dir")
    echo "Processing $device..."
    
    # Fix hot metadata (RAM storage)
    if [ -d "$capture_dir/hot/metadata" ]; then
        echo "  Fixing hot metadata permissions..."
        sudo chmod 777 "$capture_dir/hot/metadata"
        echo "  ✓ $capture_dir/hot/metadata → 777"
        FIXED_COUNT=$((FIXED_COUNT + 1))
    fi
    
    # Fix cold metadata (SD card storage)
    if [ ! -d "$capture_dir/metadata" ]; then
        echo "  Creating cold metadata directory..."
        sudo mkdir -p "$capture_dir/metadata"
        sudo chown www-data:www-data "$capture_dir/metadata"
    fi
    sudo chmod 777 "$capture_dir/metadata"
    echo "  ✓ $capture_dir/metadata → 777"
    FIXED_COUNT=$((FIXED_COUNT + 1))
    
    echo ""
done

echo "============================================"
echo "✅ Fixed $FIXED_COUNT metadata directories"
echo "============================================"
echo ""

# Show current permissions
echo "Verification (hot metadata):"
ls -ld /var/www/html/stream/capture*/hot/metadata 2>/dev/null | awk '{print $1, $9}'
echo ""
echo "Verification (cold metadata):"
ls -ld /var/www/html/stream/capture*/metadata 2>/dev/null | grep -v "/hot/" | awk '{print $1, $9}'
echo ""
echo "✅ All metadata directories should show 'drwxrwxrwx'"

