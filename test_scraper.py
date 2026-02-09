#!/usr/bin/env python3
"""
Coles & Woolworths Price Scraper - TEST VERSION
Shows exactly what's happening when scraping
"""

from playwright.sync_api import sync_playwright
import re
import time

WOOLIES_COKE_URL = "https://www.woolworths.com.au/shop/productdetails/669379/coca-cola-zero-sugar-soft-drink-multipack-cans"

def test_woolworths():
    """Test scraping Woolworths product page"""
    print("\n" + "="*60)
    print("Testing Woolworths Price Scraping")
    print("="*60)
    print(f"URL: {WOOLIES_COKE_URL}")
    print("")
    
    with sync_playwright() as p:
        print("1. Launching browser...")
        browser = p.chromium.launch(
            headless=False,  # Visible so you can see what's happening
            slow_mo=500  # Slow down to see actions
        )
        
        print("2. Creating context with stealth settings...")
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='en-AU',
            timezone_id='Australia/Sydney'
        )
        
        page = context.new_page()
        
        print("3. Navigating to product page...")
        try:
            page.goto(WOOLIES_COKE_URL, wait_until='networkidle', timeout=30000)
            print(f"   ✓ Page loaded: {page.title()}")
        except Exception as e:
            print(f"   ✗ Failed to load: {e}")
            browser.close()
            return
        
        # Wait a bit for JavaScript to render
        print("4. Waiting for JavaScript to render...")
        time.sleep(3)
        
        # Take a screenshot
        print("5. Taking screenshot...")
        page.screenshot(path='/tmp/woolworths_test.png', full_page=False)
        print("   ✓ Screenshot saved to /tmp/woolworths_test.png")
        
        # Try to find price with multiple selectors
        print("\n6. Searching for price...")
        price_selectors = [
            '[data-testid="price"]',
            '[class*="price"]',
            'span[class*="dollar"]',
            'div[class*="price-section"]',
            '[class*="product-price"]',
            'h3',  # Sometimes price is in a heading
            'span:has-text("$")',  # Any span with $
        ]
        
        found_price = None
        for selector in price_selectors:
            try:
                elements = page.locator(selector).all()
                print(f"\n   Selector: {selector}")
                print(f"   Found {len(elements)} elements")
                
                for i, elem in enumerate(elements[:3]):  # Check first 3
                    try:
                        if elem.is_visible():
                            text = elem.text_content()
                            if text and '$' in text:
                                print(f"   [{i}] Text: {text.strip()}")
                                # Extract price
                                matches = re.findall(r'\$([\d]+\.\d{2})', text)
                                if matches:
                                    price = float(matches[0])
                                    if 0.5 < price < 200:
                                        found_price = price
                                        print(f"   ✓✓✓ PRICE FOUND: ${price:.2f}")
                                        break
                    except:
                        pass
                
                if found_price:
                    break
                    
            except Exception as e:
                print(f"   Error: {e}")
        
        # Check for bot detection
        print("\n7. Checking for bot detection...")
        page_text = page.content().lower()
        if any(x in page_text for x in ['captcha', 'verify you are human', 'robot', 'bot detected']):
            print("   ✗ BOT DETECTED!")
        else:
            print("   ✓ No obvious bot detection message")
        
        # Look for the actual product data in page source
        print("\n8. Searching page source for price data...")
        content = page.content()
        
        # Look for JSON price data
        price_patterns = [
            r'"price":\s*"?([\d.]+)"?',
            r'"Price":\s*"?([\d.]+)"?',
            r'"priceAmount":\s*"?([\d.]+)"?',
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, content)
            if matches:
                print(f"   Pattern '{pattern}': {matches[:5]}")  # First 5 matches
        
        print("\n9. Keeping browser open for 10 seconds...")
        print("   Check the browser window!")
        time.sleep(10)
        
        browser.close()
        print("\n" + "="*60)
        if found_price:
            print(f"SUCCESS! Price found: ${found_price:.2f}")
        else:
            print("FAILED - Could not extract price automatically")
        print("="*60 + "\n")

if __name__ == '__main__':
    test_woolworths()
