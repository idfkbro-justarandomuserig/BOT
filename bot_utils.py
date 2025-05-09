import json
import os
import logging
import datetime
import random
from typing import List, Dict, Any, Optional, Tuple
import requests

# Configure logging
logger = logging.getLogger('bot_utils')
logging.basicConfig(level=logging.INFO)

# Define paths for storage
DATA_DIR = "data"
INVENTORY_FILE = os.path.join(DATA_DIR, "user_inventory.json")
BOT_STATUS_FILE = os.path.join(DATA_DIR, "bot_status.json")

# Make sure data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

class InventorySystem:
    """Handles user inventory operations"""
    
    @staticmethod
    def get_user_inventory(user_id: str) -> Dict[str, Any]:
        """Get a user's inventory, creating a default one if none exists"""
        all_inventories = InventorySystem._load_all_inventories()
        
        if user_id not in all_inventories:
            # Create default inventory for new users
            default_inventory = {
                "capacity": 20,  # Default capacity
                "items": []
            }
            all_inventories[user_id] = default_inventory
            InventorySystem._save_all_inventories(all_inventories)
            
        return all_inventories[user_id]
    
    @staticmethod
    def save_user_inventory(user_id: str, inventory: Dict[str, Any]) -> bool:
        """Save a user's inventory"""
        all_inventories = InventorySystem._load_all_inventories()
        all_inventories[user_id] = inventory
        return InventorySystem._save_all_inventories(all_inventories)
    
    @staticmethod
    def add_item_to_inventory(user_id: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add an item to a user's inventory"""
        inventory = InventorySystem.get_user_inventory(user_id)
        
        # Check if inventory is full
        if len(inventory["items"]) >= inventory["capacity"]:
            return {
                "success": False,
                "message": "Inventory is full! Sell or use some items first."
            }
        
        # Check if the item is stackable and already exists
        if item_data.get("stackable", False):
            for existing_item in inventory["items"]:
                if existing_item.get("name") == item_data.get("name"):
                    # Increment quantity instead of adding new item
                    existing_item["quantity"] = existing_item.get("quantity", 1) + 1
                    InventorySystem.save_user_inventory(user_id, inventory)
                    return {
                        "success": True,
                        "message": f"Added another {item_data.get('name')} to your inventory."
                    }
        
        # Add the item
        if "id" not in item_data:
            # Generate a unique ID for the item
            item_data["id"] = str(random.randint(10000, 99999))
            
        # Set default quantity for stackable items
        if item_data.get("stackable", False) and "quantity" not in item_data:
            item_data["quantity"] = 1
            
        inventory["items"].append(item_data)
        InventorySystem.save_user_inventory(user_id, inventory)
        
        return {
            "success": True,
            "message": f"Added {item_data.get('name')} to your inventory."
        }
    
    @staticmethod
    def remove_item_from_inventory(user_id: str, item_id: int) -> Dict[str, Any]:
        """Remove an item from a user's inventory by id"""
        inventory = InventorySystem.get_user_inventory(user_id)
        
        # Find the item
        for i, item in enumerate(inventory["items"]):
            if str(item.get("id")) == str(item_id):
                # If item is stackable and has quantity > 1, reduce quantity
                if item.get("stackable", False) and item.get("quantity", 1) > 1:
                    inventory["items"][i]["quantity"] -= 1
                else:
                    # Otherwise remove the item
                    inventory["items"].pop(i)
                
                InventorySystem.save_user_inventory(user_id, inventory)
                return {
                    "success": True,
                    "message": f"Removed {item.get('name')} from inventory."
                }
        
        return {
            "success": False,
            "message": "Item not found in inventory."
        }
    
    @staticmethod
    def use_item(user_id: str, item_id: int) -> Dict[str, Any]:
        """Use an item from inventory and apply its effect"""
        inventory = InventorySystem.get_user_inventory(user_id)
        
        # Find the item
        for i, item in enumerate(inventory["items"]):
            if str(item.get("id")) == str(item_id):
                # Check if item is usable
                if not item.get("usable", False):
                    return {
                        "success": False,
                        "message": f"{item.get('name')} cannot be used."
                    }
                
                # Process item effects (would be more sophisticated in actual implementation)
                effect_description = item.get("effect", "No effect")
                
                # Remove the item if it's not permanent
                if not item.get("permanent", False):
                    # If item has quantity > 1, reduce quantity
                    if item.get("quantity", 1) > 1:
                        inventory["items"][i]["quantity"] -= 1
                    else:
                        # Otherwise remove the item
                        inventory["items"].pop(i)
                    
                    InventorySystem.save_user_inventory(user_id, inventory)
                
                return {
                    "success": True,
                    "message": f"Used {item.get('name')}.",
                    "effect": effect_description
                }
        
        return {
            "success": False,
            "message": "Item not found in inventory."
        }
    
    @staticmethod
    def _load_all_inventories() -> Dict[str, Dict[str, Any]]:
        """Load all user inventories from file"""
        if not os.path.exists(INVENTORY_FILE):
            return {}
        
        try:
            with open(INVENTORY_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.error(f"Error loading inventory data from {INVENTORY_FILE}")
            return {}
    
    @staticmethod
    def _save_all_inventories(all_inventories: Dict[str, Dict[str, Any]]) -> bool:
        """Save all user inventories to file"""
        try:
            with open(INVENTORY_FILE, 'w') as f:
                json.dump(all_inventories, f, indent=2)
            return True
        except:
            logger.error(f"Error saving inventory data to {INVENTORY_FILE}")
            return False


class TournamentSystem:
    """Handles tournament operations"""
    
    @staticmethod
    def get_active_tournaments() -> List[Dict[str, Any]]:
        """Get list of currently active tournaments"""
        # In a production environment, this would query the database
        # Here we'll make a request to our Flask API
        try:
            response = requests.get("http://localhost:5000/api/tournaments")
            if response.status_code == 200:
                tournaments = response.json()
                # Filter for active tournaments
                active_tournaments = [t for t in tournaments if t.get("status") in ["active", "upcoming"]]
                return active_tournaments
            else:
                logger.error(f"Failed to fetch tournaments: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching tournaments: {e}")
            return []
    
    @staticmethod
    def register_for_tournament(user_id: str, tournament_id: int) -> Dict[str, Any]:
        """Register a user for a tournament"""
        # This would be a POST request to the API in production
        # For now, we'll simulate success
        
        # Check if tournament exists
        try:
            response = requests.get(f"http://localhost:5000/api/tournaments")
            tournaments = response.json() if response.status_code == 200 else []
            tournament = next((t for t in tournaments if t.get("id") == tournament_id), None)
            
            if not tournament:
                return {
                    "success": False,
                    "message": "Tournament not found"
                }
            
            if tournament.get("status") not in ["active", "upcoming"]:
                return {
                    "success": False,
                    "message": "Tournament is not open for registration"
                }
            
            # In a real implementation, we would record the registration in the database
            # Here we'll just return success
            return {
                "success": True,
                "message": f"Successfully registered for tournament: {tournament.get('name')}",
                "tournament": tournament
            }
        except Exception as e:
            logger.error(f"Error registering for tournament: {e}")
            return {
                "success": False,
                "message": f"Error registering for tournament: {str(e)}"
            }
    
    @staticmethod
    def record_tournament_score(user_id: str, tournament_id: int, score: int) -> Dict[str, Any]:
        """Record a user's score in a tournament"""
        # This would update the database in production
        return {
            "success": True,
            "message": f"Score of {score} recorded for tournament #{tournament_id}"
        }


class MinigameSystem:
    """Handles minigame operations"""
    
    @staticmethod
    def get_available_minigames() -> List[Dict[str, Any]]:
        """Get list of available minigames"""
        # In production, this might come from a database
        minigames = [
            {
                "name": "Trivia",
                "description": "Test your knowledge with random questions",
                "rewards": "10-50 coins per correct answer",
                "cooldown_minutes": 5
            },
            {
                "name": "Word Scramble",
                "description": "Unscramble words against the clock",
                "rewards": "5 coins per letter",
                "cooldown_minutes": 5
            },
            {
                "name": "Number Guess",
                "description": "Guess a number between 1-100",
                "rewards": "50 coins max, decreases with attempts",
                "cooldown_minutes": 5
            },
            {
                "name": "Rock Paper Scissors",
                "description": "Play against the bot",
                "rewards": "15 coins for win, 5 for tie",
                "cooldown_minutes": 1
            },
            {
                "name": "Hangman",
                "description": "Guess the word before the hangman is complete",
                "rewards": "10 coins per correct letter",
                "cooldown_minutes": 10
            }
        ]
        return minigames


def update_bot_status(status_data: Dict[str, Any]) -> bool:
    """Update the bot status file for the web interface"""
    try:
        # Get existing data if available
        existing_data = {}
        if os.path.exists(BOT_STATUS_FILE):
            try:
                with open(BOT_STATUS_FILE, 'r') as f:
                    existing_data = json.load(f)
            except:
                pass
        
        # Update with new data
        existing_data.update(status_data)
        existing_data["last_updated"] = datetime.datetime.now().isoformat()
        
        # Save back to file
        with open(BOT_STATUS_FILE, 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"Error updating bot status: {e}")
        return False


def get_bot_status() -> Dict[str, Any]:
    """Get the current bot status"""
    if not os.path.exists(BOT_STATUS_FILE):
        return {
            "status": "unknown",
            "online_since": None,
            "last_updated": None,
            "user_count": 0,
            "message_count": 0,
            "uptime": 0
        }
    
    try:
        with open(BOT_STATUS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            "status": "error",
            "online_since": None,
            "last_updated": None
        }