#!/usr/bin/env python3
"""
Hybrid Price Scraper - Tries automatic, falls back to manual
"""

from flask import Flask, jsonify, request
import json
import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
import time
import re

app = Flask(__name__)

CACHE_FILE = '/Users/adbiptuy/clawd/meal-planner/prices_cache.json'

# Product definitions
PRODUCTS = {
    'coke-zero': {'name': 'Coke Zero 10 Pack', 'category': 'drinks'},
    'eggs': {'name': 'Free Range Eggs 12pk', 'category': 'dairy'},
    'milk': {'name': 'Full Cream Milk 2L', 'category': 'dairy'},
    'bread': {'name': 'White Bread', 'category': 'bakery'},
    'bananas': {'name': 'Bananas (per kg)', 'category': 'produce'},
    'chicken-breast': {'name': 'Chicken Breast (per kg)', 'category': 'meat'},
    'pasta': {'name': 'Spaghetti Pasta 500g', 'category': 'pantry'},
    'yogurt': {'name': 'Greek Yogurt', 'category': 'dairy'}
}

# Woolworths product URLs
WOOLIES_URLS = {
    'coke-zero': 'https://www.woolworths.com.au/shop/productdetails/669379/coca-cola-zero-sugar-soft-drink-multipack-cans',
    'eggs': 'https://www.woolworths.com.au/shop/productdetails/731079/cage-free-eggs-12-pack',
    'milk': 'https://www.woolworths.com.au/shop/productdetails/134593/woolworths-full-cream-milk',
    'bread': 'https://www.woolworths.com.au/shop/productdetails/743223/woolworths-white-sandwich-bread',
    'bananas': 'https://www.woolworths.com.au/shop/productdetails/133211/bananas',
    'chicken-breast': 'https://www.woolworths.com.au/shop/productdetails/721121/woolworths-chicken-breast-fillet',
    'pasta': 'https://www.woolworths.com.au/shop/productdetails/723538/woolworths-spaghetti-pasta',
    'yogurt': 'https://www.woolworths.com.au/shop/productdetails/666530/chobani-fit-high-protein-greek-yoghurt'
}

# Coles product URLs
COLES_URLS = {
    'coke-zero': 'https://www.coles.com.au/product/coca-cola-zero-sugar-soft-drink-multipack-cans-10x375ml-7502850',
    'eggs': 'https://www.coles.com.au/product/coles-free-range-eggs-12-pack-700g-7609829',
    'milk': 'https://www.coles.com.au/product/coles-full-cream-milk-2l-72717',
    'bread': 'https://www.coles.com.au/product/coles-white-sandwich-bread-700g-72725',
    'bananas': 'https://www.coles.com.au/product/fresh-bananas-approx-180g-each-317465',
    'chicken-breast': 'https://www.coles.com.au/product/coles-chicken-breast-fillet-approx-500g-220617',
    'pasta': 'https://www.coles.com.au/product/coles-spaghetti-500g-72711',
    'yogurt': 'https://www.coles.com.au/product/chobani-fit-high-protein-greek-yoghurt-850g-5433123'
}

# Default/demo prices
DEFAULT_PRICES = {
    'coke-zero': {'coles': 11.00, 'woolies': 11.00, 'special_coles': True, 'special_woolies': False},
    'eggs': {'coles': 5.50, 'woolies': 5.90, 'special_coles': False, 'special_woolies': False},
    'milk': {'coles': 3.50, 'woolies': 3.50, 'special_coles': False, 'special_woolies': True},
    'bread': {'coles': 2.50, 'woolies': 2.50, 'special_coles': False, 'special_woolies': False},
    'bananas': {'coles': 3.90, 'woolies': 3.50, 'special_coles': True, 'special_woolies': False},
    'chicken-breast': {'coles': 12.00, 'woolies': 13.50, 'special_coles': True, 'special_woolies': False},
    'pasta': {'coles': 1.40, 'woolies': 1.40, 'special_coles': False, 'special_woolies': True},
    'yogurt': {'coles': 6.50, 'woolies': 6.50, 'special_coles': False, 'special_woolies': False}
}

def load_cache():
    """Load cached prices"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {'timestamp': None, 'prices': {}, 'manual': False}

def save_cache(data):
    """Save prices to cache"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def scrape_with_playwright(url, store_name):
    """Try to scrape a single product page"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            page.goto(url, wait_until='networkidle', timeout=20000)
            time.sleep(2)
            
            title = page.title()
            if 'Access Denied' in title or 'blocked' in title.lower():
                browser.close()
                return {'error': 'BLOCKED', 'message': f'{store_name} blocked the scraper'}
            
            # Try to find price
            content = page.content()
            matches = re.findall(r'\$([\d]+\.\d{2})', content)
            prices = [float(p) for p in matches if 0.5 < float(p) < 200]
            
            browser.close()
            
            if prices:
                return {'price': min(prices), 'source': 'scraped'}
            else:
                return {'error': 'NO_PRICE', 'message': 'Could not find price'}
                
    except Exception as e:
        return {'error': 'EXCEPTION', 'message': str(e)}

def update_prices():
    """Try to update all prices automatically"""
    print(f"\n[{datetime.now()}] Starting automatic price update...")
    print("="*60)
    
    cache = load_cache()
    results = {
        'timestamp': datetime.now().isoformat(),
        'coles': {},
        'woolworths': {},
        'status': {
            'coles_blocked': False,
            'woolies_blocked': False,
            'items_scraped': 0,
            'method': 'automatic'
        }
    }
    
    # Try Woolworths
    print("\n🟢 Trying Woolworths...")
    woolies_blocked = False
    for product_id, product_info in PRODUCTS.items():
        url = WOOLIES_URLS.get(product_id)
        if not url:
            continue
            
        print(f"  Scraping {product_info['name']}...", end=' ')
        result = scrape_with_playwright(url, 'Woolworths')
        
        if 'error' in result:
            print(f"FAILED: {result.get('message', 'Unknown error')}")
            if result.get('error') == 'BLOCKED':
                woolies_blocked = True
                break  # Stop trying if blocked
        else:
            print(f"SUCCESS: ${result['price']:.2f}")
            results['woolworths'][product_id] = {
                'name': product_info['name'],
                'price': result['price'],
                'special': False,
                'store': 'woolworths'
            }
            results['status']['items_scraped'] += 1
        
        time.sleep(1)
    
    # Try Coles
    print("\n🟡 Trying Coles...")
    coles_blocked = False
    for product_id, product_info in PRODUCTS.items():
        url = COLES_URLS.get(product_id)
        if not url:
            continue
            
        print(f"  Scraping {product_info['name']}...", end=' ')
        result = scrape_with_playwright(url, 'Coles')
        
        if 'error' in result:
            print(f"FAILED: {result.get('message', 'Unknown error')}")
            if result.get('error') == 'BLOCKED':
                coles_blocked = True
                break
        else:
            print(f"SUCCESS: ${result['price']:.2f}")
            results['coles'][product_id] = {
                'name': product_info['name'],
                'price': result['price'],
                'special': False,
                'store': 'coles'
            }
            results['status']['items_scraped'] += 1
        
        time.sleep(1)
    
    results['status']['woolies_blocked'] = woolies_blocked
    results['status']['coles_blocked'] = coles_blocked
    
    # If nothing was scraped, use defaults
    if results['status']['items_scraped'] == 0:
        print("\n⚠️  All scraping failed - using demo prices")
        results = add_demo_prices(results)
        results['status']['method'] = 'demo'
    
    print("\n" + "="*60)
    print(f"Update complete: {results['status']['items_scraped']} items scraped")
    print(f"Woolies blocked: {woolies_blocked}, Coles blocked: {coles_blocked}")
    
    save_cache(results)
    return results

def add_demo_prices(results):
    """Add demo prices when scraping fails"""
    for product_id, product_info in PRODUCTS.items():
        defaults = DEFAULT_PRICES.get(product_id, {})
        
        if product_id not in results['coles']:
            results['coles'][product_id] = {
                'name': product_info['name'],
                'price': defaults.get('coles', 0),
                'special': defaults.get('special_coles', False),
                'store': 'coles',
                'demo': True
            }
        
        if product_id not in results['woolworths']:
            results['woolworths'][product_id] = {
                'name': product_info['name'],
                'price': defaults.get('woolies', 0),
                'special': defaults.get('special_woolies', False),
                'store': 'woolworths',
                'demo': True
            }
    
    return results

@app.route('/api/prices', methods=['GET'])
def get_prices():
    """Get current prices"""
    cache = load_cache()
    
    # Return cached if fresh (< 1 hour)
    if cache.get('timestamp'):
        cache_time = datetime.fromisoformat(cache['timestamp'])
        if datetime.now() - cache_time < timedelta(hours=1):
            return jsonify(cache)
    
    # Try to update
    return jsonify(update_prices())

@app.route('/api/prices/refresh', methods=['POST'])
def refresh_prices():
    """Force refresh prices"""
    return jsonify(update_prices())

@app.route('/api/prices/manual', methods=['POST'])
def save_manual_prices():
    """Save manually entered prices"""
    data = request.json
    
    cache = load_cache()
    cache['timestamp'] = datetime.now().isoformat()
    cache['manual'] = True
    cache['manual_timestamp'] = datetime.now().isoformat()
    
    # Update prices from manual input
    for store in ['coles', 'woolworths']:
        if store in data:
            for product_id, price_data in data[store].items():
                cache[store][product_id] = {
                    'name': price_data.get('name', PRODUCTS.get(product_id, {}).get('name', product_id)),
                    'price': price_data.get('price', 0),
                    'special': price_data.get('special', False),
                    'store': store,
                    'manual': True
                }
    
    save_cache(cache)
    return jsonify({'status': 'saved', 'prices': cache})

@app.route('/api/prices/status', methods=['GET'])
def get_status():
    """Get scraper status"""
    cache = load_cache()
    
    if not cache.get('timestamp'):
        return jsonify({'status': 'no_data', 'message': 'No prices available'})
    
    cache_time = datetime.fromisoformat(cache['timestamp'])
    age = datetime.now() - cache_time
    
    return jsonify({
        'status': 'ok' if age < timedelta(hours=2) else 'stale',
        'last_update': cache.get('timestamp'),
        'age_minutes': age.total_seconds() / 60,
        'method': cache.get('status', {}).get('method', 'unknown'),
        'is_manual': cache.get('manual', False),
        'coles_items': len(cache.get('coles', {})),
        'woolies_items': len(cache.get('woolworths', {}))
    })

if __name__ == '__main__':
    print("🛒 Hybrid Price Scraper starting on http://localhost:5002")
    print("Features:")
    print("  - Tries automatic scraping first")
    print("  - Falls back to demo prices if blocked")
    print("  - Supports manual price entry via API")
    print("")
    print("API Endpoints:")
    print("  GET  /api/prices         - Get current prices")
    print("  POST /api/prices/refresh - Force refresh (try scraping)")
    print("  POST /api/prices/manual  - Save manual prices")
    print("  GET  /api/prices/status  - Check status")
    print("")
    
    app.run(debug=True, port=5002, host='0.0.0.0')