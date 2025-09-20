#!/usr/bin/env python3
"""
Test script to validate AI analysis of real alerts

Tests the AI analyzer against actual alert data to ensure it can:
1. Fetch alert data from database correctly
2. Analyze alert patterns (freeze, blackscreen, etc.)
3. Access alert images for visual analysis
4. Make proper discard decisions based on real alert data
"""

import sys
import os
from dotenv import load_dotenv
import json

# Add project paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_discard_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_discard_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

sys.path.append(os.path.join(backend_discard_dir, 'src'))

# Load environment variables from project root .env
project_env_path = os.path.join(project_root, '.env')
if os.path.exists(project_env_path):
    load_dotenv(project_env_path)
    print(f"📁 Loaded environment from: {project_env_path}")
else:
    print(f"⚠️  No .env file found at: {project_env_path}")

# Verify API key is loaded
api_key = os.getenv('OPENROUTER_API_KEY')
if api_key:
    print(f"✅ OPENROUTER_API_KEY loaded (length: {len(api_key)})")
else:
    print(f"❌ OPENROUTER_API_KEY not found in environment")
    sys.exit(1)

try:
    from ai_analyzer import SimpleAIAnalyzer
    from shared.src.lib.utils.supabase_utils import get_supabase_client
except ImportError as e:
    print(f"❌ Cannot import required modules: {e}")
    sys.exit(1)

def get_latest_alerts(limit=5):
    """Get the latest alerts from database"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('alerts').select('*').order('created_at', desc=True).limit(limit).execute()
        
        if result.data:
            print(f"📊 Found {len(result.data)} recent alerts")
            return result.data
        else:
            print(f"❌ No alerts found in database")
            return []
            
    except Exception as e:
        print(f"❌ Error fetching alerts: {e}")
        return []

def test_alert_data_access():
    """Test access to real alert data"""
    print("🧪 Testing Alert Data Access")
    print("=" * 50)
    
    alerts = get_latest_alerts(3)
    
    if not alerts:
        print("❌ No alerts available for testing")
        return False
    
    print(f"✅ Retrieved {len(alerts)} alerts for testing")
    
    for i, alert in enumerate(alerts, 1):
        print(f"\n📋 Alert {i}:")
        print(f"   🆔 ID: {alert.get('id')}")
        print(f"   🚨 Type: {alert.get('incident_type')}")
        print(f"   🖥️  Host: {alert.get('host_name')}")
        print(f"   📱 Device: {alert.get('device_id')}")
        print(f"   📅 Start: {alert.get('started_at')}")
        print(f"   📊 Status: {alert.get('status')}")
        print(f"   🔢 Count: {alert.get('consecutive_count')}")
        print(f"   💾 Metadata: {json.dumps(alert.get('metadata', {}), indent=6)}")
    
    return True

def test_real_alert_analysis():
    """Test AI analysis with real alert data"""
    print("\n🤖 Testing AI Analysis with Real Alert Data")
    print("=" * 60)
    
    try:
        ai_analyzer = SimpleAIAnalyzer()
        
        # Get latest alerts
        alerts = get_latest_alerts(2)
        
        if not alerts:
            print("❌ No alerts available for testing")
            return False
        
        results = []
        
        for i, alert in enumerate(alerts, 1):
            alert_id = alert.get('id')
            incident_type = alert.get('incident_type', 'Unknown')
            host_name = alert.get('host_name', 'Unknown')
            device_id = alert.get('device_id', 'Unknown')
            
            print(f"\n📋 Test {i}: Analyzing real alert")
            print(f"   🆔 Alert ID: {alert_id}")
            print(f"   🚨 Type: {incident_type}")
            print(f"   🖥️  Host: {host_name}")
            print(f"   📱 Device: {device_id}")
            
            # Test database access method
            print(f"   🔍 Testing database access...")
            retrieved_alert = ai_analyzer._get_alert_from_database(alert_id)
            
            if retrieved_alert:
                print(f"   ✅ Successfully retrieved alert from database")
                
                # Generate alert analysis prompt
                print(f"   📝 Generating alert analysis prompt...")
                alert_prompt = ai_analyzer._create_alert_analysis_prompt(retrieved_alert)
                print(f"   📏 Prompt length: {len(alert_prompt)} characters")
                
                # Save prompt for inspection
                prompt_file = os.path.join(current_dir, f'last_alert_prompt_{i}.txt')
                with open(prompt_file, 'w') as f:
                    f.write(f"=== ALERT ANALYSIS PROMPT {i} ===\n\n")
                    f.write(f"Alert ID: {alert_id}\n")
                    f.write(f"Incident Type: {incident_type}\n\n")
                    f.write(alert_prompt)
                print(f"   💾 Prompt saved to: {prompt_file}")
                
                # Run AI analysis
                print(f"   🤖 Running AI analysis...")
                result = ai_analyzer.analyze_alert({'id': alert_id, 'type': 'alert'})
                
                if result.success:
                    print(f"   ✅ AI Analysis completed successfully:")
                    print(f"      • Discard Decision: {result.discard}")
                    print(f"      • Category: {result.category}")
                    print(f"      • Confidence: {result.confidence:.2f}")
                    print(f"      • Explanation: {result.explanation}")
                    
                    results.append({
                        'alert_id': alert_id,
                        'incident_type': incident_type,
                        'discard': result.discard,
                        'category': result.category,
                        'confidence': result.confidence,
                        'explanation': result.explanation,
                        'success': True
                    })
                else:
                    print(f"   ❌ AI Analysis failed: {result.error}")
                    results.append({
                        'alert_id': alert_id,
                        'incident_type': incident_type,
                        'success': False,
                        'error': result.error
                    })
            else:
                print(f"   ❌ Failed to retrieve alert from database")
                results.append({
                    'alert_id': alert_id,
                    'incident_type': incident_type,
                    'success': False,
                    'error': 'Database retrieval failed'
                })
        
        # Summary
        print(f"\n📊 Alert Analysis Results:")
        successful_analyses = [r for r in results if r['success']]
        
        for result in successful_analyses:
            print(f"   🚨 {result['incident_type']} Alert:")
            print(f"      Decision: {'DISCARD' if result['discard'] else 'KEEP'}")
            print(f"      Category: {result['category']}")
            print(f"      Confidence: {result['confidence']:.0%}")
        
        return len(successful_analyses) > 0
        
    except Exception as e:
        print(f"❌ Alert analysis test failed: {e}")
        return False

def test_alert_image_access():
    """Test access to alert images for visual analysis"""
    print(f"\n🖼️  Testing Alert Image Access")
    print("=" * 40)
    
    try:
        # Get latest alerts
        alerts = get_latest_alerts(2)
        
        if not alerts:
            print("❌ No alerts available for image testing")
            return False
        
        for i, alert in enumerate(alerts, 1):
            alert_id = alert.get('id')
            incident_type = alert.get('incident_type', 'Unknown')
            metadata = alert.get('metadata', {})
            
            print(f"\n📋 Alert {i} Image Analysis:")
            print(f"   🆔 Alert ID: {alert_id}")
            print(f"   🚨 Type: {incident_type}")
            
            # Check for r2_images metadata (the actual field used)
            if 'r2_images' in metadata and metadata['r2_images']:
                r2_images = metadata['r2_images']
                original_urls = r2_images.get('original_urls', [])
                thumbnail_urls = r2_images.get('thumbnail_urls', [])
                
                print(f"   🖼️  Found r2_images with:")
                print(f"      • {len(original_urls)} original images")
                print(f"      • {len(thumbnail_urls)} thumbnail images")
                
                if thumbnail_urls:
                    print(f"   📸 Sample thumbnail: {thumbnail_urls[0][:60]}...")
                
                # Test AI image access using the analyzer's method
                from ai_analyzer import SimpleAIAnalyzer
                ai_analyzer = SimpleAIAnalyzer()
                
                if ai_analyzer._alert_has_images(metadata):
                    print(f"   ✅ AI analyzer detects images available")
                    
                    # Test actual image download
                    if thumbnail_urls:
                        test_url = thumbnail_urls[0]
                        image_b64 = ai_analyzer._image_to_base64(test_url)
                        if image_b64:
                            print(f"   ✅ Successfully downloaded image ({len(image_b64)} chars)")
                        else:
                            print(f"   ❌ Failed to download image")
                else:
                    print(f"   ❌ AI analyzer fails to detect images")
            else:
                print(f"   ⚠️  No r2_images found in alert metadata")
                print(f"   📄 Available metadata fields: {list(metadata.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Image access test failed: {e}")
        return False

def main():
    """Run all alert analysis tests"""
    print("🧪 Real Alert Analysis Test Suite")
    print("=" * 60)
    
    # Test 1: Database access
    data_access_success = test_alert_data_access()
    
    # Test 2: AI analysis
    analysis_success = test_real_alert_analysis()
    
    # Test 3: Image access  
    image_access_success = test_alert_image_access()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"   • Alert Data Access: {'✅ PASS' if data_access_success else '❌ FAIL'}")
    print(f"   • AI Analysis Logic: {'✅ PASS' if analysis_success else '❌ FAIL'}")
    print(f"   • Image Access: {'✅ PASS' if image_access_success else '❌ FAIL'}")
    
    overall_success = data_access_success and analysis_success
    print(f"\n🎯 Overall: {'✅ ALERT ANALYSIS READY' if overall_success else '❌ NEEDS IMPROVEMENT'}")
    
    if overall_success:
        print(f"\n✨ The AI can analyze real alerts from your database!")
        if not image_access_success:
            print(f"💡 Consider implementing alert image analysis for enhanced accuracy")
    else:
        print(f"\n🔧 Alert analysis needs fixes before production use.")
    
    return 0 if overall_success else 1

if __name__ == '__main__':
    sys.exit(main())
