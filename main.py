import os
import json
import datetime
import functools
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///instance/bot.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db = SQLAlchemy(app)

# Create data directories if they don't exist
os.makedirs("data", exist_ok=True)
os.makedirs("data/inventories", exist_ok=True)

# Define models
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(100))
    rarity = db.Column(db.String(20), default="common")
    usable = db.Column(db.Boolean, default=False)
    tradable = db.Column(db.Boolean, default=True)
    effect = db.Column(db.String(255))

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    game_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False) 
    entry_fee = db.Column(db.Integer, default=0)
    prize_pool = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="upcoming")
    max_participants = db.Column(db.Integer, default=16)

# Initialize database
with app.app_context():
    db.create_all()
    # Create default admin if none exists
    if not Admin.query.filter_by(username="admin").first():
        admin = Admin(username="admin")
        admin.set_password("adminpass")  # Change this in production
        db.session.add(admin)
        db.session.commit()
        logger.info("Created default admin user")

# Helper functions for reading/writing bot data
def load_bot_data():
    try:
        if os.path.exists("data/bot_data.json"):
            with open("data/bot_data.json", "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error loading bot data: {e}")
    return {"status": "unknown"}

def load_user_data():
    try:
        if os.path.exists("data/user_balances.json"):
            with open("data/user_balances.json", "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error loading user data: {e}")
    return {}

def save_user_inventory(user_id, inventory):
    # Create data directory if it doesn't exist
    os.makedirs("data/inventories", exist_ok=True)
    
    try:
        with open(f"data/inventories/{user_id}.json", "w") as f:
            json.dump(inventory, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving inventory for user {user_id}: {e}")
        return False

def load_user_inventory(user_id):
    try:
        if os.path.exists(f"data/inventories/{user_id}.json"):
            with open(f"data/inventories/{user_id}.json", "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error loading inventory for user {user_id}: {e}")
    
    # Default empty inventory
    return {
        "items": [],
        "capacity": 20,
        "last_updated": datetime.datetime.now().isoformat()
    }

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Function to check if user is logged in
def login_required(view_func):
    @functools.wraps(view_func)
    def decorated_view(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    return decorated_view

# Main routes
@app.route('/')
def index():
    # If user is already logged in, redirect to dashboard
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
    
    return render_template('index.html', 
                           title="Discord Bot Manager",
                           bot_name="Enhanced Economy Bot")

@app.route('/dashboard')
@login_required
def dashboard():
    bot_data = load_bot_data()
    users_count = len(load_user_data())
    tournaments_count = Tournament.query.count()
    items_count = InventoryItem.query.count()
    
    return render_template('dashboard.html', 
                           title="Admin Dashboard",
                           bot_data=bot_data,
                           users_count=users_count,
                           tournaments_count=tournaments_count,
                           items_count=items_count)

@app.route('/settings')
@login_required
def settings():
    bot_data = load_bot_data()
    users_count = len(load_user_data())
    
    return render_template('settings.html', 
                           title="Bot Settings",
                           bot_data=bot_data,
                           users_count=users_count)

@app.route('/users')
@login_required
def users():
    user_data = load_user_data()
    
    return render_template('users.html', 
                           title="User Management",
                           users=user_data)

@app.route('/user/<user_id>')
@login_required
def user_details(user_id):
    user_data = load_user_data()
    if user_id not in user_data:
        flash('User not found', 'danger')
        return redirect(url_for('users'))
    
    user_inventory = load_user_inventory(user_id)
    
    return render_template('user_details.html',
                           title=f"User {user_id}",
                           user_id=user_id,
                           user=user_data[user_id],
                           inventory=user_inventory)

# Inventory management routes
@app.route('/items')
@login_required
def items():
    all_items = InventoryItem.query.all()
    return render_template('items.html', 
                           title="Inventory Items",
                           items=all_items)

@app.route('/items/new', methods=['GET', 'POST'])
@login_required
def new_item():
    if request.method == 'POST':
        # Create new item
        item = InventoryItem(
            name=request.form.get('name'),
            description=request.form.get('description'),
            icon=request.form.get('icon'),
            rarity=request.form.get('rarity'),
            usable=bool(request.form.get('usable')),
            tradable=bool(request.form.get('tradable')),
            effect=request.form.get('effect')
        )
        db.session.add(item)
        db.session.commit()
        
        flash('Item created successfully', 'success')
        return redirect(url_for('items'))
    
    return render_template('item_form.html', 
                           title="Create New Item")

@app.route('/items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    
    if request.method == 'POST':
        # Update item
        item.name = request.form.get('name')
        item.description = request.form.get('description')
        item.icon = request.form.get('icon')
        item.rarity = request.form.get('rarity')
        item.usable = bool(request.form.get('usable'))
        item.tradable = bool(request.form.get('tradable'))
        item.effect = request.form.get('effect')
        
        db.session.commit()
        flash('Item updated successfully', 'success')
        return redirect(url_for('items'))
    
    return render_template('item_form.html', 
                           title="Edit Item",
                           item=item)

# Tournament management routes
@app.route('/tournaments')
@login_required
def tournaments():
    all_tournaments = Tournament.query.all()
    return render_template('tournaments.html', 
                           title="Tournaments",
                           tournaments=all_tournaments)

@app.route('/tournaments/new', methods=['GET', 'POST'])
@login_required
def new_tournament():
    if request.method == 'POST':
        # Create new tournament
        tournament = Tournament(
            name=request.form.get('name'),
            description=request.form.get('description'),
            game_type=request.form.get('game_type'),
            start_date=datetime.datetime.fromisoformat(request.form.get('start_date')),
            end_date=datetime.datetime.fromisoformat(request.form.get('end_date')),
            entry_fee=int(request.form.get('entry_fee')),
            prize_pool=int(request.form.get('prize_pool')),
            max_participants=int(request.form.get('max_participants')),
            status=request.form.get('status')
        )
        db.session.add(tournament)
        db.session.commit()
        
        flash('Tournament created successfully', 'success')
        return redirect(url_for('tournaments'))
    
    return render_template('tournament_form.html', 
                           title="Create New Tournament")

@app.route('/tournaments/edit/<int:tournament_id>', methods=['GET', 'POST'])
@login_required
def edit_tournament(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    
    if request.method == 'POST':
        # Update tournament
        tournament.name = request.form.get('name')
        tournament.description = request.form.get('description')
        tournament.game_type = request.form.get('game_type')
        tournament.start_date = datetime.datetime.fromisoformat(request.form.get('start_date'))
        tournament.end_date = datetime.datetime.fromisoformat(request.form.get('end_date'))
        tournament.entry_fee = int(request.form.get('entry_fee'))
        tournament.prize_pool = int(request.form.get('prize_pool'))
        tournament.max_participants = int(request.form.get('max_participants'))
        tournament.status = request.form.get('status')
        
        db.session.commit()
        flash('Tournament updated successfully', 'success')
        return redirect(url_for('tournaments'))
    
    return render_template('tournament_form.html', 
                           title="Edit Tournament",
                           tournament=tournament)

# Helper function to save bot_data
def save_bot_data(bot_data):
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/bot_data.json", "w") as f:
            json.dump(bot_data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving bot data: {e}")
        return False

# API routes for the Discord bot
@app.route('/api/bot/status', methods=['GET'])
def api_bot_status():
    bot_data = load_bot_data()
    return jsonify(bot_data)

@app.route('/api/bot/settings', methods=['GET', 'POST'])
@login_required
def api_bot_settings():
    bot_data = load_bot_data()
    
    if request.method == 'GET':
        # Return only the settings portion of bot_data
        settings = {
            "daily_interest_rate": bot_data.get("daily_interest_rate", 0.5),
            "jackpot_chance": bot_data.get("jackpot_chance", 0.1),
            "daily_cooldown_hours": bot_data.get("daily_cooldown_hours", 24),
            "global_coin_boost_active": bot_data.get("global_coin_boost_active", False),
            "global_coin_boost_multiplier": bot_data.get("global_coin_boost_multiplier", 1.5),
            "global_coin_boost_ends_at": bot_data.get("global_coin_boost_ends_at", None),
            "daily_reward_amount": bot_data.get("daily_reward_amount", 100),
            "slot_jackpot_pool": bot_data.get("slot_jackpot_pool", 5000),
            "slot_jackpot_contribution": bot_data.get("slot_jackpot_contribution", 5.0)
        }
        return jsonify(settings)
    
    if request.method == 'POST':
        # Update bot settings
        settings_data = request.json
        
        # Validate input data before updating
        if not isinstance(settings_data, dict):
            return jsonify({"status": "error", "message": "Invalid data format"}), 400
            
        # Update settings in bot_data
        for key, value in settings_data.items():
            if key in ["daily_interest_rate", "jackpot_chance", "daily_cooldown_hours", 
                      "global_coin_boost_multiplier", "daily_reward_amount", 
                      "slot_jackpot_contribution"]:
                try:
                    # Convert to appropriate type and validate range
                    if key in ["daily_interest_rate", "jackpot_chance", "slot_jackpot_contribution"]:
                        value = float(value)
                        if value < 0 or value > 100:
                            return jsonify({"status": "error", "message": f"Invalid range for {key}"}), 400
                    elif key in ["daily_cooldown_hours"]:
                        value = int(value)
                        if value < 1 or value > 48:
                            return jsonify({"status": "error", "message": f"Invalid range for {key}"}), 400
                    elif key in ["daily_reward_amount"]:
                        value = int(value)
                        if value < 1:
                            return jsonify({"status": "error", "message": f"Invalid value for {key}"}), 400
                    
                    bot_data[key] = value
                except (ValueError, TypeError):
                    return jsonify({"status": "error", "message": f"Invalid value for {key}"}), 400
            elif key == "global_coin_boost_active":
                bot_data[key] = bool(value)
                
        # Save the updated bot_data
        success = save_bot_data(bot_data)
        if success:
            return jsonify({"status": "success", "message": "Bot settings updated successfully"})
        else:
            return jsonify({"status": "error", "message": "Failed to save bot settings"}), 500

@app.route('/api/bot/send-announcement', methods=['POST'])
@login_required
def api_send_announcement():
    data = request.json
    if not data or not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Invalid data format"}), 400
        
    title = data.get('title')
    content = data.get('content')
    is_important = data.get('is_important', False)
    
    if not title or not content:
        return jsonify({"status": "error", "message": "Title and content are required"}), 400
    
    # In a real implementation, this would send the announcement to Discord
    # For now, we'll just log it and return success
    logger.info(f"Announcement: {title} - {content} (Important: {is_important})")
    
    # Update bot_data to record the announcement
    bot_data = load_bot_data()
    announcements = bot_data.get("announcements", [])
    announcements.append({
        "title": title,
        "content": content,
        "is_important": is_important,
        "timestamp": datetime.datetime.now().isoformat()
    })
    bot_data["announcements"] = announcements
    save_bot_data(bot_data)
    
    return jsonify({"status": "success", "message": "Announcement sent successfully"})

@app.route('/api/users', methods=['GET'])
def api_users():
    user_data = load_user_data()
    return jsonify(user_data)

@app.route('/api/user/<user_id>/inventory', methods=['GET', 'POST'])
def api_user_inventory(user_id):
    if request.method == 'GET':
        inventory = load_user_inventory(user_id)
        return jsonify(inventory)
    
    if request.method == 'POST':
        # Require login for POST requests that modify data
        if 'admin_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
            
        # Update user inventory
        inventory_data = request.json
        success = save_user_inventory(user_id, inventory_data)
        if success:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Failed to save inventory"}), 500

@app.route('/api/tournaments', methods=['GET'])
def api_tournaments():
    tournaments = Tournament.query.all()
    result = []
    for t in tournaments:
        result.append({
            "id": t.id,
            "name": t.name,
            "game_type": t.game_type,
            "start_date": t.start_date.isoformat(),
            "end_date": t.end_date.isoformat(),
            "entry_fee": t.entry_fee,
            "prize_pool": t.prize_pool,
            "status": t.status,
            "max_participants": t.max_participants
        })
    return jsonify(result)

@app.route('/api/items', methods=['GET'])
def api_items():
    items = InventoryItem.query.all()
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "icon": item.icon,
            "rarity": item.rarity,
            "usable": item.usable,
            "tradable": item.tradable,
            "effect": item.effect
        })
    return jsonify(result)

if __name__ == "__main__":
    import os
    instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)