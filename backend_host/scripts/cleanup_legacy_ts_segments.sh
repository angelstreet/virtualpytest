#!/bin/bash

set -e

STREAM_BASE="/var/www/html/stream"
DRY_RUN=false

if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 DRY RUN MODE - No files will be deleted"
fi

echo "🧹 Cleaning up legacy TS segments from cold storage"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

total_deleted=0
total_size=0

for capture_dir in "$STREAM_BASE"/capture*; do
    if [[ ! -d "$capture_dir" ]]; then
        continue
    fi
    
    capture_name=$(basename "$capture_dir")
    echo "📁 Processing $capture_name..."
    
    # Delete TS segments from hour folders (0-23)
    for hour_dir in "$capture_dir"/segments/{0..23}; do
        if [[ ! -d "$hour_dir" ]]; then
            continue
        fi
        
        hour=$(basename "$hour_dir")
        ts_files=("$hour_dir"/segment_*.ts)
        
        if [[ -e "${ts_files[0]}" ]]; then
            count=${#ts_files[@]}
            size=$(du -sh "$hour_dir" | cut -f1)
            
            echo "  Hour $hour: Found $count TS files ($size)"
            
            if [[ "$DRY_RUN" == false ]]; then
                rm -f "$hour_dir"/segment_*.ts
                echo "  ✅ Deleted"
            fi
            
            ((total_deleted += count))
        fi
    done
    
    # Delete TS segments from temp folder (if exists)
    if [[ -d "$capture_dir/segments/temp" ]]; then
        temp_ts_files=("$capture_dir/segments/temp"/segment_*.ts)
        if [[ -e "${temp_ts_files[0]}" ]]; then
            count=${#temp_ts_files[@]}
            echo "  Temp folder: Found $count TS files"
            
            if [[ "$DRY_RUN" == false ]]; then
                rm -f "$capture_dir/segments/temp"/segment_*.ts
                echo "  ✅ Deleted"
            fi
            
            ((total_deleted += count))
        fi
    fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ "$DRY_RUN" == true ]]; then
    echo "🔍 DRY RUN: Would delete $total_deleted TS segment files"
    echo "Run without --dry-run to actually delete"
else
    echo "✅ Deleted $total_deleted TS segment files from cold storage"
    echo "💾 Live TS segments in hot/ folders preserved"
fi

