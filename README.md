# 🍽️ Meal Planner Pro

A beautiful drag-and-drop meal planning web app with macro tracking and Apple Reminders integration.

## Features

✅ **Recipe Library** - Scrollable list of recipes with search  
✅ **Drag & Drop Calendar** - Plan lunch & dinner for the week  
✅ **Macro Tracking** - See daily calories, protein, carbs, fat  
✅ **Smart Shopping List** - Aggregates ingredients across meals  
✅ **Apple Reminders** - One-click push to your shopping list  

## Quick Start

### 1. Install Dependencies
```bash
cd /Users/adbiptuy/clawd/meal-planner
pip3 install -r requirements.txt
```

### 2. Start the Backend Server
```bash
python3 server.py
```

The API will run on `http://localhost:5000`

### 3. Open the Web App
```bash
open index.html
```

Or drag `index.html` into your browser.

## How It Works

1. **Drag recipes** from the left panel onto the calendar (lunch/dinner slots)
2. **View macros** at the bottom - shows daily averages for the week
3. **Click "Generate Shopping List"** when you're happy with the plan
4. **Ingredients are aggregated** - if 3 meals need chicken, it shows total amount
5. **Items pushed to Apple Reminders** with emojis and quantities!

## Recipe Data Format

Recipes are stored in `index.html` with this structure:
```javascript
{
    id: 1,
    name: "Cheesy Chicken Fajita Wraps",
    calories: 394,
    protein: 43,
    carbs: 27,
    fat: 17,
    servings: 10,
    tags: ["high protein", "meal prep"],
    ingredients: [
        { name: "Chicken Thighs", amount: 160, unit: "g", perServing: true },
        { name: "Red Onion", amount: 20, unit: "g", perServing: true },
        ...
    ]
}
```

## Adding Your Own Recipes

1. Edit `index.html`
2. Find the `recipes` array in the `<script>` section
3. Add your recipe following the format above
4. Refresh the page

## Architecture

- **Frontend**: Pure HTML/CSS/JS (no build step!)
- **Backend**: Flask Python API
- **Reminders**: Uses `remindctl` CLI for Apple Reminders
- **Data**: Recipes stored in JS, meal plan in memory (no DB needed)

## Future Enhancements

- [ ] Save meal plans to JSON files
- [ ] Import recipes from URLs (TikTok, Instagram)
- [ ] Multiple shopping lists (weekly, special occasions)
- [ ] Export to PDF
- [ ] Macro goals/targets
- [ ] Recipe scaling (cook for 4 instead of 2)
- [ ] Webhook for automatic video-to-recipe import

## Troubleshooting

**Server won't start?**
- Make sure port 5000 is free: `lsof -i :5000`
- Check Python 3 is installed: `python3 --version`

**Reminders not working?**
- Ensure `remindctl` is installed: `which remindctl`
- Check Apple Reminders permissions

**CORS errors?**
- Make sure server is running on localhost:5000
- Check browser console for details

---

Built with ❤️ for Ethan