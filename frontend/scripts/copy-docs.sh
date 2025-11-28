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
security/README.md
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
        # Resolve relative path safely
        target_dir_path="../docs/$current_dir/$(dirname "$link")"
        
        # Skip if directory doesn't exist (avoids cd errors)
        if [ ! -d "$target_dir_path" ]; then
            continue
        fi
        
        # Resolve absolute paths to check boundaries
        abs_target_dir=$(cd "$target_dir_path" && pwd)
        abs_docs_root=$(cd "../docs" && pwd)
        
        # Skip if the file is outside the docs directory
        if [[ "$abs_target_dir" != "$abs_docs_root"* ]]; then
            continue
        fi
        
        # Construct the resolved path relative to docs root
        abs_file_path="$abs_target_dir/$(basename "$link")"
        resolved="${abs_file_path#$abs_docs_root/}"
        
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

# 3. Copy security reports if they exist (generated separately)
if [ -f "../docs/security/index.html" ]; then
    echo -e "${GREEN}✓${NC} Copying security reports"
    mkdir -p public/docs/security
    cp ../docs/security/index.html public/docs/security/
    [ -f "../docs/security/host-report.json" ] && cp ../docs/security/host-report.json public/docs/security/
    [ -f "../docs/security/server-report.json" ] && cp ../docs/security/server-report.json public/docs/security/
    [ -f "../docs/security/frontend-report.json" ] && cp ../docs/security/frontend-report.json public/docs/security/
    security_status="+ security reports"
else
    security_status="(security reports not generated yet)"
fi

echo -e "${GREEN}✓ Documentation copied successfully!${NC}"
echo -e "${BLUE}Copied: 15 OpenAPI HTML files + $file_count markdown files ${security_status}${NC}"
