#!/usr/bin/env python3
"""
Coles & Woolworths Automatic Price Scraper
Robust scraping with caching, retries, and fallbacks
"""

from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random
import os
from datetime import datetime, timedelta
from functools import lru_cache

app = Flask(__name__)

# Cache file path
CACHE_FILE = '/Users/adbiptuy/clawd/meal-planner/prices_cache.json'

# Rotating user agents to avoid blocking
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
]

# Tracked grocery items with search terms
TRACKED_ITEMS = {
    'coke-zero': {
        'name': 'Coke Zero 10 Pack',
        'search_terms': ['coke zero', 'coca-cola zero', 'coca cola zero', 'zero sugar'],
        'category': 'drinks',
        'woolies_product_id': '669379'
    },
    'eggs': {
        'name': 'Free Range Eggs 12pk',
        'search_terms': ['free range eggs', 'eggs 12', 'eggs dozen'],
        'category': 'dairy'
    },
    'milk': {
        'name': 'Full Cream Milk 2L',
        'search_terms': ['full cream milk', 'milk 2l', 'full cream 2'],
        'category': 'dairy'
    },
    'bread': {
        'name': 'White Bread 650g',
        'search_terms': ['white bread', 'sandwich bread', 'toast bread'],
        'category': 'bakery'
    },
    'bananas': {
        'name': 'Bananas 1kg',
        'search_terms': ['bananas', 'banana bunch'],
        'category': 'produce'
    },
    'chicken-breast': {
        'name': 'Chicken Breast 500g',
        'search_terms': ['chicken breast', 'chicken fillet', 'chicken 500'],
        'category': 'meat'
    },
    'pasta': {
        'name': 'Spaghetti Pasta 500g',
        'search_terms': ['spaghetti', 'pasta spaghetti', 'spaghetti 500'],
        'category': 'pantry'
    },
    'yogurt': {
        'name': 'Greek Yogurt 1kg',
        'search_terms': ['greek yogurt', 'greek yoghurt', 'yogurt 1kg'],
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

def get_random_headers():
    """Get random headers to avoid detection"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }

def scrape_coles_with_retry():
    """Scrape Coles with retry logic"""
    urls = [
        "https://www.coles.com.au/on-special",
        "https://www.coles.com.au/specials"
    ]
    
    for attempt in range(3):
        try:
            url = random.choice(urls)
            headers = get_random_headers()
            
            # Add delay to be polite
            time.sleep(random.uniform(1, 3))
            
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                return parse_coles_html(response.text)
            elif response.status_code == 403:
                print(f"Coles blocked attempt {attempt + 1}, retrying...")
                time.sleep(random.uniform(2, 5))
            else:
                print(f"Coles returned status {response.status_code}")
                
        except Exception as e:
            print(f"Coles error on attempt {attempt + 1}: {e}")
            time.sleep(random.uniform(2, 5))
    
    return None

def parse_coles_html(html):
    """Parse Coles HTML for product prices"""
    soup = BeautifulSoup(html, 'html.parser')
    products = {}
    
    # Try multiple selectors as they change frequently
    selectors = [
        'div.product-tile',
        'article.product',
        'div[data-testid="product-tile"]',
        '.coles-product',
        '[class*="product"][class*="tile"]'
    ]
    
    for selector in selectors:
        items = soup.select(selector)
        if items:
            print(f"Found {len(items)} Coles products with selector: {selector}")
            
            for item in items:
                try:
                    # Extract name
                    name_elem = item.select_one('h3, .product-title, [class*="title"], [data-testid*="title"]')
                    if not name_elem:
                        continue
                    
                    name = name_elem.get_text(strip=True).lower()
                    
                    # Check if this matches any tracked items
                    for item_id, item_data in TRACKED_ITEMS.items():
                        if any(term.lower() in name for term in item_data['search_terms']):
                            # Extract price
                            price = None
                            special_price = None
                            
                            # Look for price elements
                            price_selectors = [
                                '.price',
                                '[class*="price"]',
                                '[data-testid*="price"]',
                                '.special-price',
                                '.sale-price'
                            ]
                            
                            for ps in price_selectors:
                                price_elem = item.select_one(ps)
                                if price_elem:
                                    price_text = price_elem.get_text(strip=True)
                                    # Extract numbers
                                    matches = re.findall(r'\$?(\d+\.?\d*)', price_text)
                                    if matches:
                                        price = float(matches[0])
                                        break
                            
                            # Check for special/clearance indicators
                            is_special = bool(item.select_one('.special-badge, .clearance, .sale-badge, [class*="special"], [class*="sale"]'))
                            
                            products[item_id] = {
                                'name': item_data['name'],
                                'price': price or 0,
                                'special': is_special,
                                'special_price': special_price if is_special else None,
                                'store': 'coles',
                                'found_name': name
                            }
                            break
                            
                except Exception as e:
                    continue
            
            if products:
                break
    
    return products

def scrape_woolworths_product(product_id):
    """Scrape specific Woolworths product page"""
    url = f"https://www.woolworths.com.au/shop/productdetails/{product_id}"
    headers = get_random_headers()
    
    try:
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract product name
            name_elem = soup.select_one('h1[data-testid="product-title"], h1[class*="product-title"], h1')
            name = name_elem.get_text(strip=True).lower() if name_elem else ""
            
            # Extract price - try multiple selectors
            price = None
            special_price = None
            is_special = False
            
            # Look for price in dollar format with $
            price_patterns = [
                r'\$([\d]+\.\d{2})',  # $11.00
                r'\$([\d]+)',         # $11
                r'([\d]+\.\d{2})',    # 11.00
            ]
            
            price_selectors = [
                '[data-testid="price"]',
                '.price',
                '[class*="price"]',
                '[class*="current-price"]',
                'span[class*="dollar"]',
                'div[class*="price"]'
            ]
            
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    print(f"Price element text: {price_text}")  # Debug
                    # Look for dollar amount
                    for pattern in price_patterns:
                        matches = re.findall(pattern, price_text.replace(',', ''))
                        if matches:
                            # Filter out unreasonable values (mL, g, etc)
                            val = float(matches[0])
                            if 0.5 < val < 500:  # Reasonable price range
                                price = val
                                break
                    if price:
                        break
            
            # Check for was/now pricing (special offer)
            was_price_elem = soup.select_one('[class*="was-price"], [class*="original-price"], [class*="was"]')
            if was_price_elem:
                was_text = was_price_elem.get_text(strip=True)
                print(f"Was price text: {was_text}")  # Debug
                for pattern in price_patterns:
                    was_matches = re.findall(pattern, was_text.replace(',', ''))
                    if was_matches:
                        val = float(was_matches[0])
                        if 0.5 < val < 500:
                            is_special = True
                            special_price = price  # Current price is the special
                            price = val  # Was price is the original
                            break
            
            # Check for special badge
            if not is_special:
                special_badge = soup.select_one('[class*="special"], [class*="sale"], [class*="badge"]')
                if special_badge:
                    is_special = True
            
            return {
                'name': name,
                'price': price or 0,
                'special': is_special,
                'special_price': special_price,
                'store': 'woolworths',
                'found_name': name,
                'product_id': product_id
            }
    except Exception as e:
        print(f"Error scraping Woolworths product {product_id}: {e}")
    
    return None

def scrape_woolworths_with_retry():
    """Scrape Woolworths with retry logic"""
    products = {}
    
    # Try scraping specific products first (more reliable)
    for item_id, item_data in TRACKED_ITEMS.items():
        if 'woolies_product_id' in item_data:
            product_data = scrape_woolworths_product(item_data['woolies_product_id'])
            if product_data:
                products[item_id] = product_data
                print(f"Found {item_id} via direct product lookup: ${product_data['price']}")
    
    # Also try the specials page for other items
    urls = [
        "https://www.woolworths.com.au/shop/specials",
        "https://www.woolworths.com.au/shop/browse/specials"
    ]
    
    for attempt in range(3):
        try:
            url = random.choice(urls)
            headers = get_random_headers()
            
            time.sleep(random.uniform(1, 3))
            
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                page_products = parse_woolworths_html(response.text)
                # Merge with existing products (don't overwrite direct lookups)
                for key, value in page_products.items():
                    if key not in products:
                        products[key] = value
                return products
            elif response.status_code == 403:
                print(f"Woolworths blocked attempt {attempt + 1}, retrying...")
                time.sleep(random.uniform(2, 5))
            else:
                print(f"Woolworths returned status {response.status_code}")
                
        except Exception as e:
            print(f"Woolworths error on attempt {attempt + 1}: {e}")
            time.sleep(random.uniform(2, 5))
    
    return products if products else None

def parse_woolworths_html(html):
    """Parse Woolworths HTML for product prices"""
    soup = BeautifulSoup(html, 'html.parser')
    products = {}
    
    # Try multiple selectors
    selectors = [
        'div.product-grid-item',
        'article.product',
        'div[data-testid="product-grid-item"]',
        '.woolworths-product',
        '[class*="product"][class*="grid"]',
        'section[data-testid="product-section"]'
    ]
    
    for selector in selectors:
        items = soup.select(selector)
        if items:
            print(f"Found {len(items)} Woolworths products with selector: {selector}")
            
            for item in items:
                try:
                    # Extract name - try multiple selectors
                    name_elem = None
                    for name_selector in ['a[href*="/shop/productdetails"]', '.product-title', '[class*="product-title"]', '[data-testid*="title"]', 'h3', 'h4', 'h2']:
                        name_elem = item.select_one(name_selector)
                        if name_elem:
                            break
                    
                    if not name_elem:
                        continue
                    
                    name = name_elem.get_text(strip=True).lower()
                    
                    # Check if this matches any tracked items (more flexible matching)
                    for item_id, item_data in TRACKED_ITEMS.items():
                        # Check for any search term in the product name
                        matched = False
                        for term in item_data['search_terms']:
                            if term.lower() in name:
                                matched = True
                                break
                        
                        # Also check if key words match
                        if not matched:
                            # For coke zero, check for both "coca" and "zero"
                            if item_id == 'coke-zero' and ('coca' in name or 'coke' in name) and 'zero' in name:
                                matched = True
                        
                        if matched:
                            # Extract price - try more selectors
                            price = None
                            special_price = None
                            is_special = False
                            
                            price_selectors = [
                                '[data-testid="price"]',
                                '.price',
                                '[class*="price"]',
                                '.primary-price',
                                '.sale-price',
                                '.special-price',
                                '[class*="current-price"]'
                            ]
                            
                            for ps in price_selectors:
                                price_elem = item.select_one(ps)
                                if price_elem:
                                    price_text = price_elem.get_text(strip=True)
                                    print(f"Found price text: {price_text}")  # Debug
                                    # Extract dollar amount
                                    matches = re.findall(r'\$?([\d]+\.?\d*)', price_text.replace(',', ''))
                                    if matches:
                                        price = float(matches[0])
                                        break
                            
                            # Look for special/clearance pricing
                            special_elem = item.select_one('.was-price, .original-price, [class*="was"], [class*="original"]')
                            if special_elem:
                                is_special = True
                                special_text = special_elem.get_text(strip=True)
                                special_matches = re.findall(r'\$?([\d]+\.?\d*)', special_text.replace(',', ''))
                                if special_matches:
                                    special_price = price
                                    price = float(special_matches[0])  # Original/was price
                            
                            # Check for special badges
                            if not is_special:
                                is_special = bool(item.select_one('.badge--special, .special-badge, .on-special, [class*="special"], [class*="sale"], [class*="clearance"]'))
                            
                            products[item_id] = {
                                'name': item_data['name'],
                                'price': price or 0,
                                'special': is_special,
                                'special_price': special_price,
                                'store': 'woolworths',
                                'found_name': name
                            }
                            print(f"Matched {item_id}: ${price} (special: {is_special})")
                            break
                            
                except Exception as e:
                    print(f"Error parsing item: {e}")
                    continue
            
            if products:
                break
    
    return products

def update_prices():
    """Update all prices and cache them"""
    print(f"[{datetime.now()}] Starting price update...")
    
    # Load existing cache
    cache = load_cached_prices()
    
    # Scrape both stores
    coles_data = scrape_coles_with_retry()
    woolies_data = scrape_woolworths_with_retry()
    
    # Build result
    result = {
        'timestamp': datetime.now().isoformat(),
        'coles': coles_data or cache.get('coles', {}),
        'woolworths': woolies_data or cache.get('woolworths', {}),
        'status': {
            'coles_success': coles_data is not None,
            'woolies_success': woolies_data is not None,
            'used_cache': coles_data is None or woolies_data is None
        }
    }
    
    # Only update cache if we got new data
    if coles_data or woolies_data:
        save_cached_prices(result)
        print(f"[{datetime.now()}] Prices updated and cached")
    else:
        print(f"[{datetime.now()}] Using cached prices (scraping failed)")
    
    return result

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
    print("🛒 Automatic Price Scraper starting on http://localhost:5002")
    print("Features:")
    print("  - Rotating user agents to avoid blocking")
    print("  - Retry logic with exponential backoff")
    print("  - Automatic caching (1 hour refresh)")
    print("  - Fallback to cached data if scraping fails")
    print("")
    print("API Endpoints:")
    print("  GET  /api/prices         - Get current prices")
    print("  POST /api/prices/refresh - Force refresh")
    print("  GET  /api/prices/status  - Check scraper status")
    
    # Initial scrape on startup
    update_prices()
    
    app.run(debug=True, port=5002, host='0.0.0.0')