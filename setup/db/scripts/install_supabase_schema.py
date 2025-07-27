#!/usr/bin/env python3

"""
VirtualPyTest - Install Database Schema on Supabase
This script creates all required tables and indexes in a Supabase database using Migration API
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, Any
import time

def load_env_file(env_path: Path) -> Dict[str, str]:
    """Load environment variables from .env file"""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

def create_example_env(env_path: Path):
    """Create example .env file"""
    example_content = """# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# You can find these values in your Supabase project settings:
# 1. Go to https://app.supabase.com/project/YOUR_PROJECT/settings/api
# 2. Copy the URL and service_role key
"""
    with open(env_path, 'w') as f:
        f.write(example_content)

def get_project_id_from_url(supabase_url: str) -> str:
    """Extract project ID from Supabase URL"""
    return supabase_url.split('//')[1].split('.')[0]

def apply_migration(project_id: str, service_key: str, migration_name: str, sql_content: str) -> tuple[bool, str]:
    """Apply a migration using Supabase Management API"""
    
    # Use Supabase Management API to apply migration
    api_url = f"https://api.supabase.com/v1/projects/{project_id}/database/migrations"
    
    headers = {
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    migration_data = {
        'name': migration_name,
        'statements': [{'statement': sql_content}]
    }
    
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=migration_data,
            timeout=60
        )
        
        if response.status_code in [200, 201]:
            return True, "Migration applied successfully"
        else:
            error_detail = ""
            try:
                error_data = response.json()
                error_detail = error_data.get('message', response.text)
            except:
                error_detail = response.text
            
            return False, f"HTTP {response.status_code}: {error_detail}"
            
    except requests.exceptions.Timeout:
        return False, "Request timed out after 60 seconds"
    except Exception as e:
        return False, f"Request failed: {str(e)}"

def test_connection(supabase_url: str, service_key: str) -> bool:
    """Test connection to Supabase"""
    try:
        headers = {
            'Authorization': f'Bearer {service_key}',
            'apikey': service_key
        }
        
        # Test with a simple REST API call
        response = requests.get(
            f"{supabase_url}/rest/v1/",
            headers=headers,
            timeout=10
        )
        return response.status_code in [200, 404]  # 404 is OK, means API is accessible
    except Exception as e:
        print(f"  ❌ Connection error: {e}")
        return False

def execute_schema_file(file_path: Path, project_id: str, service_key: str, description: str) -> bool:
    """Execute a schema SQL file using Supabase Migration API"""
    print(f"📄 Executing: {description}")
    print(f"   File: {file_path}")
    
    if not file_path.exists():
        print(f"❌ Schema file not found: {file_path}")
        return False
    
    try:
        sql_content = file_path.read_text()
        
        # Generate migration name from file
        migration_name = f"virtualpytest_{file_path.stem}_{int(time.time())}"
        
        print(f"   Applying migration: {migration_name}")
        success, error_msg = apply_migration(project_id, service_key, migration_name, sql_content)
        
        if not success:
            print(f"❌ FAILED to apply migration")
            print(f"   Migration: {migration_name}")
            print(f"   Error: {error_msg}")
            print(f"\n🛑 Aborting installation due to failure in {description}")
            return False
        else:
            print(f"   ✅ Migration applied successfully")
        
        print(f"✅ {description} completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to execute: {description}")
        print(f"   Error: {e}")
        return False

def main():
    print("🗄️ VirtualPyTest Database Schema Installation")
    print("==============================================")
    
    # Get project paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent
    schema_dir = project_root / "setup" / "db" / "schema"
    env_file = project_root / "setup" / ".env"
    
    # Load environment variables
    if env_file.exists():
        print("📄 Loading environment variables from .env file...")
        env_vars = load_env_file(env_file)
        print("✅ Environment variables loaded")
    else:
        print(f"⚠️ .env file not found at: {env_file}")
        print("💡 Creating example .env file...")
        create_example_env(env_file)
        print("📝 Created example .env file in setup/ directory")
        print(f"   Please edit {env_file} with your Supabase credentials")
        return 1
    
    # Check required variables
    supabase_url = env_vars.get('SUPABASE_URL')
    service_key = env_vars.get('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not service_key:
        print("❌ Required environment variables not set in .env file:")
        print("   SUPABASE_URL - Your Supabase project URL")
        print("   SUPABASE_SERVICE_ROLE_KEY - Your Supabase service role key")
        print("\n💡 You can find these in your Supabase project settings:")
        print("   1. Go to https://app.supabase.com/project/YOUR_PROJECT/settings/api")
        print("   2. Copy the URL and service_role key")
        return 1
    
    # Extract project ID
    project_id = get_project_id_from_url(supabase_url)
    print(f"📋 Project ID: {project_id}")
    
    # Test connection
    print("🔍 Testing database connection...")
    if not test_connection(supabase_url, service_key):
        print("❌ Failed to connect to Supabase")
        print("   Please check your SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return 1
    
    print("✅ Database connection successful")
    print()
    
    # Execute schema files
    print("🚀 Installing VirtualPyTest database schema...")
    print()
    
    schema_files = [
        ("001_core_tables.sql", "Core Tables (devices, models, controllers, environments, campaigns)"),
        ("002_ui_navigation_tables.sql", "UI & Navigation Tables (userinterfaces, navigation_trees, history)"),
        ("003_test_execution_tables.sql", "Test Execution Tables (test_cases, executions, results)"),
        ("004_actions_verifications.sql", "Actions & Verifications Tables (actions, verifications, references)"),
        ("005_monitoring_analytics.sql", "Monitoring & Analytics Tables (alerts, heatmaps, metrics)")
    ]
    
    for filename, description in schema_files:
        file_path = schema_dir / filename
        if not execute_schema_file(file_path, project_id, service_key, description):
            print(f"\n❌ Installation FAILED at: {description}")
            print("🛑 Database schema installation aborted")
            return 1
        print()
    
    print("🎉 VirtualPyTest database schema installation complete!")
    print(f"📊 Successfully executed all {len(schema_files)} schema files")
    print()
    print("📋 Next steps:")
    print("   1. Update your application .env files with database credentials")
    print("   2. Test the connection from your application")
    print("   3. Optionally run: python3 setup/db/scripts/seed_example_data.py")
    print()
    
    print("🔗 Useful links:")
    print(f"   • Supabase Dashboard: https://app.supabase.com/project/{project_id}")
    print(f"   • Database Tables: https://app.supabase.com/project/{project_id}/editor")
    print(f"   • Migrations: https://app.supabase.com/project/{project_id}/database/migrations")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 