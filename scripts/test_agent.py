#!/usr/bin/env python3
"""
Agent Testing Script

Quick testing utilities for agent skills without rebuilding the full server.
Use this for rapid development and testing of agent functionality.

Usage:
    python scripts/test_agent.py --reload-skills
    python scripts/test_agent.py --test-skill device-control
    python scripts/test_agent.py --match-skill "swipe down on device1"
    python scripts/test_agent.py --list-skills
"""

import sys
import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional

# Add backend_server to path
backend_server_path = Path(__file__).parent.parent / 'backend_server' / 'src'
sys.path.insert(0, str(backend_server_path))

def get_server_url() -> str:
    """Get server URL from environment or default"""
    return os.getenv('SERVER_URL', 'http://localhost:5109')

def make_request(endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make HTTP request to server"""
    url = f"{get_server_url()}{endpoint}"

    try:
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data)
        else:
            print(f"❌ Unsupported method: {method}")
            return {}

        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return {}

def reload_skills():
    """Reload all skills from YAML"""
    print("🔄 Reloading skills...")
    result = make_request('/server/skills/reload', 'POST')

    if result:
        count = result.get('count', 0)
        print(f"✅ Reloaded {count} skills")
        return True
    return False

def list_skills():
    """List all available skills"""
    print("📋 Listing skills...")
    result = make_request('/server/skills')

    if result:
        skills = result.get('skills', [])
        print(f"\nFound {len(skills)} skills:\n")

        for skill in skills:
            device_icon = '🔌' if skill.get('requires_device') else '📝'
            platform = skill.get('platform') or 'all'
            print(f"{device_icon} {skill['name']:20} ({platform:6}) - {skill['description']}")

        return True
    return False

def test_skill(skill_name: str):
    """Test a specific skill for validity"""
    print(f"🧪 Testing skill: {skill_name}")
    result = make_request(f'/server/skills/test/{skill_name}', 'POST')

    if result:
        if result.get('valid'):
            print(f"✅ Skill '{skill_name}' is valid")
            skill_info = result.get('skill', {})
            print(f"   - {skill_info.get('triggers', 0)} triggers")
            print(f"   - {skill_info.get('tools', 0)} tools")
        else:
            print(f"❌ Skill '{skill_name}' has issues:")
            for issue in result.get('issues', []):
                print(f"   - {issue}")
        return True
    return False

def match_skill(message: str):
    """Test skill matching against a message"""
    print(f"🎯 Testing skill matching for: '{message}'")
    result = make_request('/server/skills/match', 'POST', {'message': message})

    if result:
        if result.get('matched'):
            skill = result.get('skill', {})
            print(f"✅ Matched skill: {skill.get('name')}")
            print(f"   Description: {skill.get('description')}")
        else:
            print("❌ No skill matched")
        return True
    return False

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == '--reload-skills':
        reload_skills()
    elif command == '--list-skills':
        list_skills()
    elif command == '--test-skill' and len(sys.argv) >= 3:
        test_skill(sys.argv[2])
    elif command == '--match-skill' and len(sys.argv) >= 3:
        message = ' '.join(sys.argv[2:])
        match_skill(message)
    else:
        print("❌ Invalid command")
        print(__doc__)
        sys.exit(1)

if __name__ == '__main__':
    main()