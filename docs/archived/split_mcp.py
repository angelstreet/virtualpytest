#!/usr/bin/env python3
"""
Script to split mcp.md into modular files.
Extracts specific line ranges and creates separate documentation files.
"""

# Read the original file
with open('mcp.md', 'r') as f:
    lines = f.readlines()

# Define the file splits (line ranges from original mcp.md)
splits = {
    'mcp/mcp_tools_tree.md': (111, 628),  # Primitive tools (already created manually, skip)
    'mcp/mcp_tools_control.md': (1106, 1142),  # Critical: take_control
    'mcp/mcp_tools_action.md': (1145, 1368),  # Discovery + Action Execution  
    'mcp/mcp_tools_navigation.md': (1371, 1411),  # Navigation
    'mcp/mcp_tools_verification.md': (1414, 1460),  # Verification
    'mcp/mcp_tools_testcase.md': (1464, 1633),  # TestCase Management
    'mcp/mcp_tools_script.md': (1637, 1668),  # Script Execution
    'mcp/mcp_tools_ai.md': (1672, 1729),  # AI Generation
    'mcp/mcp_tools_screenshot.md': (1770, 1812),  # capture_screenshot
    'mcp/mcp_tools_userinterface.md': (1816, 2109),  # UserInterface Management
    'mcp/mcp_playground.md': (2512, 2873),  # MCP Playground
}

# Create the split files
for filename, (start, end) in splits.items():
    # Skip if already exists (tree file was created manually)
    import os
    if os.path.exists(filename) and 'tree' in filename:
        print(f"Skipping {filename} (already exists)")
        continue
    
    content = ''.join(lines[start-1:end])  # -1 because lines are 0-indexed
    
    # Add header
    tool_name = filename.split('_')[-1].replace('.md', '').title()
    header = f"# MCP {tool_name} Tools\n\n[← Back to MCP Documentation](../mcp.md)\n\n---\n\n"
    
    with open(filename, 'w') as f:
        f.write(header + content)
    
    print(f"Created {filename} (lines {start}-{end}, {end-start+1} lines)")

print("\n✅ Split complete!")
print("Files created in docs/mcp/")

