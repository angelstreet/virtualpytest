#!/usr/bin/env python3
"""
Reference Migration Script: device_model → userinterface

This script migrates verification references (both image and text) from device_model-based 
organization to userinterface-based organization.

Database Changes:
1. Add userinterface_id column to verifications_references table
2. Populate userinterface_id based on device_model mapping
3. Update R2 paths to use userinterface names
4. Copy files in R2 to new paths
5. Remove device_model column (optional, after verification)

R2 Path Changes:
- reference-images/{device_model}/ → reference-images/{userinterface_name}/
- text-references/{device_model}/ → text-references/{userinterface_name}/
"""

import os
import sys
from typing import Dict, List, Tuple

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load .env file from project root
from dotenv import load_dotenv
env_path = os.path.join(project_root, '.env')

if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
    print(f"✅ Loaded environment from: {env_path}\n")
else:
    print(f"⚠️  Warning: .env file not found at: {env_path}")
    print("    Make sure environment variables are set\n")

from shared.src.lib.utils.supabase_utils import get_supabase_client
from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils


def get_team_id_from_env() -> str:
    """Get team_id from environment variable or use default."""
    team_id = os.environ.get('TEAM_ID')
    if team_id:
        return team_id
    
    DEFAULT_TEAM_ID = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
    print(f"⚠️  [Migration] TEAM_ID not in environment, using default: {DEFAULT_TEAM_ID}")
    return DEFAULT_TEAM_ID


def get_device_model_to_userinterface_mapping(supabase, team_id: str) -> Dict[str, Dict]:
    """
    Build mapping of device_model → userinterface based on userinterfaces.models array.
    
    Returns:
        Dict: {device_model: {'userinterface_id': uuid, 'userinterface_name': str}}
    """
    print("📊 [Migration] Building device_model → userinterface mapping...")
    
    # Get all userinterfaces with their models
    ui_result = supabase.table('userinterfaces').select('id, name, models').eq('team_id', team_id).execute()
    
    mapping = {}
    
    for ui in ui_result.data:
        ui_id = ui['id']
        ui_name = ui['name']
        models = ui.get('models', [])
        
        # Map each device_model to this userinterface
        for model in models:
            mapping[model] = {
                'userinterface_id': ui_id,
                'userinterface_name': ui_name
            }
            print(f"   {model} → {ui_name}")
    
    return mapping


def step1_add_userinterface_column(supabase) -> bool:
    """Add userinterface_id column to verifications_references table."""
    print("\n📝 [Step 1] Adding userinterface_id column...")
    
    try:
        # Check if column already exists by trying to select it
        try:
            test_query = supabase.table('verifications_references').select('userinterface_id').limit(1).execute()
            print("   ℹ️  Column userinterface_id already exists")
            return True
        except:
            # Column doesn't exist, need to add it
            pass
        
        # Need to use direct SQL - let user run migration manually
        print("\n   ⚠️  Need to add userinterface_id column to database")
        print("\n   Please run this SQL in your Supabase SQL Editor:")
        print("\n   " + "=" * 70)
        print("""
   ALTER TABLE verifications_references 
   ADD COLUMN IF NOT EXISTS userinterface_id UUID REFERENCES userinterfaces(id);
   
   CREATE INDEX IF NOT EXISTS idx_verifications_references_userinterface_id 
   ON verifications_references(userinterface_id);
        """)
        print("   " + "=" * 70)
        print("\n   After running the SQL, press ENTER to continue...")
        input()
        
        # Verify column was added
        try:
            test_query = supabase.table('verifications_references').select('userinterface_id').limit(1).execute()
            print("   ✅ Column verified successfully")
            return True
        except Exception as e:
            print(f"   ❌ Column still not found. Please ensure SQL was run successfully.")
            print(f"   Error: {e}")
            return False
        
    except Exception as e:
        print(f"   ❌ Failed to check/add column: {e}")
        return False


def step2_populate_userinterface_ids(supabase, mapping: Dict, team_id: str) -> Tuple[int, int]:
    """Populate userinterface_id based on device_model."""
    print("\n📝 [Step 2] Populating userinterface_id values...")
    
    # Get all references
    refs_result = supabase.table('verifications_references').select(
        'id, name, device_model, reference_type'
    ).eq('team_id', team_id).execute()
    
    success_count = 0
    failed_count = 0
    
    for ref in refs_result.data:
        ref_id = ref['id']
        device_model = ref['device_model']
        ref_name = ref['name']
        
        if device_model not in mapping:
            print(f"   ⚠️  No userinterface found for device_model: {device_model} (ref: {ref_name})")
            failed_count += 1
            continue
        
        userinterface_id = mapping[device_model]['userinterface_id']
        
        try:
            supabase.table('verifications_references').update({
                'userinterface_id': userinterface_id
            }).eq('id', ref_id).execute()
            
            success_count += 1
            print(f"   ✅ {ref_name}: {device_model} → {mapping[device_model]['userinterface_name']}")
            
        except Exception as e:
            print(f"   ❌ Failed to update {ref_name}: {e}")
            failed_count += 1
    
    print(f"\n   Summary: {success_count} succeeded, {failed_count} failed")
    return success_count, failed_count


def step3_copy_r2_files(supabase, mapping: Dict, team_id: str) -> Tuple[int, int]:
    """Copy reference files in R2 to new userinterface-based paths."""
    print("\n📦 [Step 3] Copying files in R2...")
    
    cloudflare = get_cloudflare_utils()
    
    # Get all references with their R2 paths
    refs_result = supabase.table('verifications_references').select(
        'id, name, device_model, reference_type, r2_path'
    ).eq('team_id', team_id).execute()
    
    success_count = 0
    failed_count = 0
    
    for ref in refs_result.data:
        ref_id = ref['id']
        device_model = ref['device_model']
        ref_name = ref['name']
        old_r2_path = ref['r2_path']
        reference_type = ref['reference_type']
        
        if device_model not in mapping:
            failed_count += 1
            continue
        
        userinterface_name = mapping[device_model]['userinterface_name']
        
        # Build new R2 path
        if reference_type == 'reference_image':
            # reference-images/{device_model}/file.jpg → reference-images/{userinterface_name}/file.jpg
            new_r2_path = old_r2_path.replace(
                f"reference-images/{device_model}/",
                f"reference-images/{userinterface_name}/"
            )
        elif reference_type == 'reference_text':
            # text-references/{device_model}/file → text-references/{userinterface_name}/file
            new_r2_path = old_r2_path.replace(
                f"text-references/{device_model}/",
                f"text-references/{userinterface_name}/"
            )
        else:
            print(f"   ⚠️  Unknown reference_type: {reference_type} for {ref_name}")
            failed_count += 1
            continue
        
        # Copy file in R2
        try:
            copy_result = cloudflare.copy_file(old_r2_path, new_r2_path)
            
            if copy_result.get('success'):
                success_count += 1
                print(f"   ✅ {ref_name}: {device_model}/ → {userinterface_name}/")
            else:
                failed_count += 1
                print(f"   ❌ {ref_name}: {copy_result.get('error')}")
                
        except Exception as e:
            failed_count += 1
            print(f"   ❌ {ref_name}: {str(e)}")
    
    print(f"\n   Summary: {success_count} files copied, {failed_count} failed")
    return success_count, failed_count


def step4_update_r2_paths(supabase, mapping: Dict, team_id: str) -> Tuple[int, int]:
    """Update r2_path and r2_url in database to point to new paths."""
    print("\n🗄️  [Step 4] Updating database R2 paths...")
    
    # Get all references
    refs_result = supabase.table('verifications_references').select(
        'id, name, device_model, reference_type, r2_path, r2_url'
    ).eq('team_id', team_id).execute()
    
    success_count = 0
    failed_count = 0
    
    for ref in refs_result.data:
        ref_id = ref['id']
        device_model = ref['device_model']
        ref_name = ref['name']
        old_r2_path = ref['r2_path']
        old_r2_url = ref.get('r2_url', '')
        reference_type = ref['reference_type']
        
        if device_model not in mapping:
            failed_count += 1
            continue
        
        userinterface_name = mapping[device_model]['userinterface_name']
        
        # Build new paths
        if reference_type == 'reference_image':
            new_r2_path = old_r2_path.replace(
                f"reference-images/{device_model}/",
                f"reference-images/{userinterface_name}/"
            )
            new_r2_url = old_r2_url.replace(
                f"reference-images/{device_model}/",
                f"reference-images/{userinterface_name}/"
            )
        elif reference_type == 'reference_text':
            new_r2_path = old_r2_path.replace(
                f"text-references/{device_model}/",
                f"text-references/{userinterface_name}/"
            )
            new_r2_url = old_r2_url.replace(
                f"text-references/{device_model}/",
                f"text-references/{userinterface_name}/"
            )
        else:
            failed_count += 1
            continue
        
        # Update database
        try:
            supabase.table('verifications_references').update({
                'r2_path': new_r2_path,
                'r2_url': new_r2_url
            }).eq('id', ref_id).execute()
            
            success_count += 1
            print(f"   ✅ Updated: {ref_name}")
            
        except Exception as e:
            failed_count += 1
            print(f"   ❌ Failed: {ref_name}: {e}")
    
    print(f"\n   Summary: {success_count} updated, {failed_count} failed")
    return success_count, failed_count


def check_environment():
    """Check required environment variables are set."""
    required_vars = [
        'NEXT_PUBLIC_SUPABASE_URL',
        'NEXT_PUBLIC_SUPABASE_ANON_KEY',
        'CLOUDFLARE_R2_ENDPOINT',
        'CLOUDFLARE_R2_ACCESS_KEY_ID',
        'CLOUDFLARE_R2_SECRET_ACCESS_KEY',
        'CLOUDFLARE_R2_PUBLIC_URL'
    ]
    
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these environment variables before running the migration.")
        return False
    
    print("✅ All required environment variables are set")
    return True


def main():
    """Main migration execution."""
    print("=" * 80)
    print("🚀 Reference Migration: device_model → userinterface")
    print("=" * 80)
    print()
    
    # Check environment variables
    if not check_environment():
        sys.exit(1)
    
    print()
    
    try:
        supabase = get_supabase_client()
        team_id = get_team_id_from_env()
        
        # Get device_model → userinterface mapping
        mapping = get_device_model_to_userinterface_mapping(supabase, team_id)
        
        if not mapping:
            print("\n⚠️  No userinterfaces found or no device_model mappings available.")
            return
        
        print(f"\n✅ Found {len(mapping)} device_model → userinterface mappings")
        
        # Show migration plan
        print("\n" + "=" * 80)
        print("⚠️  MIGRATION PLAN:")
        print("=" * 80)
        print("This will:")
        print("1. Add userinterface_id column to verifications_references table")
        print("2. Populate userinterface_id based on device_model")
        print("3. Copy reference files in R2 to new userinterface paths")
        print("4. Update database r2_path and r2_url to new paths")
        print("5. Keep original files and device_model column as backup")
        print("\nPress ENTER to continue or Ctrl+C to cancel...")
        input()
        
        # Execute migration steps
        if not step1_add_userinterface_column(supabase):
            print("\n❌ Migration failed at step 1")
            sys.exit(1)
        
        ids_success, ids_failed = step2_populate_userinterface_ids(supabase, mapping, team_id)
        r2_success, r2_failed = step3_copy_r2_files(supabase, mapping, team_id)
        db_success, db_failed = step4_update_r2_paths(supabase, mapping, team_id)
        
        # Final summary
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE")
        print("=" * 80)
        print(f"UserInterface IDs:  {ids_success} populated")
        print(f"R2 Files:           {r2_success} copied")
        print(f"Database Paths:     {db_success} updated")
        
        if ids_failed > 0 or r2_failed > 0 or db_failed > 0:
            print(f"\n⚠️  Some operations failed:")
            if ids_failed > 0:
                print(f"   - UserInterface IDs: {ids_failed} failed")
            if r2_failed > 0:
                print(f"   - R2 Files: {r2_failed} failed")
            if db_failed > 0:
                print(f"   - Database Paths: {db_failed} failed")
        
        print("\n📝 Next steps:")
        print("1. Verify references work correctly in the UI")
        print("2. Test creating new references")
        print("3. After verification (1+ week), optionally remove device_model column")
        print("4. After verification, delete old R2 paths")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n❌ Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

