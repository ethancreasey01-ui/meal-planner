#!/usr/bin/env python3
"""Quick test to see what Woolworths returns"""

from playwright.sync_api import sync_playwright
import re

url = "https://www.woolworths.com.au/shop/productdetails/669379/coca-cola-zero-sugar-soft-drink-multipack-cans"

print("Testing Woolworths scraping...")
print(f"URL: {url}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    )
    page = context.new_page()
    
    print("Loading page...")
    page.goto(url, wait_until='networkidle', timeout=30000)
    
    title = page.title()
    print(f"Page title: {title}")
    
    # Check for blocking
    content = page.content()
    if 'captcha' in content.lower() or 'verify' in content.lower():
        print("\n❌ BLOCKED - Captcha or verification required")
    else:
        print("\n✓ Page loaded (no obvious blocking)")
    
    # Try to find price
    print("\nSearching for price...")
    
    # Look for dollar amounts in the page
    matches = re.findall(r'\$([\d]+\.\d{2})', content)
    prices = [float(p) for p in matches if 0.5 < float(p) < 100]
    
    if prices:
        print(f"Found prices: {prices[:10]}")  # First 10
    else:
        print("No prices found in page content")
    
    # Check specific selectors
    selectors = [
        '[data-testid="price"]',
        '[class*="price"]',
        'h1',
        'h2',
        'h3'
    ]
    
    print("\nChecking selectors:")
    for sel in selectors:
        try:
            elem = page.locator(sel).first
            if elem and elem.is_visible():
                text = elem.text_content()[:100]  # First 100 chars
                print(f"  {sel}: {text}...")
        except Exception as e:
            print(f"  {sel}: Error - {e}")
    
    browser.close()

print("\nDone!")
