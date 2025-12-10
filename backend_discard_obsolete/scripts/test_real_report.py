#!/usr/bin/env python3
"""
Test script to validate AI analysis of real HTML reports

Tests the AI analyzer against actual report URLs to ensure it can:
1. Fetch and parse HTML reports correctly
2. Extract step-by-step execution details
3. Make proper discard decisions based on real data
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
except ImportError as e:
    print(f"❌ Cannot import AI analyzer: {e}")
    sys.exit(1)

def test_real_report_analysis():
    """Test AI analysis with real report URL from your example"""
    print("🧪 Testing AI Analysis with Real HTML Report")
    print("=" * 70)
    
    try:
        ai_analyzer = SimpleAIAnalyzer()
        
        # Real test case from your example
        real_script_data = {
            'id': 'test-goto-real',
            'script_name': 'goto',
            'script_type': 'navigation',
            'userinterface_name': 'horizon_android_mobile',
            'device_name': 'S21x',
            'host_name': 'sunri-pi1',
            'success': True,  # Report shows PASS
            'error_msg': None,
            'execution_time_ms': 49400,  # 49.4s from report
            'html_report_r2_url': 'https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/android_mobile/goto_20250817_20250817215853/report.html',
            'started_at': '2025-08-17T21:58:06Z',
            'completed_at': '2025-08-17T21:58:53Z'
        }
        
        print(f"📋 Test Case: Real goto script execution")
        print(f"   🎯 Script: {real_script_data['script_name']}")
        print(f"   📱 Device: {real_script_data['device_name']}")
        print(f"   ✅ Status: {'PASSED' if real_script_data['success'] else 'FAILED'}")
        print(f"   ⏱️  Duration: {real_script_data['execution_time_ms']/1000:.1f}s")
        print(f"   📊 Report: {real_script_data['html_report_r2_url'][:50]}...")
        
        # Test HTML report fetching first
        print(f"\n🔍 Testing HTML Report Fetching...")
        if ai_analyzer._is_valid_report_url(real_script_data['html_report_r2_url']):
            print(f"   ✅ Report URL is valid")
            
            report_content = ai_analyzer._fetch_report_content(real_script_data['html_report_r2_url'])
            if report_content:
                print(f"   ✅ Successfully fetched report ({len(report_content)} chars)")
                print(f"   📄 Report preview:")
                print(f"      {report_content[:300]}...")
            else:
                print(f"   ❌ Failed to fetch report content")
                return False
        else:
            print(f"   ❌ Invalid report URL")
            return False
        
        # Show the exact prompt that will be sent to AI
        print(f"\n📝 Generating AI Prompt...")
        ai_prompt = ai_analyzer._create_script_analysis_prompt(real_script_data, report_content)
        print(f"   📏 Prompt length: {len(ai_prompt)} characters")
        print(f"   📋 Prompt preview (first 500 chars):")
        print(f"      {ai_prompt[:500]}...")
        
        # Save full prompt to file for inspection
        prompt_file = os.path.join(current_dir, 'last_ai_prompt.txt')
        with open(prompt_file, 'w') as f:
            f.write("=== FULL AI PROMPT FOR REAL REPORT ANALYSIS ===\n\n")
            f.write(ai_prompt)
        print(f"   💾 Full prompt saved to: {prompt_file}")
        
        # Run full AI analysis
        print(f"\n🤖 Running AI Analysis...")
        result = ai_analyzer._analyze_text_only(real_script_data)
        
        if result.success:
            print(f"   ✅ AI Analysis completed successfully:")
            print(f"      • Discard Decision: {result.discard}")
            print(f"      • Category: {result.category}")
            print(f"      • Confidence: {result.confidence:.2f}")
            print(f"      • Explanation: {result.explanation}")
            
            # Validate the decision
            print(f"\n📊 Analysis Validation:")
            if real_script_data['success'] and result.discard:
                print(f"   ⚠️  WARNING: Successful script was marked for discard!")
                print(f"      This might indicate an issue with the AI prompt.")
                return False
            elif real_script_data['success'] and not result.discard:
                print(f"   ✅ CORRECT: Successful script was kept (not discarded)")
                return True
            elif not real_script_data['success'] and result.discard:
                print(f"   ✅ CORRECT: Failed script was appropriately discarded as false positive")
                return True
            elif not real_script_data['success'] and not result.discard:
                print(f"   ✅ CORRECT: Failed script was kept as valid failure")
                return True
            
        else:
            print(f"   ❌ AI Analysis failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def test_report_parsing_details():
    """Test detailed parsing of the HTML report"""
    print(f"\n🔬 Testing Detailed HTML Report Parsing")
    print("=" * 50)
    
    try:
        ai_analyzer = SimpleAIAnalyzer()
        report_url = 'https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/android_mobile/goto_20250817_20250817215853/report.html'
        
        # Test HTML parsing methods
        print(f"📥 Fetching report content...")
        html_content = ai_analyzer._fetch_report_content(report_url)
        
        if html_content:
            print(f"✅ Report fetched successfully ({len(html_content)} characters)")
            
            # Check what specific elements were extracted
            print(f"\n🔍 Parsed Content Analysis:")
            
            # Look for key elements that should be in the parsed content
            key_elements = [
                ('Status', 'PASS'),
                ('Duration', '49.4s'),
                ('Device', 'S21x'),
                ('Host', 'sunri-pi1'),
                ('Steps', '1/1'),
                ('Target', 'home'),
                ('Action', 'click_element'),
                ('Verification', 'waitForElementToAppear'),
                ('Home Tab', 'Home Tab')
            ]
            
            found_elements = []
            for element_name, search_term in key_elements:
                if search_term.lower() in html_content.lower():
                    found_elements.append(element_name)
                    print(f"   ✅ Found {element_name}: '{search_term}'")
                else:
                    print(f"   ❌ Missing {element_name}: '{search_term}'")
            
            print(f"\n📊 Parsing Results:")
            print(f"   Found {len(found_elements)}/{len(key_elements)} key elements")
            
            if len(found_elements) >= 6:  # Should find most elements
                print(f"   ✅ Report parsing is working well")
                return True
            else:
                print(f"   ⚠️  Report parsing may need improvement")
                return False
                
        else:
            print(f"❌ Failed to fetch report content")
            return False
            
    except Exception as e:
        print(f"❌ Parsing test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Real HTML Report Analysis Test Suite")
    print("=" * 70)
    
    # Test detailed parsing first
    parsing_success = test_report_parsing_details()
    
    # Test full AI analysis
    analysis_success = test_real_report_analysis()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Results Summary:")
    print(f"   • HTML Report Parsing: {'✅ PASS' if parsing_success else '❌ FAIL'}")
    print(f"   • AI Analysis Logic: {'✅ PASS' if analysis_success else '❌ FAIL'}")
    
    overall_success = parsing_success and analysis_success
    print(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print(f"\n✨ The AI is ready to analyze real HTML reports!")
    else:
        print(f"\n🔧 The AI needs improvements to handle real reports properly.")
    
    return 0 if overall_success else 1

if __name__ == '__main__':
    sys.exit(main())
