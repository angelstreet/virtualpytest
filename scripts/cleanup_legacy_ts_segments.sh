#!/bin/bash
set -e

STREAM_BASE="/var/www/html/stream"

echo "Deleting legacy TS segments from cold storage..."

for capture_dir in "$STREAM_BASE"/capture*; do
    [[ -d "$capture_dir" ]] || continue
    
    echo "Processing $(basename "$capture_dir")..."
    
    find "$capture_dir/segments" -maxdepth 2 -name "*.ts" -type f -delete
    
    echo "✓ Done"
done

echo "Cleanup complete"
