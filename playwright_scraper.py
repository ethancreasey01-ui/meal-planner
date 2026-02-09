#!/usr/bin/env python3
"""
Coles & Woolworths Price Scraper using Playwright
Handles JavaScript-rendered pages for accurate price extraction
"""

from flask import Flask, jsonify
import json
import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
import time

app = Flask(__name__)

# Cache file path
CACHE_FILE = '/Users/adbiptuy/clawd/meal-planner/prices_cache.json'

# Product URLs - these should remain consistent
WOOLWORTHS_PRODUCTS = {
    'coke-zero': {
        'name': 'Coke Zero 10 Pack',
        'url': 'https://www.woolworths.com.au/shop/productdetails/669379/coca-cola-zero-sugar-soft-drink-multipack-cans',
        'category': 'drinks'
    },
    'eggs': {
        'name': 'Free Range Eggs 12pk',
        'url': 'https://www.woolworths.com.au/shop/productdetails/731079/cage-free-eggs-12-pack',
        'category': 'dairy'
    },
    'milk': {
        'name': 'Full Cream Milk 2L',
        'url': 'https://www.woolworths.com.au/shop/productdetails/134593/woolworths-full-cream-milk',
        'category': 'dairy'
    },
    'bread': {
        'name': 'White Bread',
        'url': 'https://www.woolworths.com.au/shop/productdetails/743223/woolworths-white-sandwich-bread',
        'category': 'bakery'
    },
    'bananas': {
        'name': 'Bananas',
        'url': 'https://www.woolworths.com.au/shop/productdetails/133211/bananas',
        'category': 'produce'
    },
    'chicken-breast': {
        'name': 'Chicken Breast',
        'url': 'https://www.woolworths.com.au/shop/productdetails/721121/woolworths-chicken-breast-fillet',
        'category': 'meat'
    },
    'pasta': {
        'name': 'Spaghetti Pasta',
        'url': 'https://www.woolworths.com.au/shop/productdetails/723538/woolworths-spaghetti-pasta',
        'category': 'pantry'
    },
    'yogurt': {
        'name': 'Greek Yogurt',
        'url': 'https://www.woolworths.com.au/shop/productdetails/666530/chobani-fit-high-protein-greek-yoghurt',
        'category': 'dairy'
    }
}

COLES_PRODUCTS = {
    'coke-zero': {
        'name': 'Coke Zero 10 Pack',
        'url': 'https://www.coles.com.au/product/coca-cola-zero-sugar-soft-drink-multipack-cans-10x375ml-7502850',
        'category': 'drinks'
    },
    'eggs': {
        'name': 'Free Range Eggs 12pk',
        'url': 'https://www.coles.com.au/product/coles-free-range-eggs-12-pack-700g-7609829',
        'category': 'dairy'
    },
    'milk': {
        'name': 'Full Cream Milk 2L',
        'url': 'https://www.coles.com.au/product/coles-full-cream-milk-2l-72717',
        'category': 'dairy'
    },
    'bread': {
        'name': 'White Bread',
        'url': 'https://www.coles.com.au/product/coles-white-sandwich-bread-700g-72725',
        'category': 'bakery'
    },
    'bananas': {
        'name': 'Bananas',
        'url': 'https://www.coles.com.au/product/fresh-bananas-approx-180g-each-317465',
        'category': 'produce'
    },
    'chicken-breast': {
        'name': 'Chicken Breast',
        'url': 'https://www.coles.com.au/product/coles-chicken-breast-fillet-approx-500g-220617',
        'category': 'meat'
    },
    'pasta': {
        'name': 'Spaghetti Pasta',
        'url': 'https://www.coles.com.au/product/coles-spaghetti-500g-72711',
        'category': 'pantry'
    },
    'yogurt': {
        'name': 'Greek Yogurt',
        'url': 'https://www.coles.com.au/product/chobani-fit-high-protein-greek-yoghurt-850g-5433123',
        'category': 'dairy'
    }
}

def load_cached_prices():
    """Load prices from cache file"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cached_prices(prices):
    """Save prices to cache file"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(prices, f, indent=2)

def scrape_woolworths_price(product_id, product_info):
    """Scrape price from Woolworths product page using Playwright"""
    print(f"[Woolworths] Scraping {product_info['name']}...")
    
    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            # Navigate to product page
            page.goto(product_info['url'], wait_until='networkidle', timeout=30000)
            
            # Wait for price element to load
            page.wait_for_timeout(2000)  # Give JavaScript time to render
            
            # Try to extract price
            price_data = {
                'name': product_info['name'],
                'price': 0,
                'special': False,
                'special_price': None,
                'store': 'woolworths',
                'url': product_info['url']
            }
            
            # Try multiple selectors for price
            price_selectors = [
                '[data-testid="price"]',
                '.price',
                '[class*="price"]',
                'span[class*="dollar"]',
                'div[class*="price-section"]',
                '[class*="product-price"]'
            ]
            
            for selector in price_selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible():
                        text = element.text_content()
                        print(f"  Found price text: {text}")
                        
                        # Extract dollar amount
                        import re
                        matches = re.findall(r'\$?([\d]+\.\d{2})', text)
                        if matches:
                            price = float(matches[0])
                            if 0.5 < price < 200:  # Reasonable price range
                                price_data['price'] = price
                                break
                except:
                    continue
            
            # Check for special/sale pricing
            try:
                # Look for was/now pricing or special badges
                special_selectors = [
                    '[class*="was-price"]',
                    '[class*="special-price"]',
                    '[class*="sale-price"]',
                    '[data-testid="was-price"]'
                ]
                
                for selector in special_selectors:
                    try:
                        element = page.locator(selector).first
                        if element.is_visible():
                            text = element.text_content()
                            matches = re.findall(r'\$?([\d]+\.\d{2})', text)
                            if matches:
                                original_price = float(matches[0])
                                if original_price > price_data['price']:
                                    price_data['special'] = True
                                    price_data['special_price'] = price_data['price']
                                    price_data['price'] = original_price
                                    break
                    except:
                        continue
                
                # Check for special badge
                badge_selectors = [
                    '[class*="special-badge"]',
                    '[class*="on-special"]',
                    '[data-testid*="badge"]'
                ]
                
                for selector in badge_selectors:
                    try:
                        if page.locator(selector).first.is_visible():
                            price_data['special'] = True
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"  Error checking special price: {e}")
            
            browser.close()
            
            if price_data['price'] > 0:
                print(f"  ✓ Price: ${price_data['price']:.2f} (Special: {price_data['special']})")
                return price_data
            else:
                print(f"  ✗ Could not extract price")
                return None
                
    except Exception as e:
        print(f"  ✗ Error scraping Woolworths: {e}")
        return None

def scrape_coles_price(product_id, product_info):
    """Scrape price from Coles product page using Playwright"""
    print(f"[Coles] Scraping {product_info['name']}...")
    
    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            # Navigate to product page
            page.goto(product_info['url'], wait_until='networkidle', timeout=30000)
            
            # Wait for price element to load
            page.wait_for_timeout(2000)  # Give JavaScript time to render
            
            # Try to extract price
            price_data = {
                'name': product_info['name'],
                'price': 0,
                'special': False,
                'special_price': None,
                'store': 'coles',
                'url': product_info['url']
            }
            
            # Try multiple selectors for price
            price_selectors = [
                '[data-testid="price"]',
                '.price',
                '[class*="price"]',
                'span[class*="dollar"]',
                '[class*="product-price"]'
            ]
            
            for selector in price_selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible():
                        text = element.text_content()
                        print(f"  Found price text: {text}")
                        
                        # Extract dollar amount
                        import re
                        matches = re.findall(r'\$?([\d]+\.\d{2})', text)
                        if matches:
                            price = float(matches[0])
                            if 0.5 < price < 200:  # Reasonable price range
                                price_data['price'] = price
                                break
                except:
                    continue
            
            # Check for special/sale pricing
            try:
                special_selectors = [
                    '[class*="was-price"]',
                    '[class*="special-price"]',
                    '[class*="down-down"]',
                    '[class*="member-price"]'
                ]
                
                for selector in special_selectors:
                    try:
                        element = page.locator(selector).first
                        if element.is_visible():
                            text = element.text_content()
                            matches = re.findall(r'\$?([\d]+\.\d{2})', text)
                            if matches:
                                original_price = float(matches[0])
                                if original_price > price_data['price']:
                                    price_data['special'] = True
                                    price_data['special_price'] = price_data['price']
                                    price_data['price'] = original_price
                                    break
                    except:
                        continue
                        
            except Exception as e:
                print(f"  Error checking special price: {e}")
            
            browser.close()
            
            if price_data['price'] > 0:
                print(f"  ✓ Price: ${price_data['price']:.2f} (Special: {price_data['special']})")
                return price_data
            else:
                print(f"  ✗ Could not extract price")
                return None
                
    except Exception as e:
        print(f"  ✗ Error scraping Coles: {e}")
        return None

def update_prices():
    """Update all prices using Playwright"""
    print(f"\n[{datetime.now()}] Starting Playwright price update...")
    print("="*60)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'coles': {},
        'woolworths': {},
        'status': {
            'coles_success': False,
            'woolies_success': False,
            'method': 'playwright'
        }
    }
    
    # Scrape Woolworths
    print("\n🟢 Woolworths:")
    woolies_success = 0
    for product_id, product_info in WOOLWORTHS_PRODUCTS.items():
        data = scrape_woolworths_price(product_id, product_info)
        if data:
            results['woolworths'][product_id] = data
            woolies_success += 1
        time.sleep(1)  # Be polite
    
    # Scrape Coles
    print("\n🟡 Coles:")
    coles_success = 0
    for product_id, product_info in COLES_PRODUCTS.items():
        data = scrape_coles_price(product_id, product_info)
        if data:
            results['coles'][product_id] = data
            coles_success += 1
        time.sleep(1)  # Be polite
    
    results['status']['coles_success'] = coles_success > 0
    results['status']['woolies_success'] = woolies_success > 0
    
    print("\n" + "="*60)
    print(f"Results: Coles {coles_success}/{len(COLES_PRODUCTS)}, Woolies {woolies_success}/{len(WOOLWORTHS_PRODUCTS)}")
    
    # Save to cache
    save_cached_prices(results)
    print(f"[{datetime.now()}] Prices saved to cache\n")
    
    return results

@app.route('/api/prices', methods=['GET'])
def get_prices():
    """Get current prices (from cache or fresh scrape)"""
    cache = load_cached_prices()
    
    # Check if cache is stale (older than 1 hour)
    if cache:
        cache_time = datetime.fromisoformat(cache.get('timestamp', '2000-01-01'))
        if datetime.now() - cache_time < timedelta(hours=1):
            return jsonify(cache)
    
    # Update prices
    return jsonify(update_prices())

@app.route('/api/prices/refresh', methods=['POST'])
def refresh_prices():
    """Force refresh of prices"""
    return jsonify(update_prices())

@app.route('/api/prices/status', methods=['GET'])
def get_status():
    """Get status of price scraping"""
    cache = load_cached_prices()
    
    if not cache:
        return jsonify({'status': 'no_data', 'message': 'No price data available'})
    
    cache_time = datetime.fromisoformat(cache.get('timestamp', '2000-01-01'))
    age = datetime.now() - cache_time
    
    return jsonify({
        'status': 'ok' if age < timedelta(hours=2) else 'stale',
        'last_update': cache.get('timestamp'),
        'age_minutes': age.total_seconds() / 60,
        'coles_items': len(cache.get('coles', {})),
        'woolies_items': len(cache.get('woolworths', {}))
    })

if __name__ == '__main__':
    print("🛒 Playwright Price Scraper starting on http://localhost:5002")
    print("Features:")
    print("  - Real browser automation with Playwright")
    print("  - JavaScript-rendered page scraping")
    print("  - Consistent product URLs")
    print("  - Automatic caching (1 hour refresh)")
    print("")
    print("API Endpoints:")
    print("  GET  /api/prices         - Get current prices")
    print("  POST /api/prices/refresh - Force refresh")
    print("  GET  /api/prices/status  - Check scraper status")
    print("")
    
    # Don't auto-scrape on startup - let user trigger it
    
    app.run(debug=True, port=5002, host='0.0.0.0')