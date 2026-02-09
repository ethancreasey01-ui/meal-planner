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

app = Flask(__name__)
CORS(app)

# Get the directory containing this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

def add_to_reminders(title, list_name="Shopping List"):
    """Add item to Apple Reminders using remindctl"""
    try:
        result = subprocess.run(
            ['remindctl', 'add', '--title', title, '--list', list_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
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
            {"name": "Chicken", "amount": 640, "unit": "g", "meals": ["Fajitas", "Stir Fry"]},
            ...
        ]
    }
    """
    try:
        data = request.json
        ingredients = data.get('ingredients', [])
        list_name = data.get('listName', 'Shopping List')
        
        if not ingredients:
            return jsonify({
                "success": False,
                "error": "No ingredients provided"
            }), 400
        
        results = []
        successful = 0
        failed = 0
        
        for ing in ingredients:
            name = ing.get('name', '')
            amount = ing.get('amount', 0)
            unit = ing.get('unit', 'g')
            meals = ing.get('meals', [])
            
            emoji = get_emoji(name)
            amount_str = format_amount(amount, unit)
            meal_count = len(meals)
            
            # Format: "🍗 Chicken: 640g (2 meals)"
            title = f"{emoji} {name}: {amount_str}"
            if meal_count > 1:
                title += f" ({meal_count} meals)"
            elif meal_count == 1:
                title += f" ({meals[0]})"
            
            success, message = add_to_reminders(title, list_name)
            
            if success:
                successful += 1
            else:
                failed += 1
            
            results.append({
                "ingredient": name,
                "title": title,
                "success": success,
                "message": message
            })
        
        return jsonify({
            "success": True,
            "summary": {
                "total": len(ingredients),
                "successful": successful,
                "failed": failed
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

if __name__ == '__main__':
    print("🍽️ Meal Planner API starting on http://localhost:5000")
    app.run(debug=True, port=5000)