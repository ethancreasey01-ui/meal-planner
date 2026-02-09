#!/usr/bin/env python3
"""
Meal Planner Backend API
Handles shopping list generation and Apple Reminders integration
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import json
import re
import os
import time

app = Flask(__name__)
CORS(app)

# Get the directory containing this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Store categories for ingredients
STORE_CATEGORIES = {
    'produce': ['onion', 'garlic', 'tomato', 'tomatoes', 'pepper', 'peppers', 'capsicum', 'cucumber', 'lettuce', 
                'spinach', 'kale', 'cabbage', 'broccoli', 'carrot', 'carrots', 'potato', 'potatoes', 'sweet potato',
                'corn', 'avocado', 'eggplant', 'mushroom', 'olive', 'olives', 'lemon', 'lime', 'apple', 'banana',
                'orange', 'berry', 'berries', 'grape', 'watermelon', 'pineapple', 'coconut', 'kiwi', 'mango',
                'peach', 'cherry', 'strawberry', 'blueberry', 'ginger', 'asparagus', 'spring onion', 'scallions',
                'green onion', 'red onion', 'white onion', 'shallots', 'celery', 'zucchini', 'courgette',
                'sweetcorn', 'corn', 'red pepper', 'green pepper', 'yellow pepper'],
    'meat': ['chicken', 'beef', 'steak', 'pork', 'turkey', 'salmon', 'shrimp', 'fish', 'bacon', 'ham',
             'sausage', 'mince', 'ground beef', 'chicken breast', 'chicken thighs', 'chicken thigh'],
    'dairy': ['egg', 'eggs', 'milk', 'yogurt', 'butter', 'cream', 'cheese', 'cheddar', 'mozzarella',
              'feta', 'parmesan', 'greek yogurt', 'low fat yogurt'],
    'pantry': ['rice', 'pasta', 'noodle', 'bread', 'tortilla', 'wrap', 'flour', 'oats', 'quinoa',
               'beans', 'chickpea', 'lentil', 'tofu', 'oil', 'olive oil', 'vinegar', 'soy sauce',
               'sugar', 'salt', 'honey', 'peanut butter', 'mayo', 'mayonnaise', 'ketchup', 'mustard',
               'sriracha', 'hot sauce', 'spices', 'herbs', 'paprika', 'cumin', 'cinnamon', 'stock',
               'broth', 'tahini', 'cornstarch', 'corn starch', 'baking powder', 'baking soda'],
    'freezer': ['frozen', 'ice cream'],
    'bakery': ['buns', 'brioche', 'baguette', 'rolls'],
    'drinks': ['juice', 'water', 'coffee', 'tea', 'soda', 'wine', 'beer']
}

def get_store_category(ingredient_name):
    """Get store category for ingredient - checks for whole word matches"""
    name_lower = ingredient_name.lower()
    
    # Priority order: produce and meat first to avoid misclassification
    priority_categories = ['produce', 'meat', 'dairy', 'pantry', 'freezer', 'bakery', 'drinks']
    
    for category in priority_categories:
        items = STORE_CATEGORIES.get(category, [])
        for item in items:
            # Check for whole word match (surrounded by spaces, start/end of string, or punctuation)
            item_lower = item.lower()
            # Use word boundary check
            if item_lower in name_lower:
                # Make sure it's not a partial match (e.g., "on" in "onions" should match, but we want to be careful)
                # Check if it's a standalone word
                idx = name_lower.find(item_lower)
                if idx != -1:
                    # Check if it's at the start, end, or surrounded by non-word chars
                    before = idx == 0 or not name_lower[idx-1].isalpha()
                    after = idx + len(item_lower) >= len(name_lower) or not name_lower[idx + len(item_lower)].isalpha()
                    if before and after:
                        return category
    
    return 'other'

# Emoji mapping for ingredients
EMOJI_MAP = {
    'chicken': '🍗',
    'beef': '🥩',
    'steak': '🥩',
    'pork': '🥓',
    'turkey': '🦃',
    'salmon': '🐟',
    'shrimp': '🦐',
    'fish': '🐟',
    'egg': '🥚',
    'eggs': '🥚',
    'rice': '🍚',
    'pasta': '🍝',
    'noodle': '🍜',
    'bread': '🍞',
    'tortilla': '🌯',
    'wrap': '🌯',
    'cheese': '🧀',
    'cheddar': '🧀',
    'mozzarella': '🧀',
    'feta': '🧀',
    'parmesan': '🧀',
    'milk': '🥛',
    'yogurt': '🥛',
    'butter': '🧈',
    'cream': '🥛',
    'onion': '🧅',
    'garlic': '🧄',
    'tomato': '🍅',
    'tomatoes': '🍅',
    'pepper': '🫑',
    'peppers': '🫑',
    'capsicum': '🫑',
    'cucumber': '🥒',
    'lettuce': '🥬',
    'spinach': '🥬',
    'kale': '🥬',
    'cabbage': '🥬',
    'broccoli': '🥦',
    'carrot': '🥕',
    'carrots': '🥕',
    'potato': '🥔',
    'potatoes': '🥔',
    'sweet potato': '🍠',
    'corn': '🌽',
    'avocado': '🥑',
    'eggplant': '🍆',
    'mushroom': '🍄',
    'olive': '🫒',
    'olives': '🫒',
    'lemon': '🍋',
    'lime': '🍋',
    'apple': '🍎',
    'banana': '🍌',
    'orange': '🍊',
    'berry': '🫐',
    'berries': '🫐',
    'grape': '🍇',
    'watermelon': '🍉',
    'pineapple': '🍍',
    'coconut': '🥥',
    'kiwi': '🥝',
    'mango': '🥭',
    'peach': '🍑',
    'cherry': '🍒',
    'strawberry': '🍓',
    'blueberry': '🫐',
    'oil': '🫒',
    'olive oil': '🫒',
    'vinegar': '🍶',
    'soy sauce': '🍶',
    'sugar': '🧂',
    'salt': '🧂',
    'pepper_spice': '🌶️',
    'chili': '🌶️',
    'chilli': '🌶️',
    'spice': '🌶️',
    'herb': '🌿',
    'cilantro': '🌿',
    'coriander': '🌿',
    'parsley': '🌿',
    'basil': '🌿',
    'rosemary': '🌿',
    'thyme': '🌿',
    'oregano': '🌿',
    'honey': '🍯',
    'peanut butter': '🥜',
    'nut': '🥜',
    'almond': '🥜',
    'seed': '🌱',
    'sesame': '🌱',
    'chocolate': '🍫',
    'coffee': '☕',
    'tea': '🍵',
    'juice': '🧃',
    'water': '💧',
    'wine': '🍷',
    'beer': '🍺',
    'soda': '🥤',
    'mayo': '🥄',
    'mayonnaise': '🥄',
    'ketchup': '🍅',
    'mustard': '🌭',
    'sriracha': '🌶️',
    'hot sauce': '🌶️',
    'tahini': '🥣',
    'quinoa': '🌾',
    'oats': '🌾',
    'flour': '🌾',
    'bean': '🫘',
    'beans': '🫘',
    'chickpea': '🫘',
    'lentil': '🫘',
    'tofu': '🧊',
    'edamame': '🫛',
    'asparagus': '🌱',
    'ginger': '🫚',
    'cinnamon': '🧂',
    'cumin': '🧂',
    'paprika': '🧂',
    'seaweed': '🌿',
}

def get_emoji(ingredient_name):
    """Find appropriate emoji for ingredient"""
    name_lower = ingredient_name.lower()
    
    for key, emoji in EMOJI_MAP.items():
        if key in name_lower:
            return emoji
    
    return '🛒'  # Default shopping cart

def format_amount(amount, unit):
    """Format amount with unit"""
    if amount == int(amount):
        amount_str = str(int(amount))
    else:
        amount_str = f"{amount:.1f}"
    
    return f"{amount_str}{unit}"

def add_to_reminders(title, list_name="Shopping List", delay=0.1):
    """Add item to Apple Reminders using remindctl"""
    try:
        # Small delay to avoid rate limiting
        time.sleep(delay)
        
        result = subprocess.run(
            ['remindctl', 'add', '--title', title, '--list', list_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            # Retry once if failed
            time.sleep(0.2)
            result = subprocess.run(
                ['remindctl', 'add', '--title', title, '--list', list_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)

@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "service": "meal-planner-api"})

@app.route('/api/shopping-list', methods=['POST'])
def generate_shopping_list():
    """
    Receive aggregated ingredients and add to Apple Reminders
    
    Expected JSON:
    {
        "ingredients": [
            {"name": "Chicken", "amount": 640, "unit": "g", "meals": ["Fajitas", "Stir Fry"], "category": "meat"},
            ...
        ],
        "mealPlan": {
            "Mon": {"lunch": "Recipe Name", "dinner": "Recipe Name"},
            ...
        }
    }
    """
    try:
        data = request.json
        ingredients = data.get('ingredients', [])
        meal_plan = data.get('mealPlan', {})
        
        if not ingredients:
            return jsonify({
                "success": False,
                "error": "No ingredients provided"
            }), 400
        
        results = []
        successful = 0
        failed = 0
        
        # List names - use simple names that exist
        meals_list_name = "Meals"
        shopping_list_name = "Shopping List"
        
        # Track meal count
        meals_added = 0
        
        # Add meal schedule to separate list
        if meal_plan:
            add_to_reminders("📅 MEAL PLAN", meals_list_name)
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            for day in days:
                if day in meal_plan:
                    day_info = meal_plan[day]
                    lunch = day_info.get('lunch', '-')
                    dinner = day_info.get('dinner', '-')
                    lunch_url = day_info.get('lunchUrl', '')
                    dinner_url = day_info.get('dinnerUrl', '')
                    lunch_image = day_info.get('lunchImage', '🍽️')
                    dinner_image = day_info.get('dinnerImage', '🍽️')
                    
                    # Add day header
                    meal_entry = f"📆 {day}:"
                    success, _ = add_to_reminders(meal_entry, meals_list_name)
                    if success:
                        successful += 1
                    
                    # Add lunch with recipe link and emoji
                    if lunch != '-':
                        if lunch_url:
                            lunch_entry = f"    🌞 L: {lunch_image} {lunch} → {lunch_url}"
                        else:
                            lunch_entry = f"    🌞 L: {lunch_image} {lunch}"
                        success, _ = add_to_reminders(lunch_entry, meals_list_name)
                        if success:
                            successful += 1
                            meals_added += 1
                    
                    # Add dinner with recipe link and emoji
                    if dinner != '-':
                        if dinner_url:
                            dinner_entry = f"    🌙 D: {dinner_image} {dinner} → {dinner_url}"
                        else:
                            dinner_entry = f"    🌙 D: {dinner_image} {dinner}"
                        success, _ = add_to_reminders(dinner_entry, meals_list_name)
                        if success:
                            successful += 1
                            meals_added += 1
        
        # Group ingredients by store category
        categories = {
            'produce': [],
            'meat': [],
            'dairy': [],
            'pantry': [],
            'freezer': [],
            'bakery': [],
            'drinks': [],
            'other': []
        }
        
        category_emojis = {
            'produce': '🥬 PRODUCE',
            'meat': '🥩 MEAT & FISH',
            'dairy': '🥛 DAIRY & EGGS',
            'pantry': '🥫 PANTRY',
            'freezer': '🧊 FROZEN',
            'bakery': '🍞 BAKERY',
            'drinks': '🥤 DRINKS',
            'other': '🛒 OTHER'
        }
        
        for ing in ingredients:
            name = ing.get('name', '')
            category = ing.get('category', get_store_category(name))
            categories[category].append(ing)
        
        # Add ingredients grouped by category to shopping list
        add_to_reminders("🛒 INGREDIENTS", shopping_list_name)
        
        # Note: iOS Reminders Shopping List auto-categorizes items
        # No need for manual category headers - let iOS sort them!
        
        for category, items in categories.items():
            if items:
                for ing in items:
                    name = ing.get('name', '')
                    amount = ing.get('amount', 0)
                    unit = ing.get('unit', 'g')
                    meals = ing.get('meals', [])
                    
                    emoji = get_emoji(name)
                    amount_str = format_amount(amount, unit)
                    meal_count = len(meals)
                    
                    # Format WITHOUT leading emoji so iOS can auto-categorize properly
                    # "Chicken: 640g (2 meals)" - iOS sees "Chicken" → Meat section
                    title = f"{name}: {amount_str}"
                    if meal_count > 1:
                        title += f" ({meal_count} meals)"
                    elif meal_count == 1:
                        title += f" ({meals[0]})"
                    
                    success, message = add_to_reminders(title, shopping_list_name)
                    
                    if success:
                        successful += 1
                    else:
                        failed += 1
                    
                    results.append({
                        "ingredient": name,
                        "title": title,
                        "category": category,
                        "success": success,
                        "message": message
                    })
        
        return jsonify({
            "success": True,
            "summary": {
                "total": len(ingredients),
                "successful": successful,
                "failed": failed,
                "mealsAdded": meals_added
            },
            "results": results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/reminders/lists', methods=['GET'])
def get_reminder_lists():
    """Get available reminder lists"""
    try:
        result = subprocess.run(
            ['remindctl', 'list-lists'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Parse output (assuming format: "List Name (X items)")
            lines = result.stdout.strip().split('\n')
            lists = []
            for line in lines:
                match = re.match(r'(.+?)\s*\((\d+)\s*item', line)
                if match:
                    lists.append({
                        "name": match.group(1).strip(),
                        "itemCount": int(match.group(2))
                    })
            
            return jsonify({"success": True, "lists": lists})
        else:
            return jsonify({"success": False, "error": result.stderr}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/clear-lists', methods=['POST'])
def clear_lists():
    """Clear all items from Meals and Shopping List"""
    try:
        lists_to_clear = ["Meals", "Shopping List"]
        cleared = 0
        failed = 0
        
        for list_name in lists_to_clear:
            # Get all reminders in the list
            result = subprocess.run(
                ['remindctl', 'list', list_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse reminder IDs and delete them
                lines = result.stdout.strip().split('\n')
                ids_to_delete = []
                for line in lines:
                    # Match format like "[1] [ ] Title"
                    match = re.match(r'\[(\d+)\]', line)
                    if match:
                        ids_to_delete.append(match.group(1))
                
                # Delete in reverse order (highest ID first) to avoid index shifting
                for reminder_id in reversed(ids_to_delete):
                    del_result = subprocess.run(
                        ['remindctl', 'delete', reminder_id, '-f'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if del_result.returncode == 0:
                        cleared += 1
                    else:
                        failed += 1
                    time.sleep(0.05)  # Small delay to avoid rate limiting
        
        return jsonify({
            "success": True,
            "summary": {
                "cleared": cleared,
                "failed": failed
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/specials/google', methods=['GET'])
def get_google_specials():
    """Get supermarket specials via Google search"""
    try:
        # Import and run the Google specials scraper
        import importlib.util
        spec = importlib.util.spec_from_file_location("google_specials", 
            os.path.join(BASE_DIR, "google_specials.py"))
        google_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(google_module)
        
        # Get specials
        coles = google_module.scrape_coles_specials()
        woolies = google_module.scrape_woolworths_specials()
        catalogue = google_module.get_catalogue_specials()
        
        # Merge results
        all_coles = {**coles, **catalogue.get('coles', {})}
        all_woolies = {**woolies, **catalogue.get('woolworths', {})}
        
        return jsonify({
            'success': True,
            'data': {
                'coles': all_coles,
                'woolworths': all_woolies,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'google_search'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/product/check', methods=['POST'])
def check_product():
    """Check price and special status for a specific product URL"""
    try:
        data = request.json
        urls = data.get('urls', [])
        
        if not urls:
            return jsonify({'success': False, 'error': 'No URLs provided'}), 400
        
        import importlib.util
        spec = importlib.util.spec_from_file_location("google_specials", 
            os.path.join(BASE_DIR, "google_specials.py"))
        google_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(google_module)
        
        results = []
        for item in urls:
            url = item.get('url')
            store = item.get('store', 'unknown')
            
            if url:
                result = google_module.check_product_url(url, store)
                results.append(result)
                time.sleep(0.5)  # Be nice to the servers
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Load tracked products from JSON file
TRACKED_PRODUCTS_FILE = os.path.join(BASE_DIR, 'tracked_products.json')

def load_tracked_products():
    """Load tracked products from JSON file"""
    try:
        if os.path.exists(TRACKED_PRODUCTS_FILE):
            with open(TRACKED_PRODUCTS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading tracked products: {e}")
        return {}

def save_tracked_products(products):
    """Save tracked products to JSON file"""
    try:
        with open(TRACKED_PRODUCTS_FILE, 'w') as f:
            json.dump(products, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving tracked products: {e}")
        return False

@app.route('/api/tracked-products', methods=['GET'])
def get_tracked_products():
    """Get list of tracked products (without checking prices - just the list)"""
    try:
        products = load_tracked_products()
        return jsonify({
            'success': True,
            'data': products
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tracked-products/check', methods=['POST'])
def check_tracked_products():
    """Check prices for ALL tracked products - one button click!"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("google_specials", 
            os.path.join(BASE_DIR, "google_specials.py"))
        google_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(google_module)
        
        products = load_tracked_products()
        results = []
        
        for product_id, product_info in products.items():
            product_result = {
                'id': product_id,
                'name': product_info.get('name', 'Unknown'),
                'category': product_info.get('category', 'other'),
                'coles': None,
                'woolworths': None
            }
            
            if product_info.get('coles_url'):
                product_result['coles'] = google_module.check_product_url(
                    product_info['coles_url'], 'Coles'
                )
                time.sleep(0.5)
            
            if product_info.get('woolies_url'):
                product_result['woolworths'] = google_module.check_product_url(
                    product_info['woolies_url'], 'Woolworths'
                )
                time.sleep(0.5)
            
            results.append(product_result)
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results),
            'checked_at': time.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tracked-products', methods=['POST'])
def add_tracked_product():
    """Add a new product to track"""
    try:
        data = request.json
        name = data.get('name')
        coles_url = data.get('coles_url', '')
        woolies_url = data.get('woolies_url', '')
        category = data.get('category', 'other')
        
        if not name:
            return jsonify({'success': False, 'error': 'Product name required'}), 400
        
        if not coles_url and not woolies_url:
            return jsonify({'success': False, 'error': 'At least one URL required'}), 400
        
        products = load_tracked_products()
        
        # Generate ID from name
        product_id = name.lower().replace(' ', '-').replace("'", '').replace('&', 'and')[:30]
        
        products[product_id] = {
            'name': name,
            'coles_url': coles_url,
            'woolies_url': woolies_url,
            'category': category
        }
        
        if save_tracked_products(products):
            return jsonify({
                'success': True,
                'message': f'Added {name} to tracked products',
                'id': product_id
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to save'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tracked-products/<product_id>', methods=['DELETE'])
def delete_tracked_product(product_id):
    """Remove a product from tracking"""
    try:
        products = load_tracked_products()
        
        if product_id in products:
            name = products[product_id]['name']
            del products[product_id]
            save_tracked_products(products)
            return jsonify({
                'success': True,
                'message': f'Removed {name} from tracked products'
            })
        else:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🍽️ Meal Planner API starting on http://0.0.0.0:5000")
    print("   Local access: http://localhost:5000")
    print("   Network access: http://192.168.68.86:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)