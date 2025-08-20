#!/usr/bin/env python3
"""
Simple Playwright test script to isolate navigation behavior.

This script:
1. Initializes the Playwright web controller
2. Connects to browser (launches if needed)
3. Navigates to sunrisetv.ch
4. Prints detailed results
5. Closes the browser

Usage: python test_scripts/playwright_test.py
"""

import sys
import os
import time

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import Playwright controller
from backend_core.src.controllers.web.playwright import PlaywrightWebController

def test_playwright_navigation():
    print("🚀 Starting Playwright navigation test...")
    
    # Initialize controller
    controller = PlaywrightWebController()
    
    # Step 1: Connect to browser
    print("\n=== Step 1: Connecting to browser ===")
    connect_result = controller.connect_browser()
    print(f"Connect result: {connect_result}")
    
    if not connect_result.get('success'):
        print("❌ Browser connection failed!")
        return
    
    # Step 2: Navigate to URL
    print("\n=== Step 2: Navigating to https://www.sunrisetv.ch/en/home ===")
    nav_result = controller.navigate_to_url(
        url='https://www.sunrisetv.ch/en/home',
        timeout=60000  # 60 seconds
    )
    print(f"Navigation result: {nav_result}")
    
    if nav_result.get('success'):
        print("✅ Navigation succeeded!")
        print(f"Current URL: {nav_result.get('url')}")
        print(f"Page Title: {nav_result.get('title')}")
        print(f"Execution Time: {nav_result.get('execution_time')}ms")
    else:
        print("❌ Navigation failed!")
        print(f"Error: {nav_result.get('error')}")
    
    # Pause to observe the browser (10 seconds)
    print("\nPausing for 10 seconds to observe the browser...")
    time.sleep(10)
    
    # Step 3: Close browser
    print("\n=== Step 3: Closing browser ===")
    close_result = controller.close_browser()
    print(f"Close result: {close_result}")
    
    if close_result.get('success'):
        print("✅ Browser closed successfully!")
    else:
        print("❌ Browser close failed!")

if __name__ == "__main__":
    test_playwright_navigation()