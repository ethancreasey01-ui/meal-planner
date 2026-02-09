#!/usr/bin/env python3
"""
Google Search Supermarket Specials Scraper
Searches Google for Coles and Woolworths specials without browser automation
"""

from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import re
import json
import time
from datetime import datetime

app = Flask(__name__)

# Track common grocery items for specials
TRACKED_ITEMS = {
    'coke-zero': {
        'name': 'Coke Zero 10 Pack',
        'coles_search': 'coke zero 10 pack coles',
        'woolies_search': 'coke zero 10 pack woolworths',
        'category': 'drinks'
    },
    'eggs': {
        'name': 'Free Range Eggs 12pk',
        'coles_search': 'free range eggs 12 pack coles',
        'woolies_search': 'free range eggs 12 pack woolworths',
        'category': 'dairy'
    },
    'milk': {
        'name': 'Full Cream Milk 2L',
        'coles_search': 'full cream milk 2L coles',
        'woolies_search': 'full cream milk 2L woolworths',
        'category': 'dairy'
    },
    'bread': {
        'name': 'White Bread 650g',
        'coles_search': 'white bread 650g coles',
        'woolies_search': 'white bread 650g woolworths',
        'category': 'bakery'
    },
    'bananas': {
        'name': 'Bananas 1kg',
        'coles_search': 'bananas 1kg price coles',
        'woolies_search': 'bananas 1kg price woolworths',
        'category': 'produce'
    },
    'chicken-breast': {
        'name': 'Chicken Breast 500g',
        'coles_search': 'chicken breast 500g coles price',
        'woolies_search': 'chicken breast 500g woolworths price',
        'category': 'meat'
    },
    'beef-mince': {
        'name': 'Beef Mince 500g',
        'coles_search': 'beef mince 500g coles price',
        'woolies_search': 'beef mince 500g woolworths price',
        'category': 'meat'
    },
    'pasta': {
        'name': 'Spaghetti Pasta 500g',
        'coles_search': 'spaghetti pasta 500g coles',
        'woolies_search': 'spaghetti pasta 500g woolworths',
        'category': 'pantry'
    },
    'yogurt': {
        'name': 'Greek Yogurt 1kg',
        'coles_search': 'greek yogurt 1kg coles',
        'woolies_search': 'greek yogurt 1kg woolworths',
        'category': 'dairy'
    },
    'cheese': {
        'name': 'Tasty Cheese 500g',
        'coles_search': 'tasty cheese 500g coles',
        'woolies_search': 'tasty cheese 500g woolworths',
        'category': 'dairy'
    }
}

def search_google(query):
    """Search Google and return results"""
    try:
        # Use DuckDuckGo HTML version (no API key needed)
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"Search error: {e}")
        return None

def extract_price(text):
    """Extract price from text"""
    # Look for patterns like $5.50, $12, 5.50, etc.
    patterns = [
        r'\$([0-9]+\.?[0-9]{0,2})',
        r'([0-9]+\.[0-9]{2})\s*(?:AUD|dollars?)?',
        r'(?:price|cost|was)\s*\$?([0-9]+\.?[0-9]{0,2})'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                price = float(match)
                if 0.50 < price < 500:  # Reasonable price range
                    return price
            except:
                continue
    return None

def scrape_coles_specials():
    """Scrape Coles specials from their website directly"""
    specials = {}
    
    try:
        # Coles half-price specials page
        url = "https://www.coles.com.au/on-special"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for product tiles
            products = soup.find_all('article', class_=re.compile('product-tile', re.I))
            
            for product in products[:20]:  # First 20 products
                try:
                    # Get product name
                    name_elem = product.find(['h3', 'h2', 'h1'], class_=re.compile('product-title|product-name', re.I))
                    if not name_elem:
                        name_elem = product.find(['h3', 'h2', 'h1'])
                    
                    name = name_elem.text.strip() if name_elem else 'Unknown'
                    
                    # Get price
                    price_elem = product.find(['span', 'div'], class_=re.compile('price|special', re.I))
                    if price_elem:
                        price_text = price_elem.text.strip()
                        price = extract_price(price_text)
                        
                        if price and price < 100:  # Sanity check
                            specials[name] = {
                                'price': price,
                                'special': True,
                                'store': 'Coles'
                            }
                except:
                    continue
                    
    except Exception as e:
        print(f"Coles scrape error: {e}")
    
    return specials

def scrape_woolworths_specials():
    """Scrape Woolworths specials from their website directly"""
    specials = {}
    
    try:
        # Woolworths specials page
        url = "https://www.woolworths.com.au/shop/specials"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for product cards
            products = soup.find_all(['article', 'div', 'section'], class_=re.compile('product|tile', re.I))
            
            for product in products[:20]:  # First 20 products
                try:
                    # Get product name
                    name_elem = product.find(['h3', 'h2', 'h1', 'span'], class_=re.compile('title|name', re.I))
                    if not name_elem:
                        name_elem = product.find(['h3', 'h2', 'h1'])
                    
                    name = name_elem.text.strip() if name_elem else 'Unknown'
                    
                    # Get price
                    price_elem = product.find(['span', 'div'], class_=re.compile('price|dollar', re.I))
                    if price_elem:
                        price_text = price_elem.text.strip()
                        price = extract_price(price_text)
                        
                        if price and price < 100:
                            specials[name] = {
                                'price': price,
                                'special': True,
                                'store': 'Woolworths'
                            }
                except:
                    continue
                    
    except Exception as e:
        print(f"Woolworths scrape error: {e}")
    
    return specials

def check_product_url(url, store):
    """Check a specific product URL for price and special status"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            result = {
                'url': url,
                'store': store,
                'name': None,
                'price': None,
                'was_price': None,
                'special': False,
                'special_type': None
            }
            
            # Coles format
            if 'coles.com.au' in url:
                # Product name
                name_elem = soup.find('h1', {'data-testid': 'product-title'})
                if not name_elem:
                    name_elem = soup.find('h1', class_=re.compile('product-title|product-name', re.I))
                if name_elem:
                    result['name'] = name_elem.text.strip()
                
                # Price
                price_elem = soup.find('span', {'data-testid': 'price-value'})
                if not price_elem:
                    price_elem = soup.find('span', class_=re.compile('price', re.I))
                if price_elem:
                    price_text = price_elem.text.strip()
                    result['price'] = extract_price(price_text)
                
                # Was price (for specials)
                was_price_elem = soup.find('span', {'data-testid': 'was-price'})
                if was_price_elem:
                    result['was_price'] = extract_price(was_price_elem.text.strip())
                    if result['was_price'] and result['price']:
                        result['special'] = True
                        result['special_type'] = 'On Sale'
                
                # Check for special badges
                special_badge = soup.find('span', {'data-testid': 'badge'})
                if special_badge:
                    badge_text = special_badge.text.strip()
                    if 'half price' in badge_text.lower() or 'special' in badge_text.lower():
                        result['special'] = True
                        result['special_type'] = badge_text
            
            # Woolworths format
            elif 'woolworths.com.au' in url:
                # Product name
                name_elem = soup.find('h1', {'data-testid': 'product-title'})
                if not name_elem:
                    name_elem = soup.find('h1', class_=re.compile('product-title|product-name', re.I))
                if name_elem:
                    result['name'] = name_elem.text.strip()
                
                # Price
                price_elem = soup.find('div', {'data-testid': 'product-price'})
                if not price_elem:
                    price_elem = soup.find('span', class_=re.compile('price', re.I))
                if price_elem:
                    price_text = price_elem.text.strip()
                    result['price'] = extract_price(price_text)
                
                # Was price (for specials)
                was_price_elem = soup.find('span', class_=re.compile('was-price|savings', re.I))
                if was_price_elem:
                    result['was_price'] = extract_price(was_price_elem.text.strip())
                    if result['was_price'] and result['price']:
                        result['special'] = True
                        result['special_type'] = 'On Sale'
                
                # Check for special badges
                special_badge = soup.find('div', class_=re.compile('badge|special', re.I))
                if special_badge:
                    badge_text = special_badge.text.strip()
                    if 'half price' in badge_text.lower() or 'special' in badge_text.lower():
                        result['special'] = True
                        result['special_type'] = badge_text
            
            return result
        
        return {'error': f'Failed to fetch: HTTP {response.status_code}'}
        
    except Exception as e:
        return {'error': str(e)}

def get_catalogue_specials():
    """Get specials from catalogue aggregator sites"""
    coles_specials = {}
    woolies_specials = {}
    
    try:
        # Try latestcatalogues.com for Coles
        url = "https://www.latestcatalogues.com/coles/"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for product listings with prices
            items = soup.find_all(['div', 'article'], class_=re.compile('item|product|deal', re.I))
            
            for item in items[:15]:
                try:
                    name_elem = item.find(['h3', 'h2', 'h4', 'p'])
                    price_elem = item.find(['span', 'div'], class_=re.compile('price', re.I))
                    
                    if name_elem and price_elem:
                        name = name_elem.text.strip()
                        price = extract_price(price_elem.text)
                        
                        if price:
                            coles_specials[name] = {
                                'price': price,
                                'special': True,
                                'store': 'Coles'
                            }
                except:
                    continue
                    
    except Exception as e:
        print(f"Catalogue scrape error: {e}")
    
    return {'coles': coles_specials, 'woolworths': woolies_specials}

@app.route('/api/specials', methods=['GET'])
def get_specials():
    """Get current supermarket specials"""
    try:
        # Try multiple sources
        coles = scrape_coles_specials()
        woolies = scrape_woolworths_specials()
        catalogue = get_catalogue_specials()
        
        # Merge results
        all_coles = {**coles, **catalogue.get('coles', {})}
        all_woolies = {**woolies, **catalogue.get('woolworths', {})}
        
        # Format for frontend
        formatted = {
            'coles': all_coles,
            'woolworths': all_woolies,
            'timestamp': datetime.now().isoformat(),
            'source': 'web_scrape'
        }
        
        return jsonify({
            'success': True,
            'data': formatted
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("🛒 Google Specials Scraper starting on http://localhost:5003")
    app.run(debug=True, host='0.0.0.0', port=5003)
