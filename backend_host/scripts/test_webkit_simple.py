#!/usr/bin/env python3
"""Simple test of webkit_utils.py - does it work?"""

import sys
sys.path.insert(0, '/app/src')

from lib.utils.webkit_utils import WebKitUtils

print("="*60)
print("TESTING webkit_utils.py")
print("="*60)

# Create instance
utils = WebKitUtils(debug_port=9223)

# Launch chromium
print("\n1. Launching chromium...")
process = utils.launch_webkit()

# Try to connect
print("\n2. Connecting to chromium...")
import asyncio

async def test_connect():
    try:
        playwright, browser, context, page = await utils.connect_to_webkit()
        print("✓ CONNECTION SUCCESS!")
        print(f"  Browser: {browser}")
        print(f"  Contexts: {len(browser.contexts)}")
        print(f"  Pages: {len(context.pages)}")
        
        # Navigate to test page
        print("\n3. Testing navigation...")
        await page.goto("https://example.com", timeout=10000)
        title = await page.title()
        print(f"✓ PAGE LOADED: {title}")
        
        # Close
        await browser.close()
        await playwright.stop()
        print("\n✓ TEST PASSED!")
        return True
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

success = asyncio.run(test_connect())

# Cleanup
utils.kill_chrome(process)

print("="*60)
if success:
    print("RESULT: SUCCESS")
    sys.exit(0)
else:
    print("RESULT: FAILED")
    sys.exit(1)

