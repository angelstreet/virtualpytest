#!/bin/bash

# Script to copy only necessary documentation files to frontend/public/docs
# - OpenAPI HTML docs (original)
# - Only markdown files that are actually referenced/linked

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Copying documentation files...${NC}"

# Clean and create target directory
rm -rf public/docs
mkdir -p public/docs

# 1. Copy OpenAPI HTML docs (original - what you had before)
echo -e "${GREEN}✓${NC} Copying OpenAPI HTML docs"
mkdir -p public/docs/api/openapi
cp -r ../docs/api/openapi/docs/* public/docs/api/openapi/

# 2. Copy only referenced markdown files
echo -e "${GREEN}✓${NC} Finding and copying referenced markdown files"

# Temporary files to track what to copy
TEMP_DIR=$(mktemp -d)
FILES_TO_COPY="$TEMP_DIR/files_to_copy.txt"
PROCESSED="$TEMP_DIR/processed.txt"

touch "$FILES_TO_COPY"
touch "$PROCESSED"

# Start with main README and section READMEs (entry points)
cat > "$FILES_TO_COPY" << EOF
README.md
get-started/README.md
features/README.md
user-guide/README.md
technical/README.md
api/README.md
examples/README.md
integrations/README.md
EOF

echo -e "${YELLOW}→${NC} Following markdown links recursively"

# Process files iteratively
while IFS= read -r file; do
    # Skip if already processed
    if grep -Fxq "$file" "$PROCESSED" 2>/dev/null; then
        continue
    fi
    
    # Mark as processed
    echo "$file" >> "$PROCESSED"
    
    # Skip if file doesn't exist
    if [ ! -f "../docs/$file" ]; then
        continue
    fi
    
    # Find all markdown links in this file
    current_dir=$(dirname "$file")
    
    # Extract .md links from markdown
    grep -oE '\]\([^)]*\.md\)' "../docs/$file" 2>/dev/null | \
    sed 's/][(]//g' | sed 's/)//g' | \
    while IFS= read -r link; do
        # Resolve relative path
        if [[ "$link" == ../* ]]; then
            # Parent directory: ../features/file.md
            resolved=$(cd "../docs/$current_dir" && cd "$(dirname "$link")" && pwd)/$(basename "$link")
            resolved="${resolved#$(cd ../docs && pwd)/}"
        elif [[ "$link" == ./* ]]; then
            # Same directory: ./file.md
            resolved="$current_dir/${link#./}"
        else
            # Direct path
            resolved="$current_dir/$link"
        fi
        
        # Normalize and clean path
        resolved=$(echo "$resolved" | sed 's|/\./|/|g')
        
        # Add to files to copy if not already there
        if [ -f "../docs/$resolved" ] && ! grep -Fxq "$resolved" "$FILES_TO_COPY" 2>/dev/null; then
            echo "$resolved" >> "$FILES_TO_COPY"
        fi
    done
    
done < "$FILES_TO_COPY"

# Copy all found files
file_count=0
sort -u "$FILES_TO_COPY" | while IFS= read -r file; do
    if [ -f "../docs/$file" ]; then
        target_dir="public/docs/$(dirname "$file")"
        mkdir -p "$target_dir"
        cp "../docs/$file" "public/docs/$file"
        ((file_count++)) || true
    fi
done

# Count actual copied files
file_count=$(find public/docs -name "*.md" | wc -l | tr -d ' ')

# Cleanup
rm -rf "$TEMP_DIR"

echo -e "${GREEN}✓ Documentation copied successfully!${NC}"
echo -e "${BLUE}Copied: 15 OpenAPI HTML files + $file_count referenced markdown files${NC}"
