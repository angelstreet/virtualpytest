#!/usr/bin/env python3
"""
Test script to validate AI visual analysis of alert images

Tests the AI analyzer's ability to:
1. Access alert images from R2 storage
2. Analyze freeze/blackscreen screenshots visually
3. Make decisions based on visual content + metadata
"""

import sys
import os
from dotenv import load_dotenv

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

try:
    from ai_analyzer import SimpleAIAnalyzer
    from shared.src.lib.utils.supabase_utils import get_supabase_client
except ImportError as e:
    print(f"❌ Cannot import required modules: {e}")
    sys.exit(1)

def test_alert_visual_analysis():
    """Test visual analysis of real alert images"""
    print("🖼️  Testing Alert Visual Analysis")
    print("=" * 50)
    
    try:
        ai_analyzer = SimpleAIAnalyzer()
        supabase = get_supabase_client()
        
        # Get alerts with images
        result = supabase.table('alerts').select('*').order('created_at', desc=True).limit(5).execute()
        
        if not result.data:
            print("❌ No alerts found for testing")
            return False
        
        # Find alerts with images
        alerts_with_images = []
        for alert in result.data:
            metadata = alert.get('metadata', {})
            if ai_analyzer._alert_has_images(metadata):
                alerts_with_images.append(alert)
        
        if not alerts_with_images:
            print("❌ No alerts with images found")
            return False
        
        print(f"✅ Found {len(alerts_with_images)} alerts with images")
        
        # Test visual analysis on first alert
        test_alert = alerts_with_images[0]
        alert_id = test_alert.get('id')
        incident_type = test_alert.get('incident_type')
        metadata = test_alert.get('metadata', {})
        
        print(f"\n📋 Testing Visual Analysis:")
        print(f"   🆔 Alert ID: {alert_id}")
        print(f"   🚨 Type: {incident_type}")
        
        # Show available images
        r2_images = metadata.get('r2_images', {})
        thumbnail_urls = r2_images.get('thumbnail_urls', [])
        original_urls = r2_images.get('original_urls', [])
        
        print(f"   🖼️  Available Images:")
        for i, url in enumerate(thumbnail_urls[:3]):
            print(f"      Thumbnail {i+1}: {url}")
        
        # Test image access
        if thumbnail_urls:
            test_image_url = thumbnail_urls[0]
            print(f"\n🔍 Testing Image Access:")
            print(f"   📥 Downloading: {test_image_url[:60]}...")
            
            image_b64 = ai_analyzer._image_to_base64(test_image_url)
            if image_b64:
                print(f"   ✅ Successfully downloaded and encoded image ({len(image_b64)} chars)")
                
                # Test visual analysis
                print(f"\n🤖 Running Visual Analysis...")
                visual_result = ai_analyzer._analyze_alert_with_images(test_alert)
                
                if visual_result.success:
                    print(f"   ✅ Visual Analysis completed:")
                    print(f"      • Discard Decision: {visual_result.discard}")
                    print(f"      • Category: {visual_result.category}")
                    print(f"      • Confidence: {visual_result.confidence:.2f}")
                    print(f"      • Visual Explanation: {visual_result.explanation}")
                    
                    # Compare with text-only analysis
                    print(f"\n📊 Comparison with Text-Only Analysis:")
                    text_prompt = ai_analyzer._create_alert_analysis_prompt(test_alert)
                    text_result = ai_analyzer._call_text_ai(text_prompt)
                    
                    if text_result.success:
                        print(f"   Text-Only Decision: {text_result.discard}")
                        print(f"   Visual Decision: {visual_result.discard}")
                        
                        if text_result.discard == visual_result.discard:
                            print(f"   ✅ Both analyses agree!")
                        else:
                            print(f"   ⚠️  Analyses disagree - visual analysis may provide better insight")
                    
                    return True
                else:
                    print(f"   ❌ Visual analysis failed: {visual_result.error}")
                    return False
            else:
                print(f"   ❌ Failed to download/encode image")
                return False
        else:
            print(f"   ❌ No thumbnail URLs available")
            return False
            
    except Exception as e:
        print(f"❌ Visual analysis test failed: {e}")
        return False

def main():
    """Run visual analysis test"""
    print("🧪 Alert Visual Analysis Test Suite")
    print("=" * 50)
    
    # Verify API key
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found")
        return 1
    
    print(f"✅ OpenRouter API key loaded")
    
    # Run visual analysis test
    success = test_alert_visual_analysis()
    
    print(f"\n" + "=" * 50)
    if success:
        print("🎉 Alert visual analysis is working!")
        print("✨ The AI can now analyze alert screenshots to improve accuracy")
    else:
        print("❌ Alert visual analysis needs fixes")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
