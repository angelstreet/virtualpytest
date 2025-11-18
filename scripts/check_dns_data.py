#!/usr/bin/env python3
"""
Quick script to check if DNS lookup data is in Supabase database
"""
import sys
import os

# Add shared to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared', 'src'))

from lib.database.supabase_connection import get_supabase_client

def check_dns_data():
    """Check for DNS lookup results in database"""
    try:
        supabase = get_supabase_client()
        
        # Query for dns_lookuptime results
        print("🔍 Querying script_results for dns_lookuptime...")
        print("="*80)
        
        result = supabase.table('script_results')\
            .select('id, script_name, device_name, host_name, success, started_at, metadata')\
            .eq('script_name', 'dns_lookuptime')\
            .order('started_at', desc=True)\
            .limit(5)\
            .execute()
        
        if not result.data:
            print("❌ NO DNS LOOKUP DATA FOUND IN DATABASE!")
            print("\nPossible issues:")
            print("1. Data not being written to database")
            print("2. Script name mismatch")
            print("3. Database connection issue")
            return False
        
        print(f"✅ Found {len(result.data)} recent DNS lookup records\n")
        
        for idx, record in enumerate(result.data, 1):
            print(f"Record #{idx}:")
            print(f"  ID: {record['id']}")
            print(f"  Script: {record['script_name']}")
            print(f"  Device: {record['device_name']}")
            print(f"  Host: {record['host_name']}")
            print(f"  Success: {record['success']}")
            print(f"  Started: {record['started_at']}")
            
            # Check metadata
            metadata = record.get('metadata')
            if metadata:
                print(f"  ✅ Metadata exists:")
                print(f"     - Domain: {metadata.get('domain')}")
                print(f"     - Lookup Time (ms): {metadata.get('lookup_time_ms')}")
                print(f"     - DNS Server: {metadata.get('dns_server')}")
                print(f"     - IPv4: {metadata.get('ipv4_addresses')}")
            else:
                print(f"  ❌ NO METADATA!")
            print()
        
        # Check the specific record from logs
        specific_id = '8c94cc50-4717-4d65-8bd9-fa8052218ce8'
        print(f"\n🎯 Checking specific record from logs: {specific_id}")
        print("="*80)
        
        specific_result = supabase.table('script_results')\
            .select('*')\
            .eq('id', specific_id)\
            .execute()
        
        if specific_result.data:
            record = specific_result.data[0]
            print("✅ Record found!")
            print(f"  Script: {record['script_name']}")
            print(f"  Success: {record['success']}")
            print(f"  Started: {record['started_at']}")
            print(f"  Metadata: {record.get('metadata')}")
        else:
            print("❌ Specific record NOT found!")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    check_dns_data()

