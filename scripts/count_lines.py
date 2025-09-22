#!/usr/bin/env python3
import os
from pathlib import Path

def count_lines(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except:
        return 0

def main():
    root = Path(__file__).parent.parent
    total_lines = 0
    total_files = 0
    folder_data = {}
    
    # Code file extensions to count
    code_exts = {'.py', '.js', '.jsx', '.ts', '.tsx', '.sh', '.sql', '.md', '.yml', '.yaml', '.json', '.html', '.css', '.conf', '.service'}
    
    for file_path in root.rglob('*'):
        if file_path.is_file() and file_path.suffix in code_exts:
            # Skip certain directories
            if any(skip in str(file_path) for skip in ['venv/', '__pycache__/', 'node_modules/', '.git/', 'dist/']):
                continue
                
            lines = count_lines(file_path)
            total_lines += lines
            total_files += 1
            
            # Get folder relative to root
            folder = file_path.relative_to(root).parts[0] if len(file_path.relative_to(root).parts) > 1 else 'root'
            if folder not in folder_data:
                folder_data[folder] = {'lines': 0, 'files': 0}
            folder_data[folder]['lines'] += lines
            folder_data[folder]['files'] += 1
    
    print(f"Total lines: {total_lines:,} ({total_files} files)")
    print("\nPer folder:")
    for folder, data in sorted(folder_data.items()):
        print(f"  {folder}: {data['lines']:,} lines ({data['files']} files)")

if __name__ == "__main__":
    main()
