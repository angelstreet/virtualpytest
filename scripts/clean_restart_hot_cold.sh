#!/bin/bash
################################################################################
# Hot/Cold Architecture - Clean Restart Script
################################################################################
#
# This script performs a CLEAN RESTART with the new hot/cold architecture:
#   1. Stops all capture-related services
#   2. Deletes old capture folders
#   3. Recreates hot/cold folder structure with proper permissions
#   4. Restarts all services
#
# ⚠️  WARNING: This will DELETE ALL EXISTING CAPTURE DATA!
#
# Usage:
#   sudo bash scripts/clean_restart_hot_cold.sh
#
################################################################################

set -e  # Exit on any error

# Configuration
STREAM_BASE="/var/www/html/stream"
CAPTURE_FOLDERS=("capture1" "capture2" "capture3" "capture4")
WWW_USER="www-data"
WWW_GROUP="www-data"

# Services to manage
SERVICES=(
    "stream"
    "monitor"
    "transcript-stream"
    "hot_cold_archiver"
    "heatmap_processor"
)

echo "================================================================================
🔄 HOT/COLD ARCHITECTURE - CLEAN RESTART
================================================================================"
echo ""
echo "⚠️  WARNING: This will DELETE ALL EXISTING CAPTURE DATA!"
echo ""
echo "Services to stop:"
for service in "${SERVICES[@]}"; do
    echo "  - $service"
done
echo ""
echo "Folders to recreate:"
for folder in "${CAPTURE_FOLDERS[@]}"; do
    echo "  - $STREAM_BASE/$folder"
done
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Aborted by user"
    exit 1
fi

################################################################################
# Step 1: Stop all services
################################################################################

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "Step 1: Stopping services..."
echo "════════════════════════════════════════════════════════════════════════════"

for service in "${SERVICES[@]}"; do
    echo "🛑 Stopping $service..."
    if systemctl is-active --quiet "$service"; then
        systemctl stop "$service"
        echo "   ✅ Stopped"
    else
        echo "   ⏭️  Already stopped"
    fi
done

echo "✅ All services stopped"
sleep 2

################################################################################
# Step 2: Delete old capture folders
################################################################################

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "Step 2: Deleting old capture folders..."
echo "════════════════════════════════════════════════════════════════════════════"

for folder in "${CAPTURE_FOLDERS[@]}"; do
    folder_path="$STREAM_BASE/$folder"
    
    if [ -d "$folder_path" ]; then
        echo ""
        echo "🗑️  Deleting $folder_path..."
        
        # Use Python script for fast parallel deletion with progress tracking
        # Shows: progress bar, files/sec, ETA, percentage
        python3 "$(dirname "$0")/fast_delete_with_progress.py" "$folder_path"
        
        if [ $? -eq 0 ]; then
            echo "   ✅ Deletion complete"
        else
            echo "   ⚠️  Deletion had errors, attempting cleanup..."
            # Fallback: force remove any remaining files
            if [ -d "$folder_path" ]; then
                rm -rf "$folder_path" 2>/dev/null || true
            fi
        fi
    else
        echo "⏭️  $folder_path does not exist, skipping"
    fi
done

echo "✅ Old folders deleted"

################################################################################
# Step 3: Create hot/cold folder structure
################################################################################

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "Step 3: Creating hot/cold folder structure..."
echo "════════════════════════════════════════════════════════════════════════════"

for folder in "${CAPTURE_FOLDERS[@]}"; do
    folder_path="$STREAM_BASE/$folder"
    
    echo "📁 Creating $folder..."
    
    # Create root directories (hot storage)
    mkdir -p "$folder_path/segments"
    mkdir -p "$folder_path/captures"
    mkdir -p "$folder_path/thumbnails"
    mkdir -p "$folder_path/metadata"
    
    # Create 24 hour folders for each type (cold storage)
    for hour in {0..23}; do
        mkdir -p "$folder_path/segments/$hour"
        mkdir -p "$folder_path/captures/$hour"
        mkdir -p "$folder_path/thumbnails/$hour"
        mkdir -p "$folder_path/metadata/$hour"
    done
    
    # Set ownership to www-data
    chown -R "$WWW_USER:$WWW_GROUP" "$folder_path"
    
    # Set permissions (755 for directories, 644 for future files)
    chmod -R 755 "$folder_path"
    
    echo "   ✅ Created with hot/cold structure"
    echo "      Owner: $WWW_USER:$WWW_GROUP"
    echo "      Structure:"
    echo "        - segments/    : hot (10 files) + 0-23 hour folders"
    echo "        - captures/    : hot (100 files) + 0-23 hour folders"
    echo "        - thumbnails/  : hot (100 files) + 0-23 hour folders"
    echo "        - metadata/    : hot (100 files) + 0-23 hour folders"
done

echo "✅ Hot/cold folder structure created"

################################################################################
# Step 4: Verify structure
################################################################################

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "Step 4: Verifying structure..."
echo "════════════════════════════════════════════════════════════════════════════"

for folder in "${CAPTURE_FOLDERS[@]}"; do
    folder_path="$STREAM_BASE/$folder"
    echo "📊 $folder:"
    
    # Count directories
    total_dirs=$(find "$folder_path" -type d | wc -l)
    echo "   Total directories: $total_dirs (expected: 101)"
    echo "     - Root: 4 (segments, captures, thumbnails, metadata)"
    echo "     - Hour folders: 96 (24 folders × 4 types)"
    
    # Check ownership
    owner=$(stat -c '%U:%G' "$folder_path" 2>/dev/null || stat -f '%Su:%Sg' "$folder_path" 2>/dev/null)
    echo "   Owner: $owner"
    
    # Check permissions
    perms=$(stat -c '%a' "$folder_path" 2>/dev/null || stat -f '%A' "$folder_path" 2>/dev/null)
    echo "   Permissions: $perms"
done

echo "✅ Structure verified"

################################################################################
# Step 5: Restart services
################################################################################

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "Step 5: Restarting services..."
echo "════════════════════════════════════════════════════════════════════════════"

for service in "${SERVICES[@]}"; do
    echo "🚀 Starting $service..."
    systemctl start "$service"
    
    # Wait a moment for service to start
    sleep 1
    
    if systemctl is-active --quiet "$service"; then
        echo "   ✅ Running"
    else
        echo "   ⚠️  Failed to start - check 'systemctl status $service'"
    fi
done

echo "✅ All services restarted"

################################################################################
# Step 6: Final status check
################################################################################

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "Step 6: Final status check..."
echo "════════════════════════════════════════════════════════════════════════════"

for service in "${SERVICES[@]}"; do
    status=$(systemctl is-active "$service" 2>/dev/null || echo "unknown")
    
    if [ "$status" = "active" ]; then
        echo "✅ $service: $status"
    else
        echo "❌ $service: $status"
    fi
done

################################################################################
# Done!
################################################################################

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "🎉 HOT/COLD ARCHITECTURE CLEAN RESTART COMPLETE!"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "📋 What happened:"
echo "   ✅ Old capture folders deleted"
echo "   ✅ New hot/cold structure created"
echo "   ✅ Proper www-data ownership set"
echo "   ✅ All services restarted"
echo ""
echo "📁 New structure:"
echo "   segments/     : hot (10 files) + 0-23/ hour folders (24h retention)"
echo "   captures/     : hot (100 files) + 0-23/ hour folders (1h retention)"
echo "   thumbnails/   : hot (100 files) + 0-23/ hour folders (24h retention)"
echo "   metadata/     : hot (100 files) + 0-23/ hour folders (24h retention)"
echo ""
echo "🔍 Monitor services:"
echo "   systemctl status stream"
echo "   systemctl status monitor"
echo "   systemctl status hot_cold_archiver"
echo "   tail -f /tmp/ffmpeg_service.log"
echo "   tail -f /tmp/hot_cold_archiver.log"
echo ""
echo "✨ System ready! FFmpeg will start creating files in hot folders."
echo ""

