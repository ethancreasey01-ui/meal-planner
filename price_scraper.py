#!/usr/bin/env python3
"""
Coles & Woolworths Price Scraper
Scrapes weekly specials from both supermarkets
"""

from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import time

app = Flask(__name__)

# Sample tracked items (would be stored in DB in production)
TRACKED_ITEMS = [
    "coke zero",
    "eggs free range",
    "milk full cream",
    "bread white",
    "bananas",
    "chicken breast",
    "pasta spaghetti",
    "yogurt greek"
]

def scrape_coles():
    """Scrape Coles specials page"""
    url = "https://www.coles.com.au/on-special"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        specials = []
        # Coles uses specific class names for products
        products = soup.find_all('div', class_=re.compile('product-tile'))
        
        for product in products:
            try:
                name = product.find('h3', class_=re.compile('product-title')).text.strip()
                
                # Check if it's a tracked item
                if any(tracked.lower() in name.lower() for tracked in TRACKED_ITEMS):
                    price_elem = product.find('span', class_=re.compile('price'))
                    special_price = None
                    
                    if price_elem:
                        # Extract price
                        price_text = price_elem.text.strip()
                        match = re.search(r'\$?([\d.]+)', price_text)
                        if match:
                            special_price = float(match.group(1))
                    
                    specials.append({
                        'name': name,
                        'price': special_price,
                        'special': special_price is not None,
                        'store': 'coles'
                    })
            except:
                continue
        
        return specials
    except Exception as e:
        print(f"Error scraping Coles: {e}")
        return []

def scrape_woolworths():
    """Scrape Woolworths specials page"""
    url = "https://www.woolworths.com.au/shop/specials"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        specials = []
        # Woolworths product selectors
        products = soup.find_all('div', class_=re.compile('product-grid-item'))
        
        for product in products:
            try:
                name_elem = product.find('a', class_=re.compile('product-title'))
                if not name_elem:
                    continue
                
                name = name_elem.text.strip()
                
                # Check if it's a tracked item
                if any(tracked.lower() in name.lower() for tracked in TRACKED_ITEMS):
                    price_elem = product.find('div', class_=re.compile('price'))
                    special_price = None
                    
                    if price_elem:
                        price_text = price_elem.text.strip()
                        match = re.search(r'\$?([\d.]+)', price_text)
                        if match:
                            special_price = float(match.group(1))
                    
                    specials.append({
                        'name': name,
                        'price': special_price,
                        'special': special_price is not None,
                        'store': 'woolworths'
                    })
            except:
                continue
        
        return specials
    except Exception as e:
        print(f"Error scraping Woolworths: {e}")
        return []

@app.route('/api/prices', methods=['GET'])
def get_prices():
    """Get current prices from both stores"""
    coles_data = scrape_coles()
    woolies_data = scrape_woolworths()
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'coles': coles_data,
        'woolworths': woolies_data
    })

@app.route('/api/prices/refresh', methods=['POST'])
def refresh_prices():
    """Force refresh of prices"""
    # Add delay to be nice to their servers
    time.sleep(1)
    return get_prices()

if __name__ == '__main__':
    print("🛒 Price Scraper API starting on http://localhost:5002")
    print("Note: Web scraping may be blocked by Coles/Woolworths")
    print("Consider using their official APIs if available")
    app.run(debug=True, port=5002)