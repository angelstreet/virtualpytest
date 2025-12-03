#!/usr/bin/env python3
"""
Export OpenAPI Specifications from Postman & Generate Beautiful HTML Docs
1. Downloads all OpenAPI specs from Postman
2. Saves YAML files to docs/openapi_specs/
3. Generates beautiful HTML documentation to docs/api_docs/
"""

import os
import sys
import json
import requests
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Configuration
POSTMAN_API_KEY = os.getenv('POSTMAN_API_KEY')
if not POSTMAN_API_KEY:
    print("❌ Error: POSTMAN_API_KEY not found in .env file")
    print("Add it to your .env file:")
    print("  POSTMAN_API_KEY=your-key-here")
    sys.exit(1)

WORKSPACE_ID = "91dbec69-5756-413d-a530-a97b9cadf615"
YAML_DIR = Path(__file__).parent.parent / "docs" / "openapi" / "specs"
DOCS_DIR = Path(__file__).parent.parent / "docs" / "openapi" / "docs"

# Spec mappings (ID -> filename)
SPECS = {
    "f2193488-7d68-46e7-a480-dca6462e892a": "server-device-management",
    "d75354a3-6e8c-4c55-b401-49d83d3a5718": "server-campaign-management",
    "e73f30d2-9c3e-4670-a72a-46cf9d14b187": "server-core-system",
    "da4b8bfc-565e-46d8-bbda-d76234430b46": "server-navigation-management",
    "b51b8d1c-7bd5-4f7c-9a7e-61ea7dfd62e3": "server-testcase-management",
    "2615abf6-2613-4a22-b058-c85603fa3efd": "server-script-management",
    "f3fb66c6-a7ce-46fd-885e-ebbdb07f6c51": "server-requirements-management",
    "42f978c7-b2ef-4673-8c82-69dbe7581dea": "server-ai-analysis",
    "77c15aaa-f04a-4584-8bc3-34b7f2185388": "server-metrics-analytics",
    "dde5b7e6-4b92-49d7-9f6a-1ebde263c2bf": "server-deployment-scheduling",
    "e42eda2e-d046-461f-9c31-d8a991711157": "server-user-interface-management",
    "b02534c3-f5dc-425e-acf5-9edaf9f32bd8": "host-testcase-execution",
    "afa2b34c-2802-41f2-b8ae-e01c6331572b": "host-ai-exploration",
    "e1ef3690-24a8-4dff-84a3-1a10f2f51d9d": "host-verification-suite",
}

# Colors
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'

def print_header():
    print(f"{Colors.BLUE}╔══════════════════════════════════════════════════════════╗{Colors.NC}")
    print(f"{Colors.BLUE}║   VirtualPyTest - OpenAPI Spec Export Utility          ║{Colors.NC}")
    print(f"{Colors.BLUE}╚══════════════════════════════════════════════════════════╝{Colors.NC}\n")

def check_node_tools():
    """Check if required Node.js tools are installed."""
    try:
        subprocess.run(['npx', '--version'], capture_output=True, check=True)
        return True
    except:
        return False

def inject_auto_expand_script(html_file):
    """Inject JavaScript to auto-expand menu items in ReDoc HTML."""
    auto_expand_script = """
    // Auto-expand all menu items after Redoc loads
    setTimeout(function() {
      var menuLabels = document.querySelectorAll('[data-item-id] > label');
      menuLabels.forEach(function(label) {
        var svg = label.querySelector('svg');
        if (svg && !label.parentElement.classList.contains('active')) {
          label.click();
        }
      });
    }, 300);
    """
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Insert the script before the closing </script></body> tags
        content = content.replace(
            '    </script>\n</body>',
            f'{auto_expand_script}    </script>\n</body>'
        )
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"  {Colors.YELLOW}⚠{Colors.NC} Could not inject auto-expand script: {e}")

def generate_html_docs():
    """Generate beautiful HTML documentation using redoc-cli."""
    print(f"\n{Colors.BLUE}╔══════════════════════════════════════════════════════════╗{Colors.NC}")
    print(f"{Colors.BLUE}║   Generating Beautiful HTML Documentation               ║{Colors.NC}")
    print(f"{Colors.BLUE}╚══════════════════════════════════════════════════════════╝{Colors.NC}\n")
    
    if not check_node_tools():
        print(f"{Colors.RED}✗{Colors.NC} Node.js/npx not found. Skipping HTML generation.\n")
        print(f"{Colors.YELLOW}Install Node.js to generate documentation:{Colors.NC}")
        print(f"  brew install node  # or download from nodejs.org\n")
        return False
    
    # Create docs directory
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate HTML for each spec
    yaml_files = list(YAML_DIR.glob("*.yaml"))
    total = len(yaml_files)
    
    for index, yaml_file in enumerate(yaml_files, 1):
        spec_name = yaml_file.stem
        html_file = DOCS_DIR / f"{spec_name}.html"
        
        print(f"{Colors.BLUE}[{index}/{total}]{Colors.NC} {spec_name}.yaml → {spec_name}.html")
        
        try:
            # Use redoc-cli to generate standalone HTML
            subprocess.run([
                'npx', '-y', 'redoc-cli', 'bundle',
                str(yaml_file),
                '-o', str(html_file),
                '--title', f'VirtualPyTest API - {spec_name.replace("-", " ").title()}'
            ], capture_output=True, check=True, text=True)
            
            # Post-process: Add auto-expand script for menu items
            inject_auto_expand_script(html_file)
            
            print(f"  {Colors.GREEN}✓{Colors.NC} Generated: {html_file}\n")
        except subprocess.CalledProcessError as e:
            print(f"  {Colors.RED}✗{Colors.NC} Failed: {e.stderr}\n")
    
    # Create index.html
    create_index_html(yaml_files)
    
    return True

def create_index_html(yaml_files):
    """Create an index page linking to all documentation."""
    index_path = DOCS_DIR / "index.html"
    
    server_specs = [f for f in yaml_files if f.stem.startswith('server-')]
    host_specs = [f for f in yaml_files if f.stem.startswith('host-')]
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VirtualPyTest API Documentation</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
               background: #0f172a; 
               padding: 20px; min-height: 100vh; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .section {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 20px; margin-bottom: 20px; 
                    box-shadow: 0 4px 20px rgba(0,0,0,0.2); }}
        .section h2 {{ color: #94a3b8; margin-bottom: 16px; font-size: 1rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
        .api-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }}
        .api-card {{ background: #334155; 
                     padding: 14px 16px; border-radius: 6px; transition: all 0.2s; 
                     border-left: 3px solid #64748b; }}
        .api-card:hover {{ transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.3); background: #3f4f63; }}
        .api-card a {{ text-decoration: none; color: #f1f5f9; font-weight: 500; font-size: 0.95rem; }}
        .api-card p {{ color: #94a3b8; margin-top: 4px; font-size: 0.8rem; }}
        .host-card {{ border-left-color: #94a3b8; background: #3d4f5f; }}
        .host-card:hover {{ background: #4a5f70; }}
        .stats {{ display: flex; justify-content: center; gap: 60px; padding: 8px 0; }}
        .stat {{ text-align: center; }}
        .stat-number {{ font-size: 1.5em; color: #e2e8f0; font-weight: bold; }}
        .stat-label {{ color: #64748b; margin-top: 2px; font-size: 0.7rem; text-transform: uppercase; }}
        .section.stats-section {{ padding: 12px 20px; margin-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="section">
            <h2>📡 Server APIs</h2>
            <div class="api-grid">
"""
    
    for spec_file in sorted(server_specs):
        name = spec_file.stem.replace('server-', '').replace('-', ' ').title()
        html_content += f"""                <div class="api-card">
                    <a href="{spec_file.stem}.html">{name}</a>
                    <p>Server-side {name.lower()} endpoints</p>
                </div>
"""
    
    html_content += """            </div>
        </div>
        
        <div class="section">
            <h2>🖥️ Host APIs</h2>
            <div class="api-grid">
"""
    
    for spec_file in sorted(host_specs):
        name = spec_file.stem.replace('host-', '').replace('-', ' ').title()
        html_content += f"""                <div class="api-card host-card">
                    <a href="{spec_file.stem}.html">{name}</a>
                    <p>Host-side {name.lower()} operations</p>
                </div>
"""
    
    html_content += f"""            </div>
        </div>
        
        <div class="section stats-section">
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">{len(server_specs)}</div>
                    <div class="stat-label">Server APIs</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{len(host_specs)}</div>
                    <div class="stat-label">Host APIs</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{len(yaml_files)}</div>
                    <div class="stat-label">Total</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"{Colors.GREEN}✓{Colors.NC} Created index: {index_path}\n")

def print_footer(success_count, total_count, docs_generated):
    print(f"\n{Colors.GREEN}╔══════════════════════════════════════════════════════════╗{Colors.NC}")
    print(f"{Colors.GREEN}║   Complete!                                             ║{Colors.NC}")
    print(f"{Colors.GREEN}╚══════════════════════════════════════════════════════════╝{Colors.NC}\n")
    print(f"{Colors.BLUE}YAML Specs:{Colors.NC} {YAML_DIR} ({success_count}/{total_count} exported)")
    if docs_generated:
        print(f"{Colors.BLUE}HTML Docs:{Colors.NC}  {DOCS_DIR} ({success_count} pages generated)")
        print(f"\n{Colors.YELLOW}Open documentation:{Colors.NC}")
        print(f"  file://{DOCS_DIR / 'index.html'}\n")
    else:
        print(f"\n{Colors.YELLOW}To generate HTML docs, install Node.js:{Colors.NC}")
        print(f"  brew install node\n")

def get_spec_files(spec_id):
    """Get list of files in a spec."""
    url = f"https://api.postman.com/specs/{spec_id}/files"
    headers = {"X-Api-Key": POSTMAN_API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('files', [])
    except Exception as e:
        print(f"  {Colors.RED}✗{Colors.NC} Error getting file list: {e}")
        return []

def download_spec_file(spec_id, file_path):
    """Download a spec file content."""
    url = f"https://api.postman.com/specs/{spec_id}/files/{file_path}"
    headers = {"X-Api-Key": POSTMAN_API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('content', '')
    except Exception as e:
        print(f"  {Colors.RED}✗{Colors.NC} Error downloading file: {e}")
        return None

def export_spec(spec_id, spec_name, index, total):
    """Export a single spec."""
    print(f"{Colors.BLUE}[{index}/{total}]{Colors.NC} Exporting: {Colors.YELLOW}{spec_name}{Colors.NC}")
    
    # Get spec files
    files = get_spec_files(spec_id)
    if not files:
        print(f"  {Colors.YELLOW}⚠{Colors.NC}  No files found\n")
        return False
    
    # Find root file (usually index.yaml)
    root_file = next((f for f in files if f.get('type') == 'ROOT'), None)
    if not root_file:
        print(f"  {Colors.YELLOW}⚠{Colors.NC}  No root file found\n")
        return False
    
    file_path = root_file.get('path', 'index.yaml')
    
    # Download content
    content = download_spec_file(spec_id, file_path)
    if content is None:
        return False
    
    # Save to file
    output_file = YAML_DIR / f"{spec_name}.yaml"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  {Colors.GREEN}✓{Colors.NC} Saved to: {output_file}\n")
        return True
    except Exception as e:
        print(f"  {Colors.RED}✗{Colors.NC} Error saving file: {e}\n")
        return False

def main():
    print_header()
    
    # Create output directories
    YAML_DIR.mkdir(parents=True, exist_ok=True)
    print(f"{Colors.GREEN}✓{Colors.NC} YAML directory: {Colors.YELLOW}{YAML_DIR}{Colors.NC}\n")
    
    # Export each spec
    total = len(SPECS)
    success_count = 0
    
    for index, (spec_id, spec_name) in enumerate(SPECS.items(), 1):
        if export_spec(spec_id, spec_name, index, total):
            success_count += 1
    
    # Generate HTML documentation
    docs_generated = generate_html_docs()
    
    print_footer(success_count, total, docs_generated)

if __name__ == "__main__":
    main()

