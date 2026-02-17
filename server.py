#!/usr/bin/env python3
"""
Meal Planner Backend API
Handles shopping list generation and Apple Reminders integration
"""

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import subprocess
import json
import re
import os
import glob
import urllib.parse

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Get the directory containing this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEOS_DIR = os.path.join(BASE_DIR, 'videos')
os.makedirs(VIDEOS_DIR, exist_ok=True)

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

@app.route('/api/shopping', methods=['POST'])
def add_shopping_items():
    """
    Add individual shopping items to Apple Reminders
    
    Expected JSON:
    {
        "items": ["📋 Milk", "🍞 Bread", ...]
    }
    """
    try:
        data = request.json
        items = data.get('items', [])
        list_name = data.get('listName', 'Shopping List')
        
        if not items:
            return jsonify({
                "success": False,
                "error": "No items provided"
            }), 400
        
        results = []
        successful = 0
        failed = 0
        
        for item in items:
            success, message = add_to_reminders(item, list_name)
            
            if success:
                successful += 1
            else:
                failed += 1
            
            results.append({
                "item": item,
                "success": success,
                "message": message
            })
        
        return jsonify({
            "success": True,
            "summary": {
                "total": len(items),
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

@app.route('/api/meals', methods=['POST'])
def add_meals_to_reminders():
    """
    Add meals to the Meals list in Apple Reminders
    
    Expected JSON:
    {
        "meals": [
            {"name": "Chicken Fajitas", "emoji": "🌯", "day": "Mon", "type": "dinner"},
            ...
        ],
        "servings": 2
    }
    """
    try:
        data = request.json
        meals = data.get('meals', [])
        list_name = data.get('listName', 'Meals')
        servings = data.get('servings', 1)
        
        if not meals:
            return jsonify({
                "success": False,
                "error": "No meals provided"
            }), 400
        
        results = []
        successful = 0
        failed = 0
        
        for meal in meals:
            name = meal.get('name', '')
            emoji = meal.get('emoji', '🍽️')
            day = meal.get('day', '')
            meal_type = meal.get('type', '')
            
            # Format: "🌯 Mon Dinner: Chicken Fajitas (serves 2)"
            title = f"{emoji} {day} {meal_type.capitalize()}: {name}"
            if servings > 1:
                title += f" (serves {servings})"
            
            success, message = add_to_reminders(title, list_name)
            
            if success:
                successful += 1
            else:
                failed += 1
            
            results.append({
                "meal": name,
                "title": title,
                "success": success,
                "message": message
            })
        
        return jsonify({
            "success": True,
            "summary": {
                "total": len(meals),
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

@app.route('/api/reminders/clear', methods=['POST'])
def clear_reminders_list():
    """Clear all items from a reminder list"""
    try:
        data = request.json
        list_name = data.get('listName', 'Shopping List')
        
        result = clear_reminders_list_internal(list_name)
        
        if "error" in result and result["error"]:
            return jsonify({
                "success": False, 
                "error": result["error"]
            }), 500
        
        return jsonify({
            "success": True,
            "listName": list_name,
            "deleted": result.get("deleted", 0),
            "failed": result.get("failed", 0)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reminders/clear-all', methods=['POST'])
def clear_all_meal_reminders():
    """Clear both meal plan and shopping list reminders"""
    try:
        results = []
        
        # Clear Shopping List
        shopping_result = clear_reminders_list_internal('Shopping List')
        results.append({"list": "Shopping List", **shopping_result})
        
        # Clear Meal Plan list
        meal_result = clear_reminders_list_internal("Meals")
        results.append({"list": "Meals", **meal_result})
        
        total_deleted = sum(r.get('deleted', 0) for r in results)
        total_failed = sum(r.get('failed', 0) for r in results)
        
        return jsonify({
            "success": True,
            "results": results,
            "summary": {
                "totalDeleted": total_deleted,
                "totalFailed": total_failed
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def clear_reminders_list_internal(list_name):
    """Internal function to clear a reminders list using JSON output"""
    try:
        # Get all items in the list with JSON output
        result = subprocess.run(
            ['remindctl', 'list', list_name, '--json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            # List might not exist, that's ok
            if "not found" in result.stderr.lower() or "no reminders" in result.stdout.lower():
                return {"deleted": 0, "failed": 0}
            return {"deleted": 0, "failed": 0, "error": result.stderr}
        
        # Parse JSON output to get reminder IDs
        try:
            reminders = json.loads(result.stdout)
        except json.JSONDecodeError:
            # No reminders or empty list
            return {"deleted": 0, "failed": 0}
        
        if not reminders or len(reminders) == 0:
            return {"deleted": 0, "failed": 0}
        
        # Collect all reminder IDs
        ids_to_delete = []
        for reminder in reminders:
            if isinstance(reminder, dict) and 'id' in reminder:
                ids_to_delete.append(reminder['id'])
            elif isinstance(reminder, str):
                # Try to extract ID from string format
                parts = reminder.split()
                if parts:
                    ids_to_delete.append(parts[0])
        
        if not ids_to_delete:
            return {"deleted": 0, "failed": 0}
        
        # Delete all reminders by ID
        deleted_count = 0
        failed_count = 0
        
        for reminder_id in ids_to_delete:
            try:
                delete_result = subprocess.run(
                    ['remindctl', 'delete', reminder_id, '--force'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if delete_result.returncode == 0:
                    deleted_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1
                continue
        
        return {"deleted": deleted_count, "failed": failed_count}
        
    except Exception as e:
        return {"deleted": 0, "failed": 0, "error": str(e)}


# Video Download and Serving Endpoints

@app.route('/api/videos/download', methods=['POST'])
def download_video():
    """
    Download a video from TikTok/Instagram/Reels URL
    
    Expected JSON:
    {
        "url": "https://www.tiktok.com/@user/video/123...",
        "recipeId": 1,
        "recipeName": "Chicken Fajitas"
    }
    """
    try:
        data = request.json
        url = data.get('url')
        recipe_id = data.get('recipeId')
        recipe_name = data.get('recipeName', 'recipe')
        
        if not url:
            return jsonify({"success": False, "error": "No URL provided"}), 400
        
        # Sanitize recipe name for filename
        safe_name = re.sub(r'[^\w\-_.]', '_', recipe_name.lower())
        output_template = os.path.join(VIDEOS_DIR, f"{recipe_id}_{safe_name}_%(title).50s.%(ext)s")
        
        # Download with yt-dlp - use absolute path and set working directory
        result = subprocess.run(
            [
                'yt-dlp',
                '--no-playlist',
                '--format', 'best[height<=720]',  # Max 720p for smaller files
                '--output', output_template,
                '--write-thumbnail',  # Save thumbnail too
                '--convert-thumbnails', 'jpg',
                '--no-warnings',
                '--cookies-from-browser', 'chrome',  # Use Chrome cookies for TikTok/Instagram auth
                url
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=VIDEOS_DIR  # Run from videos directory
        )
        
        if result.returncode != 0:
            return jsonify({
                "success": False,
                "error": "Download failed",
                "details": result.stderr
            }), 500
        
        # Find the downloaded file
        pattern = os.path.join(VIDEOS_DIR, f"{recipe_id}_{safe_name}_*")
        downloaded_files = glob.glob(pattern)
        
        video_file = None
        thumbnail_file = None
        
        for f in downloaded_files:
            if f.endswith(('.mp4', '.webm', '.mkv')):
                video_file = f
            elif f.endswith('.jpg'):
                thumbnail_file = f
        
        if not video_file:
            return jsonify({
                "success": False,
                "error": "Video file not found after download"
            }), 500
        
        # Generate thumbnail from video if yt-dlp didn't provide one
        video_filename = os.path.basename(video_file)
        base_name = os.path.splitext(video_filename)[0]
        generated_thumbnail = os.path.join(VIDEOS_DIR, f"{base_name}_thumb.jpg")
        
        if not thumbnail_file or not os.path.exists(thumbnail_file):
            try:
                # Extract frame at 2 seconds using ffmpeg
                subprocess.run(
                    [
                        'ffmpeg',
                        '-i', video_file,
                        '-ss', '00:00:02',  # 2 seconds in
                        '-vframes', '1',     # 1 frame
                        '-q:v', '2',         # High quality
                        '-y',                # Overwrite if exists
                        generated_thumbnail
                    ],
                    capture_output=True,
                    timeout=30
                )
                if os.path.exists(generated_thumbnail):
                    thumbnail_file = generated_thumbnail
            except Exception as e:
                print(f"Thumbnail generation failed: {e}")
        
        thumbnail_filename = os.path.basename(thumbnail_file) if thumbnail_file else None
        
        return jsonify({
            "success": True,
            "videoPath": f"/videos/{video_filename}",
            "thumbnailPath": f"/videos/{thumbnail_filename}" if thumbnail_filename else None,
            "filename": video_filename
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Download timed out"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/videos/list', methods=['GET'])
def list_videos():
    """List all downloaded videos"""
    try:
        videos = []
        for f in glob.glob(os.path.join(VIDEOS_DIR, '*')):
            if f.endswith(('.mp4', '.webm', '.mkv')):
                stat = os.stat(f)
                # Extract recipe ID from filename (e.g., "1_chicken_fajitas_...")
                match = re.match(r'(\d+)_.*', os.path.basename(f))
                recipe_id = int(match.group(1)) if match else None
                
                videos.append({
                    "filename": os.path.basename(f),
                    "path": f"/videos/{os.path.basename(f)}",
                    "recipeId": recipe_id,
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })
        
        return jsonify({
            "success": True,
            "videos": sorted(videos, key=lambda x: x['filename'])
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/videos/thumbnail', methods=['GET'])
def get_video_thumbnail():
    """Get thumbnail for a specific recipe's video"""
    try:
        recipe_id = request.args.get('recipeId')
        
        if not recipe_id:
            return jsonify({"success": False, "error": "No recipeId provided"}), 400
        
        # Look for thumbnail files matching this recipe
        pattern = os.path.join(VIDEOS_DIR, f"{recipe_id}_*_thumb.jpg")
        thumbnails = glob.glob(pattern)
        
        # Also check for yt-dlp downloaded thumbnails
        pattern2 = os.path.join(VIDEOS_DIR, f"{recipe_id}_*.jpg")
        thumbnails2 = [f for f in glob.glob(pattern2) if not f.endswith('_thumb.jpg')]
        
        all_thumbnails = thumbnails + thumbnails2
        
        if all_thumbnails:
            # Return the most recently modified thumbnail
            latest = max(all_thumbnails, key=os.path.getmtime)
            return jsonify({
                "success": True,
                "thumbnailPath": f"/videos/{os.path.basename(latest)}"
            })
        
        return jsonify({"success": False, "error": "No thumbnail found"}), 404
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/videos/delete', methods=['POST'])
def delete_video():
    """Delete a video file"""
    try:
        data = request.json
        filename = data.get('filename')
        
        if not filename:
            return jsonify({"success": False, "error": "No filename provided"}), 400
        
        # Security: only allow deleting files in videos directory
        filepath = os.path.join(VIDEOS_DIR, os.path.basename(filename))
        
        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "File not found"}), 404
        
        os.remove(filepath)
        
        # Also delete thumbnail if exists
        thumbnail = filepath.replace('.mp4', '.jpg').replace('.webm', '.jpg').replace('.mkv', '.jpg')
        thumb_base = os.path.splitext(filepath)[0] + '_thumb.jpg'
        if os.path.exists(thumbnail):
            os.remove(thumbnail)
        if os.path.exists(thumb_base):
            os.remove(thumb_base)
        
        return jsonify({"success": True, "message": "Video deleted"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/videos/<path:filename>')
def serve_video(filename):
    """Serve video files"""
    try:
        # Security: prevent directory traversal
        safe_filename = os.path.basename(filename)
        filepath = os.path.join(VIDEOS_DIR, safe_filename)
        
        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "File not found"}), 404
        
        return send_file(filepath)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Server-side data storage for shared meal plans
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
MEAL_PLAN_FILE = os.path.join(DATA_DIR, 'meal_plan.json')

# Default empty meal plan structure
default_meal_plan = {
    "mealPlan": {},
    "currentWeekOffset": 0,
    "servingsCount": 1,
    "favoriteRecipes": [],
    "customGroceryItems": [],
    "lastUpdated": None
}

def load_meal_plan_data():
    """Load meal plan data from server storage"""
    try:
        if os.path.exists(MEAL_PLAN_FILE):
            with open(MEAL_PLAN_FILE, 'r') as f:
                return json.load(f)
        return default_meal_plan.copy()
    except Exception as e:
        print(f"Error loading meal plan: {e}")
        return default_meal_plan.copy()

def save_meal_plan_data(data):
    """Save meal plan data to server storage"""
    try:
        data['lastUpdated'] = subprocess.run(['date', '-u', '+%Y-%m-%dT%H:%M:%SZ'], 
                                            capture_output=True, text=True).stdout.strip()
        with open(MEAL_PLAN_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving meal plan: {e}")
        return False

@app.route('/api/data/mealplan', methods=['GET'])
def get_meal_plan():
    """Get the shared meal plan data"""
    try:
        data = load_meal_plan_data()
        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/data/mealplan', methods=['POST'])
def update_meal_plan():
    """Update the shared meal plan data"""
    try:
        new_data = request.json
        current_data = load_meal_plan_data()
        
        # Update only the fields provided
        if 'mealPlan' in new_data:
            current_data['mealPlan'] = new_data['mealPlan']
        if 'currentWeekOffset' in new_data:
            current_data['currentWeekOffset'] = new_data['currentWeekOffset']
        if 'servingsCount' in new_data:
            current_data['servingsCount'] = new_data['servingsCount']
        if 'favoriteRecipes' in new_data:
            current_data['favoriteRecipes'] = new_data['favoriteRecipes']
        if 'customGroceryItems' in new_data:
            current_data['customGroceryItems'] = new_data['customGroceryItems']
        
        if save_meal_plan_data(current_data):
            return jsonify({
                "success": True,
                "message": "Meal plan saved",
                "lastUpdated": current_data['lastUpdated']
            })
        else:
            return jsonify({"success": False, "error": "Failed to save"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/data/mealplan/clear', methods=['POST'])
def clear_meal_plan():
    """Clear all meal plan data"""
    try:
        if save_meal_plan_data(default_meal_plan.copy()):
            return jsonify({"success": True, "message": "Meal plan cleared"})
        else:
            return jsonify({"success": False, "error": "Failed to clear"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3002))
    print(f"🍽️ Meal Planner API starting on http://localhost:{PORT}")
    print(f"📹 Video downloads will be saved to: {VIDEOS_DIR}")
    print(f"💾 Shared data will be saved to: {DATA_DIR}")
    app.run(debug=True, port=PORT)