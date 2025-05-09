# botX_enhanced.py
# Enhanced version v1.2.0 - Added Daily Interest, Daily Rewards, Voice Channel Rental, Improved Gambling, Shop Enhancements
# Based on v1.1.11

import disnake
from disnake.ext import commands, tasks
import os
import json
import datetime
import pytz
import random
import asyncio
import time as time_module # Alias to avoid conflict with datetime.time
import logging
from dotenv import load_dotenv
from datetime import time, timedelta, timezone
import uuid # For generating shop item IDs
from collections import Counter # For Poker Hand Evaluation

# --- Logging Setup (Revised - Final Fix) ---
log_formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
log_level = logging.INFO
logging.basicConfig(level=log_level, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s', handlers=[logging.StreamHandler()])
disnake_logger = logging.getLogger('disnake')
disnake_logger.setLevel(log_level)
log_file_handler = logging.FileHandler(filename='discord_bot.log', encoding='utf-8', mode='w')
log_file_handler.setFormatter(log_formatter)
disnake_logger.addHandler(log_file_handler)
disnake_logger.propagate = False
logger = logging.getLogger(__name__)

# --- Configuration ---
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PLACEHOLDER_IDS_PRESENT = False
_SHOPKEEPER_ROLE_ID_STR = os.getenv("SHOPKEEPER_ROLE_ID", "1368456384886079519")
_ADMIN_CHANNEL_ID_STR = os.getenv("ADMIN_CHANNEL_ID", "1368455333751816213")
SUPPORTER_ROLE_ID = 1368689142363590726
VIP_ROLE_ID = 1368689440045797436
_LOTTERY_ANNOUNCE_CHANNEL_ID_STR = os.getenv("LOTTERY_ANNOUNCE_CHANNEL_ID", _ADMIN_CHANNEL_ID_STR)
ANNOUNCEMENT_CHANNEL_ID_STR = os.getenv("ANNOUNCEMENT_CHANNEL_ID", _ADMIN_CHANNEL_ID_STR) # For global boosts
VC_RENT_CATEGORY_ID_STR = os.getenv("VC_RENT_CATEGORY_ID", None)
VC_RENT_COST_PER_HOUR = int(os.getenv("VC_RENT_COST_PER_HOUR", 500))
HIGH_STAKES_MIN_BET = int(os.getenv("HIGH_STAKES_MIN_BET", 1000))

try:
    SHOPKEEPER_ROLE_ID = int(_SHOPKEEPER_ROLE_ID_STR)
    ADMIN_CHANNEL_ID = int(_ADMIN_CHANNEL_ID_STR)
    LOTTERY_ANNOUNCE_CHANNEL_ID = int(_LOTTERY_ANNOUNCE_CHANNEL_ID_STR)
    ANNOUNCEMENT_CHANNEL_ID = int(ANNOUNCEMENT_CHANNEL_ID_STR)
    VC_RENT_CATEGORY_ID = int(VC_RENT_CATEGORY_ID_STR) if VC_RENT_CATEGORY_ID_STR else None
    if not isinstance(SUPPORTER_ROLE_ID, int) or SUPPORTER_ROLE_ID <= 0: raise ValueError("Hardcoded SUPPORTER_ROLE_ID invalid.")
    if not isinstance(VIP_ROLE_ID, int) or VIP_ROLE_ID <= 0: raise ValueError("Hardcoded VIP_ROLE_ID invalid.")
except ValueError as e:
    logger.critical(f"FATAL: Invalid ID config: {e}"); exit(1)

original_placeholders = { "SHOPKEEPER_ROLE_ID": 987654321098765432, "ADMIN_CHANNEL_ID": 111222333444555666, "SUPPORTER_ROLE_ID": 101010101010101010, "VIP_ROLE_ID": 202020202020202020, "LOTTERY_ANNOUNCE_CHANNEL_ID": 111222333444555666 if _LOTTERY_ANNOUNCE_CHANNEL_ID_STR == "111222333444555666" else None, "ANNOUNCEMENT_CHANNEL_ID": 111222333444555666 if ANNOUNCEMENT_CHANNEL_ID_STR == _ADMIN_CHANNEL_ID_STR and _ADMIN_CHANNEL_ID_STR == "111222333444555666" else None }
current_ids = { "SHOPKEEPER_ROLE_ID": SHOPKEEPER_ROLE_ID, "ADMIN_CHANNEL_ID": ADMIN_CHANNEL_ID, "SUPPORTER_ROLE_ID": SUPPORTER_ROLE_ID, "VIP_ROLE_ID": VIP_ROLE_ID, "LOTTERY_ANNOUNCE_CHANNEL_ID": LOTTERY_ANNOUNCE_CHANNEL_ID, "ANNOUNCEMENT_CHANNEL_ID": ANNOUNCEMENT_CHANNEL_ID }
for name, placeholder_id in original_placeholders.items():
    if placeholder_id is not None and current_ids.get(name) == placeholder_id:
         logger.warning(f"Config Warning: {name} still placeholder ({placeholder_id})."); PLACEHOLDER_IDS_PRESENT = True

# Economy Settings
INITIAL_STARTING_BALANCE = int(os.getenv("INITIAL_STARTING_BALANCE", 1000))
ECONOMY_RESET_THRESHOLD = float(os.getenv("ECONOMY_RESET_THRESHOLD", 1.0e15)) # Default: 1 Quadrillion
DAILY_CLAIM_AMOUNT = int(os.getenv("DAILY_CLAIM_AMOUNT", 100))
SAVINGS_INTEREST_RATE_DAILY = float(os.getenv("SAVINGS_INTEREST_RATE_DAILY", 0.005)) # 0.5%
SAVINGS_INTEREST_MIN_BALANCE = int(os.getenv("SAVINGS_INTEREST_MIN_BALANCE", 100))
GLOBAL_BOOST_MULTIPLIER = 5
GLOBAL_BOOST_DURATION_HOURS = 2
GLOBAL_BOOST_ITEM_COST = 5000
GLOBAL_BOOST_ITEM_ID = "GLOBAL_COIN_BOOST_5X_2HR"

try: LOTTERY_TICKET_PRICE = int(os.getenv("LOTTERY_TICKET_PRICE", 10))
except ValueError: LOTTERY_TICKET_PRICE = 10
try: LOTTERY_INTERVAL_HOURS = float(os.getenv("LOTTERY_INTERVAL_HOURS", 2.0))
except ValueError: LOTTERY_INTERVAL_HOURS = 2.0
SHOP_TIMEZONE_STR = os.getenv("SHOP_TIMEZONE", 'America/Chicago')
try: SHOP_TIMEZONE = pytz.timezone(SHOP_TIMEZONE_STR)
except pytz.UnknownTimeZoneError: SHOP_TIMEZONE = pytz.utc
SHOP_OPEN_HOUR = int(os.getenv("SHOP_OPEN_HOUR", 10)); SHOP_OPEN_MINUTE = int(os.getenv("SHOP_OPEN_MINUTE", 0))
SHOP_CLOSE_HOUR = int(os.getenv("SHOP_CLOSE_HOUR", 21)); SHOP_CLOSE_MINUTE = int(os.getenv("SHOP_CLOSE_MINUTE", 0))
SHOP_OPEN_TIME = time(SHOP_OPEN_HOUR, SHOP_OPEN_MINUTE); SHOP_CLOSE_TIME = time(SHOP_CLOSE_HOUR, SHOP_CLOSE_MINUTE)
SLOT_EMOJIS = ["🍎", "🍊", "🍋", "🍉", "🍇", "🍓", "🍒", "⭐", "💎"]; SLOT_JACKPOT_EMOJI = "💎"
DEFAULT_SLOT_JACKPOT_CONTRIBUTION = 0.10
DEFAULT_SLOT_JACKPOT_OVERRIDE_CHANCE = 0.0
DICE_WIN_MULTIPLIER = 5; REDBLACK_WIN_MULTIPLIER = 1.9; REDBLACK_COOLDOWN_SECONDS = 5
BIG_WIN_THRESHOLD = 100000
SCAN_MESSAGE_LIMIT_PER_CHANNEL = int(os.getenv("SCAN_MESSAGE_LIMIT", 10000))
DATA_DIR = "data"; USER_DATA_FILE = os.path.join(DATA_DIR, "user_balances.json")
SHOP_ITEMS_FILE = os.path.join(DATA_DIR, "shop_items.json"); BOT_DATA_FILE = os.path.join(DATA_DIR, "bot_data.json")
ROULETTE_WHEEL_EMOJIS = ["🔴", "⚫", "🔴", "⚫", "🔴", "⚫", "🔴", "⚫", "🔴", "⚫"]
ROULETTE_POINTER = "📌"

# Card Game Constants & Community Goals
SUITS = ["♠️", "♥️", "♦️", "♣️"]; RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
RANK_VALUES = {rank: i + 2 for i, rank in enumerate(RANKS)}; RANK_VALUES['A'] = 14
POKER_PAYOUTS = { "Royal Flush": 250, "Straight Flush": 50, "Four of a Kind": 25, "Full House": 9, "Flush": 6, "Straight": 4, "Three of a Kind": 3, "Two Pair": 2, "Jacks or Better": 1, }
COMMUNITY_GOALS = { "lottery_donations": {"target": 100000, "reward": "1 Day Double Coin Gain!", "current": 0}, "messages_sent": {"target": 50000, "reward": "Special Lottery Draw!", "current": 0} }

if not DISCORD_BOT_TOKEN: logger.critical("FATAL: Token missing."); exit(1)
os.makedirs(DATA_DIR, exist_ok=True)

# --- Data Persistence ---
user_data = {}; shop_items = {}; bot_data = {}
def load_user_data():
    global user_data
    try:
        with open(USER_DATA_FILE, 'r') as f: loaded_data = json.load(f)
        migrated_data = {}; migration_needed = False
        for user_id_str, data in loaded_data.items():
            try:
                user_id = int(user_id_str)
                if isinstance(data, int): migrated_data[user_id] = {"balance": data, "savings": 0, "pin": None, "last_daily_claim": None}; migration_needed = True
                elif isinstance(data, dict):
                    migrated_data[user_id] = { "balance": data.get("balance", 0), "savings": data.get("savings", 0), "pin": data.get("pin", None), "last_daily_claim": data.get("last_daily_claim", None) }
                    if migrated_data[user_id]["pin"] is not None and not isinstance(migrated_data[user_id]["pin"], str): migrated_data[user_id]["pin"] = None
                else: logger.warning(f"Skipping invalid data for user {user_id_str}"); continue
            except ValueError: logger.warning(f"Skipping invalid user ID key '{user_id_str}'"); continue
        user_data = migrated_data
        if migration_needed: logger.info(f"Migrated user data for daily claim."); save_user_data()
        elif USER_DATA_FILE and os.path.exists(USER_DATA_FILE): logger.info(f"Loaded user data.")
    except FileNotFoundError: logger.warning(f"{USER_DATA_FILE} not found."); user_data = {}
    except json.JSONDecodeError: logger.error(f"Error decoding {USER_DATA_FILE}."); user_data = {}
    except Exception as e: logger.error(f"Error loading user data: {e}"); user_data = {}
def save_user_data():
    try:
        data_to_save = {str(k): v for k, v in user_data.items()}
        with open(USER_DATA_FILE, 'w') as f: json.dump(data_to_save, f, indent=4)
    except Exception as e: logger.error(f"Error saving user data: {e}")
def get_user_data(user_id: int) -> dict:
    user_id = int(user_id)
    if user_id not in user_data:
        user_data[user_id] = {"balance": INITIAL_STARTING_BALANCE, "savings": 0, "pin": None, "last_daily_claim": None}
        logger.info(f"Initialized new user {user_id} with {INITIAL_STARTING_BALANCE} balance.")
    ud = user_data[user_id]
    if "balance" not in ud or not isinstance(ud["balance"], (int, float)): ud["balance"] = 0
    if "savings" not in ud or not isinstance(ud["savings"], (int, float)): ud["savings"] = 0
    if "pin" not in ud or (ud["pin"] is not None and not isinstance(ud["pin"], str)): ud["pin"] = None
    if "last_daily_claim" not in ud: ud["last_daily_claim"] = None
    return user_data[user_id]
def load_shop_items():
    global shop_items
    try:
        with open(SHOP_ITEMS_FILE, 'r') as f: shop_items = json.load(f)
        logger.info(f"Loaded shop items.")
    except FileNotFoundError: logger.warning(f"{SHOP_ITEMS_FILE} not found."); shop_items = {}
    except json.JSONDecodeError: logger.error(f"Error decoding {SHOP_ITEMS_FILE}."); shop_items = {}
    except Exception as e: logger.error(f"Error loading shop items: {e}"); shop_items = {}
def save_shop_items():
    try:
        with open(SHOP_ITEMS_FILE, 'w') as f: json.dump(shop_items, f, indent=4)
    except Exception as e: logger.error(f"Error saving shop items: {e}")
def load_bot_data():
    global bot_data
    default_data = { 
        "slot_jackpot_pool": 0.0, 
        "lottery_pot": 0.0, 
        "lottery_tickets": [], 
        "slot_jackpot_contribution": DEFAULT_SLOT_JACKPOT_CONTRIBUTION, 
        "slot_jackpot_override_chance": DEFAULT_SLOT_JACKPOT_OVERRIDE_CHANCE, 
        "initial_balance_check_done": False, 
        "community_goals_progress": {goal_id: 0 for goal_id in COMMUNITY_GOALS.keys()}, 
        "global_coin_boost_active": False, 
        "global_coin_boost_ends_at": None,
        "rented_vcs": {}
    }
    try:
        with open(BOT_DATA_FILE, 'r') as f: loaded_data = json.load(f)
        bot_data["slot_jackpot_pool"] = float(loaded_data.get("slot_jackpot_pool", default_data["slot_jackpot_pool"]))
        bot_data["lottery_pot"] = float(loaded_data.get("lottery_pot", default_data["lottery_pot"]))
        bot_data["lottery_tickets"] = loaded_data.get("lottery_tickets", default_data["lottery_tickets"])
        contrib = float(loaded_data.get("slot_jackpot_contribution", default_data["slot_jackpot_contribution"]))
        override = float(loaded_data.get("slot_jackpot_override_chance", default_data["slot_jackpot_override_chance"]))
        bot_data["slot_jackpot_contribution"] = max(0.0, min(1.0, contrib))
        bot_data["slot_jackpot_override_chance"] = max(0.0, min(1.0, override))
        bot_data["initial_balance_check_done"] = loaded_data.get("initial_balance_check_done", default_data["initial_balance_check_done"])
        loaded_goals = loaded_data.get("community_goals_progress", {})
        bot_data["community_goals_progress"] = { goal_id: int(loaded_goals.get(goal_id, 0)) for goal_id in COMMUNITY_GOALS.keys() }
        bot_data["global_coin_boost_active"] = loaded_data.get("global_coin_boost_active", default_data["global_coin_boost_active"])
        bot_data["global_coin_boost_ends_at"] = loaded_data.get("global_coin_boost_ends_at", default_data["global_coin_boost_ends_at"])
        bot_data["rented_vcs"] = loaded_data.get("rented_vcs", default_data["rented_vcs"])
        
        if not isinstance(bot_data["slot_jackpot_pool"], float): bot_data["slot_jackpot_pool"] = 0.0
        if not isinstance(bot_data["lottery_pot"], float): bot_data["lottery_pot"] = 0.0
        if not isinstance(bot_data["lottery_tickets"], list): bot_data["lottery_tickets"] = []
        if not isinstance(bot_data["initial_balance_check_done"], bool): bot_data["initial_balance_check_done"] = False
        if not isinstance(bot_data["global_coin_boost_active"], bool): bot_data["global_coin_boost_active"] = False
        if not isinstance(bot_data["rented_vcs"], dict): bot_data["rented_vcs"] = {}
        
        # Convert timestamps from ISO strings to datetime objects
        if bot_data["global_coin_boost_ends_at"] is not None and isinstance(bot_data["global_coin_boost_ends_at"], str):
            try: bot_data["global_coin_boost_ends_at"] = datetime.datetime.fromisoformat(bot_data["global_coin_boost_ends_at"].replace('Z', '+00:00'))
            except (ValueError, TypeError): bot_data["global_coin_boost_ends_at"] = None
        
        # Convert rented_vcs timestamps from ISO strings to datetime objects
        for vc_id, vc_data in bot_data["rented_vcs"].items():
            if "expires_at" in vc_data and isinstance(vc_data["expires_at"], str):
                try: 
                    vc_data["expires_at"] = datetime.datetime.fromisoformat(vc_data["expires_at"].replace('Z', '+00:00'))
                except (ValueError, TypeError): 
                    vc_data["expires_at"] = datetime.datetime.now(timezone.utc) + timedelta(minutes=5)  # Fallback expiration
            
        logger.info(f"Loaded bot data (JP Contrib: {bot_data['slot_jackpot_contribution']:.1%}, JP Override: {bot_data['slot_jackpot_override_chance']:.1%}). Goal progress, Boost, and Rented VCs loaded.")
    except FileNotFoundError: logger.warning(f"{BOT_DATA_FILE} not found."); bot_data = default_data.copy()
    except json.JSONDecodeError: logger.error(f"Error decoding {BOT_DATA_FILE}."); bot_data = default_data.copy()
    except Exception as e: logger.error(f"Error loading bot data: {e}"); bot_data = default_data.copy()
def save_bot_data():
    try:
        data_to_save = bot_data.copy()
        # Convert datetime objects to ISO strings for serialization
        if data_to_save.get("global_coin_boost_ends_at") and isinstance(data_to_save["global_coin_boost_ends_at"], datetime.datetime):
            data_to_save["global_coin_boost_ends_at"] = data_to_save["global_coin_boost_ends_at"].isoformat()
        
        # Convert rented_vcs datetime objects to ISO strings for serialization
        rented_vcs_save = {}
        for vc_id, vc_data in data_to_save.get("rented_vcs", {}).items():
            vc_data_copy = vc_data.copy()
            if "expires_at" in vc_data_copy and isinstance(vc_data_copy["expires_at"], datetime.datetime):
                vc_data_copy["expires_at"] = vc_data_copy["expires_at"].isoformat()
            rented_vcs_save[vc_id] = vc_data_copy
        data_to_save["rented_vcs"] = rented_vcs_save
        
        with open(BOT_DATA_FILE, 'w') as f: json.dump(data_to_save, f, indent=4)
    except Exception as e: logger.error(f"Error saving bot data: {e}")

# --- Helper Functions ---
def get_user_savings(user_id: int) -> tuple:
    ud = get_user_data(user_id)
    if not isinstance(ud["savings"], (int, float)): ud["savings"] = 0
    if not isinstance(ud["balance"], (int, float)): ud["balance"] = 0
    if "pin" not in ud: ud["pin"] = None
    return ud["savings"], ud["balance"], ud["pin"]

def update_user_savings(user_id: int, new_savings: float, new_balance: float = None) -> None:
    ud = get_user_data(user_id)
    ud["savings"] = new_savings
    if new_balance is not None: ud["balance"] = new_balance

def is_shop_open() -> bool:
    now = datetime.datetime.now(SHOP_TIMEZONE)
    open_time = datetime.datetime.combine(now.date(), SHOP_OPEN_TIME).replace(tzinfo=SHOP_TIMEZONE)
    close_time = datetime.datetime.combine(now.date(), SHOP_CLOSE_TIME).replace(tzinfo=SHOP_TIMEZONE)
    if close_time <= open_time: close_time += timedelta(days=1)
    return open_time <= now <= close_time

def get_guild(bot, guild_id: int = None, guild: disnake.Guild = None) -> disnake.Guild:
    if guild: return guild
    if not guild_id and bot.guilds: return bot.guilds[0]
    for g in bot.guilds:
        if g.id == guild_id: return g
    if bot.guilds: return bot.guilds[0]
    return None

def is_supporter(member: disnake.Member) -> bool:
    return any(role.id == SUPPORTER_ROLE_ID for role in member.roles)

def is_vip(member: disnake.Member) -> bool:
    return any(role.id == VIP_ROLE_ID for role in member.roles)

def format_coins(coins: float) -> str:
    if coins >= 1000000000: return f"{coins/1000000000:.2f}B"
    elif coins >= 1000000: return f"{coins/1000000:.2f}M"
    elif coins >= 1000: return f"{coins/1000:.2f}K"
    else: return f"{int(coins)}"

# --- Bot Class Definition ---
class EconomyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_balance_check_done = False
        self.balance_scan_running = False
        self.active_cooldowns = {}
        self.tasks = []
        
    async def on_ready(self):
        logger.info(f'Bot {self.user} is ready!')
        if not bot_data.get("initial_balance_check_done", False) and not self.initial_balance_check_done and not self.balance_scan_running:
            logger.info("Starting initial balance distribution based on message history...")
            self.balance_scan_running = True
            self.loop.create_task(self.scan_message_history())
        
        # Ensure all tasks are started correctly
        self.autosave_data.start()
        self.lottery_drawing.start()
        self.apply_daily_interest.start()
        self.check_global_boost.start()
        self.check_rented_vcs.start()
        
        if PLACEHOLDER_IDS_PRESENT: logger.warning("Bot running with placeholder IDs. Please check .env configuration.")
        
        # Register tasks for clean shutdown
        self.tasks = [
            self.autosave_data,
            self.lottery_drawing,
            self.apply_daily_interest,
            self.check_global_boost,
            self.check_rented_vcs
        ]
        
    async def on_close(self):
        logger.info("Bot is shutting down, canceling tasks...")
        for task in self.tasks:
            if task.is_running():
                task.cancel()
        await save_all_data()
        
    async def scan_message_history(self):
        for guild in self.guilds:
            for channel in guild.text_channels:
                if not channel.permissions_for(guild.me).read_message_history:
                    logger.info(f"Skipping channel {channel.name} - missing permissions")
                    continue
                try:
                    logger.info(f"Scanning history of {channel.name}")
                    message_count = Counter()
                    async for message in channel.history(limit=SCAN_MESSAGE_LIMIT_PER_CHANNEL):
                        if not message.author.bot:
                            message_count[message.author.id] += 1
                    for user_id, count in message_count.items():
                        balance = count
                        ud = get_user_data(user_id)
                        if ud["balance"] < balance: 
                            ud["balance"] = balance
                            logger.info(f"Set user {user_id} initial balance to {balance} based on message count")
                except Exception as e:
                    logger.error(f"Error scanning history of {channel.name}: {e}")
        self.initial_balance_check_done = True
        bot_data["initial_balance_check_done"] = True
        self.balance_scan_running = False
        logger.info("Initial balance scan complete")
        await save_all_data()
        
    @tasks.loop(minutes=5.0)
    async def autosave_data(self):
        await save_all_data()
        await self.check_community_goals()
        
    @tasks.loop(hours=LOTTERY_INTERVAL_HOURS)
    async def lottery_drawing(self):
        if not bot_data.get("lottery_tickets", []): return
        winner_id = random.choice(bot_data["lottery_tickets"])
        pot = bot_data.get("lottery_pot", 0.0)
        try:
            channel = self.get_channel(LOTTERY_ANNOUNCE_CHANNEL_ID)
            if not channel: return
            winner = await self.get_or_fetch_user(winner_id)
            if not winner: return
            ud = get_user_data(winner_id)
            ud["balance"] += pot
            await channel.send(f"🎉 **LOTTERY DRAWING!** 🎉\n{winner.mention} wins {format_coins(pot)} coins from the pot with 1/{len(bot_data['lottery_tickets'])} odds!")
            winner_dm = await winner.create_dm()
            await winner_dm.send(f"🎉 Congratulations! You won {format_coins(pot)} coins in the lottery drawing!")
        except Exception as e: logger.error(f"Error in lottery drawing: {e}")
        finally:
            bot_data["lottery_tickets"] = []
            bot_data["lottery_pot"] = 0.0
            
    @tasks.loop(time=time(hour=0, minute=0))  # Run at midnight UTC
    async def apply_daily_interest(self):
        """Apply daily interest to all savings accounts with balance >= minimum"""
        try:
            applied_count = 0
            total_interest = 0.0
            
            for user_id, user_data_entry in user_data.items():
                if "savings" in user_data_entry and isinstance(user_data_entry["savings"], (int, float)):
                    savings_balance = user_data_entry["savings"]
                    
                    # Apply interest only if balance meets minimum requirement
                    if savings_balance >= SAVINGS_INTEREST_MIN_BALANCE:
                        interest = savings_balance * SAVINGS_INTEREST_RATE_DAILY
                        user_data_entry["savings"] += interest
                        applied_count += 1
                        total_interest += interest
            
            logger.info(f"Applied daily interest to {applied_count} accounts. Total interest: {total_interest:.2f} coins")
            save_user_data()
        except Exception as e:
            logger.error(f"Error applying daily interest: {e}")
    
    @tasks.loop(minutes=1.0)
    async def check_global_boost(self):
        """Check if global coin boost has expired"""
        try:
            if not bot_data.get("global_coin_boost_active", False):
                return
                
            now = datetime.datetime.now(timezone.utc)
            boost_end = bot_data.get("global_coin_boost_ends_at")
            
            if boost_end and now >= boost_end:
                # Boost has expired
                bot_data["global_coin_boost_active"] = False
                bot_data["global_coin_boost_ends_at"] = None
                save_bot_data()
                
                # Announce the end of the boost
                try:
                    channel = self.get_channel(ANNOUNCEMENT_CHANNEL_ID)
                    if channel:
                        await channel.send(f"⏰ The global {GLOBAL_BOOST_MULTIPLIER}x coin boost has ended!")
                except Exception as e:
                    logger.error(f"Failed to announce boost end: {e}")
                
                logger.info("Global coin boost has ended")
        except Exception as e:
            logger.error(f"Error in check_global_boost task: {e}")
    
    @tasks.loop(minutes=1.0)
    async def check_rented_vcs(self):
        """Check for expired rented voice channels and delete them"""
        try:
            if not bot_data.get("rented_vcs"):
                return
                
            now = datetime.datetime.now(timezone.utc)
            expired_vcs = []
            
            for vc_id, vc_data in bot_data["rented_vcs"].items():
                expiry = vc_data.get("expires_at")
                if expiry and now >= expiry:
                    expired_vcs.append(vc_id)
            
            if not expired_vcs:
                return
                
            # Process expired VCs
            for vc_id in expired_vcs:
                try:
                    # Try to get the channel and delete it
                    vc_id_int = int(vc_id)
                    channel = self.get_channel(vc_id_int)
                    if channel:
                        await channel.delete(reason="Rental period expired")
                        logger.info(f"Deleted expired rented VC: {vc_id}")
                    
                    # Remove from bot_data regardless of whether we found the channel
                    # (in case it was manually deleted)
                    if vc_id in bot_data["rented_vcs"]:
                        del bot_data["rented_vcs"][vc_id]
                except Exception as e:
                    logger.error(f"Error deleting expired VC {vc_id}: {e}")
                    # Still remove from bot_data even if deletion fails
                    if vc_id in bot_data["rented_vcs"]:
                        del bot_data["rented_vcs"][vc_id]
            
            # Save changes
            save_bot_data()
        except Exception as e:
            logger.error(f"Error in check_rented_vcs task: {e}")
            
    async def check_community_goals(self):
        try:
            for goal_id, goal_data in COMMUNITY_GOALS.items():
                if goal_id in bot_data["community_goals_progress"]:
                    current = bot_data["community_goals_progress"][goal_id]
                    target = goal_data["target"]
                    if current >= target:
                        channel = self.get_channel(ANNOUNCEMENT_CHANNEL_ID)
                        if channel:
                            await channel.send(f"🎯 **COMMUNITY GOAL ACHIEVED!** 🎯\n{goal_data['reward']}")
                        bot_data["community_goals_progress"][goal_id] = 0
        except Exception as e:
            logger.error(f"Error checking community goals: {e}")

# --- Command Cogs ---
class BalanceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="balance", description="Check your coin balance")
    async def balance(self, inter: disnake.ApplicationCommandInteraction):
        user_id = inter.author.id
        ud = get_user_data(user_id)
        embed = disnake.Embed(title="💰 Your Balance", color=disnake.Color.gold())
        embed.add_field(name="Coins", value=f"{format_coins(ud['balance'])}", inline=True)
        embed.add_field(name="Savings", value=f"{format_coins(ud['savings'])}", inline=True)
        await inter.response.send_message(embed=embed, ephemeral=True)
        
    @commands.slash_command(name="pay", description="Pay coins to another user")
    async def pay(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User, amount: int):
        if amount <= 0:
            await inter.response.send_message("Amount must be positive.", ephemeral=True)
            return
        sender_id = inter.author.id
        receiver_id = user.id
        if sender_id == receiver_id:
            await inter.response.send_message("You can't pay yourself.", ephemeral=True)
            return
        if user.bot:
            await inter.response.send_message("You can't pay bots.", ephemeral=True)
            return
        sender_data = get_user_data(sender_id)
        if sender_data["balance"] < amount:
            await inter.response.send_message(f"You don't have enough coins! You have {format_coins(sender_data['balance'])}.", ephemeral=True)
            return
        receiver_data = get_user_data(receiver_id)
        sender_data["balance"] -= amount
        receiver_data["balance"] += amount
        await inter.response.send_message(f"💸 {inter.author.mention} paid {user.mention} {format_coins(amount)} coins!")
        
    @commands.slash_command(name="daily", description="Claim your daily coins")
    async def daily(self, inter: disnake.ApplicationCommandInteraction):
        user_id = inter.author.id
        ud = get_user_data(user_id)
        
        now = datetime.datetime.now(timezone.utc)
        
        # Check if user has claimed within the last 24 hours
        if ud["last_daily_claim"]:
            try:
                last_claim = datetime.datetime.fromisoformat(ud["last_daily_claim"].replace('Z', '+00:00'))
                time_since_claim = now - last_claim
                
                # Calculate time remaining until next claim
                if time_since_claim < timedelta(hours=23, minutes=55):  # Slightly less than 24h for buffer
                    next_claim_time = last_claim + timedelta(hours=24)
                    time_remaining = next_claim_time - now
                    hours, remainder = divmod(time_remaining.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    await inter.response.send_message(
                        f"⏱️ You've already claimed your daily coins today. Try again in {hours}h {minutes}m.",
                        ephemeral=True
                    )
                    return
            except (ValueError, TypeError):
                # If timestamp is invalid, reset it
                ud["last_daily_claim"] = None
        
        # Award coins and update timestamp
        ud["balance"] += DAILY_CLAIM_AMOUNT
        ud["last_daily_claim"] = now.isoformat()
        save_user_data()
        
        await inter.response.send_message(
            f"🎁 {inter.author.mention} claimed their daily reward of {DAILY_CLAIM_AMOUNT} coins!"
        )
        
    @commands.slash_command(name="leaderboard", description="View the server's coin leaderboard")
    async def leaderboard(self, inter: disnake.ApplicationCommandInteraction, type: str = commands.Param(choices=["balance", "savings"])):
        await inter.response.defer()
        
        sorted_data = []
        
        # Build the sorted leaderboard data
        for user_id, data in user_data.items():
            try:
                user = await self.bot.get_or_fetch_user(int(user_id))
                if user and not user.bot:
                    sorted_data.append((
                        user.display_name,
                        data.get("balance", 0) if type == "balance" else data.get("savings", 0)
                    ))
            except:
                continue
        
        # Sort by coin amount (descending)
        sorted_data.sort(key=lambda x: x[1], reverse=True)
        
        # Create the embed
        embed = disnake.Embed(
            title=f"🏆 {type.capitalize()} Leaderboard",
            color=disnake.Color.gold()
        )
        
        # Add top 10 entries to the embed
        for i, (name, amount) in enumerate(sorted_data[:10], 1):
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{format_coins(amount)} coins",
                inline=False
            )
        
        await inter.edit_original_message(embed=embed)
        
class SavingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="savings")
    async def savings_group(self, inter: disnake.ApplicationCommandInteraction):
        """Manage your savings account"""
        pass
        
    @savings_group.sub_command(name="setpin", description="Set or change your savings account PIN")
    async def setpin(self, inter: disnake.ApplicationCommandInteraction, pin: str = commands.Param(min_length=4, max_length=4)):
        user_id = inter.author.id
        if not pin.isdigit():
            await inter.response.send_message("PIN must be a 4-digit number.", ephemeral=True)
            return
            
        ud = get_user_data(user_id)
        old_pin = ud.get("pin")
        ud["pin"] = pin
        
        await inter.response.send_message(
            f"{'Changed your savings account PIN.' if old_pin else 'Set up your savings account PIN.'} Keep it secret!",
            ephemeral=True
        )
        save_user_data()
        
    @savings_group.sub_command(name="balance", description="Check your savings account balance")
    async def savings_balance(self, inter: disnake.ApplicationCommandInteraction, pin: str = commands.Param(min_length=4, max_length=4)):
        user_id = inter.author.id
        savings, balance, stored_pin = get_user_savings(user_id)
        
        if not stored_pin:
            await inter.response.send_message("You haven't set up a PIN for your savings account yet. Use `/savings setpin` first.", ephemeral=True)
            return
            
        if pin != stored_pin:
            await inter.response.send_message("Incorrect PIN.", ephemeral=True)
            return
            
        embed = disnake.Embed(
            title="🏦 Savings Account",
            description=f"Your current savings: {format_coins(savings)} coins\n"
                       f"Daily interest rate: {SAVINGS_INTEREST_RATE_DAILY:.1%} (min balance: {SAVINGS_INTEREST_MIN_BALANCE})",
            color=disnake.Color.blue()
        )
        
        await inter.response.send_message(embed=embed, ephemeral=True)
        
    @savings_group.sub_command(name="deposit", description="Deposit coins into your savings account")
    async def deposit(self, inter: disnake.ApplicationCommandInteraction, amount: int, pin: str = commands.Param(min_length=4, max_length=4)):
        user_id = inter.author.id
        
        if amount <= 0:
            await inter.response.send_message("Amount must be positive.", ephemeral=True)
            return
            
        savings, balance, stored_pin = get_user_savings(user_id)
        
        if not stored_pin:
            await inter.response.send_message("You haven't set up a PIN for your savings account yet. Use `/savings setpin` first.", ephemeral=True)
            return
            
        if pin != stored_pin:
            await inter.response.send_message("Incorrect PIN.", ephemeral=True)
            return
            
        if balance < amount:
            await inter.response.send_message(f"You don't have enough coins. Current balance: {format_coins(balance)}", ephemeral=True)
            return
            
        # Transfer the funds
        update_user_savings(user_id, savings + amount, balance - amount)
        save_user_data()
        
        await inter.response.send_message(
            f"Deposited {format_coins(amount)} coins to your savings account.\n"
            f"New savings balance: {format_coins(savings + amount)}\n"
            f"Main balance: {format_coins(balance - amount)}",
            ephemeral=True
        )
        
    @savings_group.sub_command(name="withdraw", description="Withdraw coins from your savings account")
    async def withdraw(self, inter: disnake.ApplicationCommandInteraction, amount: int, pin: str = commands.Param(min_length=4, max_length=4)):
        user_id = inter.author.id
        
        if amount <= 0:
            await inter.response.send_message("Amount must be positive.", ephemeral=True)
            return
            
        savings, balance, stored_pin = get_user_savings(user_id)
        
        if not stored_pin:
            await inter.response.send_message("You haven't set up a PIN for your savings account yet. Use `/savings setpin` first.", ephemeral=True)
            return
            
        if pin != stored_pin:
            await inter.response.send_message("Incorrect PIN.", ephemeral=True)
            return
            
        if savings < amount:
            await inter.response.send_message(f"You don't have enough coins in savings. Current savings: {format_coins(savings)}", ephemeral=True)
            return
            
        # Transfer the funds
        update_user_savings(user_id, savings - amount, balance + amount)
        save_user_data()
        
        await inter.response.send_message(
            f"Withdrew {format_coins(amount)} coins from your savings account.\n"
            f"New savings balance: {format_coins(savings - amount)}\n"
            f"Main balance: {format_coins(balance + amount)}",
            ephemeral=True
        )
        
class GamblingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="gamble")
    async def gamble_group(self, inter: disnake.ApplicationCommandInteraction):
        """Regular gambling games"""
        pass
        
    @gamble_group.sub_command(name="slots", description="Bet coins on the slot machine")
    async def slots(self, inter: disnake.ApplicationCommandInteraction, amount: int = commands.Param(ge=10)):
        user_id = inter.author.id
        ud = get_user_data(user_id)
        
        if amount <= 0:
            await inter.response.send_message("Bet amount must be positive.", ephemeral=True)
            return
            
        if ud["balance"] < amount:
            await inter.response.send_message(f"Not enough coins. You have {format_coins(ud['balance'])}.", ephemeral=True)
            return
            
        ud["balance"] -= amount
        
        # Prepare the animation
        await inter.response.defer()
        
        # Initial fast spins (all reels spinning)
        msg = await inter.edit_original_message(content=f"🎰 **SLOTS** 🎰\nBet: {format_coins(amount)}\n\n"+"".join(random.choice(SLOT_EMOJIS) for _ in range(3)))
        
        # Determine final result - check for jackpot override
        jackpot_chance = bot_data.get("slot_jackpot_override_chance", DEFAULT_SLOT_JACKPOT_OVERRIDE_CHANCE)
        if random.random() < jackpot_chance:
            final_icons = [SLOT_JACKPOT_EMOJI, SLOT_JACKPOT_EMOJI, SLOT_JACKPOT_EMOJI]
        else:
            final_icons = [random.choice(SLOT_EMOJIS) for _ in range(3)]
        
        # Ultra-fast initial spinning (all reels at once)
        # This creates a blur effect with very rapid updates
        fast_spin_frames = 30
        for i in range(fast_spin_frames):
            try:
                # Update every 0.02 seconds (50 times per second)
                await asyncio.sleep(0.02)
                await msg.edit(content=f"🎰 **SLOTS** 🎰\nBet: {format_coins(amount)}\n\n"+"".join(random.choice(SLOT_EMOJIS) for _ in range(3)))
            except:
                # In case of rate limit, continue
                pass
        
        # Stop first reel (still spinning other reels fast)
        first_reel = final_icons[0]
        medium_spin_frames = 20
        for i in range(medium_spin_frames):
            try:
                await asyncio.sleep(0.05)  # Slightly slower now
                reels = [first_reel] + [random.choice(SLOT_EMOJIS) for _ in range(2)]
                await msg.edit(content=f"🎰 **SLOTS** 🎰\nBet: {format_coins(amount)}\n\n"+"".join(reels))
            except:
                pass
            
        # Slow down second reel (still spinning third reel)
        second_reel = final_icons[1]
        slow_spin_frames = 15
        for i in range(slow_spin_frames):
            try:
                await asyncio.sleep(0.08)  # Even slower
                reels = [first_reel, second_reel, random.choice(SLOT_EMOJIS)]
                await msg.edit(content=f"🎰 **SLOTS** 🎰\nBet: {format_coins(amount)}\n\n"+"".join(reels))
            except:
                pass
            
        # Final dramatic pause before showing third reel
        await asyncio.sleep(0.5)
        
        # Tease the final result with a few slower spins
        final_teases = 5
        for i in range(final_teases):
            await asyncio.sleep(0.3)
            reels = [first_reel, second_reel, random.choice(SLOT_EMOJIS)]
            await msg.edit(content=f"🎰 **SLOTS** 🎰\nBet: {format_coins(amount)}\n\n"+"".join(reels))
            
        # Final result - stop third reel
        third_reel = final_icons[2]
        reels = [first_reel, second_reel, third_reel]
        
        # Dramatic pause
        await asyncio.sleep(0.8)
            
        # Calculate winnings
        if reels.count(reels[0]) == 3:  # Three of a kind
            if reels[0] == SLOT_JACKPOT_EMOJI:  # Jackpot
                jackpot = bot_data.get("slot_jackpot_pool", 0)
                win_amount = amount + (jackpot * 0.5)
                bot_data["slot_jackpot_pool"] = jackpot * 0.5  # 50% of jackpot remains
                result = f"💎 **JACKPOT!** 💎\nYou won {format_coins(win_amount)}! (Bet + 50% of Jackpot Pool)"
                ud["balance"] += win_amount
                
                # Check for big win announcement
                if win_amount > BIG_WIN_THRESHOLD:
                    self.bot.loop.create_task(self.announce_big_win(inter.author, win_amount, "slots jackpot"))
            else:
                win_amount = amount * 5
                result = f"🎉 **THREE OF A KIND!** 🎉\nYou won {format_coins(win_amount)}!"
                ud["balance"] += win_amount
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:  # Pair
            win_amount = amount * 2
            result = f"🎉 **PAIR!** 🎉\nYou won {format_coins(win_amount)}!"
            ud["balance"] += win_amount
        else:  # Loss
            result = "😢 No match. Better luck next time!"
            # Contribute to jackpot
            contribution_rate = bot_data.get("slot_jackpot_contribution", DEFAULT_SLOT_JACKPOT_CONTRIBUTION)
            bot_data["slot_jackpot_pool"] = bot_data.get("slot_jackpot_pool", 0) + (amount * contribution_rate)
            
        # Final message with result
        await msg.edit(content=f"🎰 **SLOTS** 🎰\nBet: {format_coins(amount)}\n\n"+"".join(reels)+f"\n\n{result}")
        
    @gamble_group.sub_command(name="dice", description="Bet on a dice roll")
    async def dice(self, inter: disnake.ApplicationCommandInteraction, guess: int = commands.Param(ge=1, le=6), amount: int = commands.Param(ge=10)):
        user_id = inter.author.id
        ud = get_user_data(user_id)
        
        if amount <= 0:
            await inter.response.send_message("Bet amount must be positive.", ephemeral=True)
            return
            
        if ud["balance"] < amount:
            await inter.response.send_message(f"Not enough coins. You have {format_coins(ud['balance'])}.", ephemeral=True)
            return
            
        # Place bet
        ud["balance"] -= amount
        
        # Roll dice
        roll = random.randint(1, 6)
        
        # Check result
        if roll == guess:
            win_amount = amount * DICE_WIN_MULTIPLIER
            ud["balance"] += win_amount
            result = f"🎲 You rolled a **{roll}**!\n\n🎉 **WINNER!** 🎉\nYou guessed correctly and won {format_coins(win_amount)}!"
            
            # Check for big win announcement
            if win_amount > BIG_WIN_THRESHOLD:
                self.bot.loop.create_task(self.announce_big_win(inter.author, win_amount, "dice"))
        else:
            result = f"🎲 You rolled a **{roll}**!\n\nYou guessed {guess}, but rolled {roll}. Better luck next time!"
            
        dice_emojis = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        await inter.response.send_message(
            f"🎲 **DICE** 🎲\nBet: {format_coins(amount)} on {guess}\n\n{dice_emojis[roll-1]} {result}"
        )
        
    @gamble_group.sub_command(name="redblack", description="Bet on red or black")
    async def redblack(self, inter: disnake.ApplicationCommandInteraction, 
                       choice: str = commands.Param(choices=["red", "black"]), 
                       amount: int = commands.Param(ge=10)):
        user_id = inter.author.id
        ud = get_user_data(user_id)
        
        # Check cooldown
        if user_id in self.bot.active_cooldowns.get("redblack", {}):
            cooldown_end = self.bot.active_cooldowns["redblack"][user_id]
            if datetime.datetime.now() < cooldown_end:
                seconds_left = (cooldown_end - datetime.datetime.now()).total_seconds()
                await inter.response.send_message(f"Please wait {seconds_left:.1f} seconds before playing again.", ephemeral=True)
                return
                
        # Add to cooldown
        if "redblack" not in self.bot.active_cooldowns:
            self.bot.active_cooldowns["redblack"] = {}
        self.bot.active_cooldowns["redblack"][user_id] = datetime.datetime.now() + timedelta(seconds=REDBLACK_COOLDOWN_SECONDS)
        
        if amount <= 0:
            await inter.response.send_message("Bet amount must be positive.", ephemeral=True)
            return
            
        if ud["balance"] < amount:
            await inter.response.send_message(f"Not enough coins. You have {format_coins(ud['balance'])}.", ephemeral=True)
            return
            
        # Place bet
        ud["balance"] -= amount
        
        # Generate result
        number = random.randint(1, 36)
        result_color = "red" if number % 2 == 0 else "black"
        
        # Check win
        if result_color == choice:
            win_amount = int(amount * REDBLACK_WIN_MULTIPLIER)
            ud["balance"] += win_amount
            result_msg = f"The ball landed on {number} {result_color}!\n\n🎉 **WINNER!** 🎉\nYou won {format_coins(win_amount)}!"
            
            # Check for big win announcement
            if win_amount > BIG_WIN_THRESHOLD:
                self.bot.loop.create_task(self.announce_big_win(inter.author, win_amount, "red/black"))
        else:
            result_msg = f"The ball landed on {number} {result_color}!\n\nYou bet on {choice}. Better luck next time!"
            
        await inter.response.send_message(
            f"🎮 **RED/BLACK** 🎮\nBet: {format_coins(amount)} on {choice}\n\n{result_msg}"
        )
        
    @gamble_group.sub_command(name="wheel", description="Spin the wheel and win!")
    async def wheel(self, inter: disnake.ApplicationCommandInteraction, 
                   choice: str = commands.Param(choices=["red", "black"]), 
                   amount: int = commands.Param(ge=10)):
        """Spin the wheel and bet on red or black
        
        Parameters
        ----------
        choice: Which color to bet on (red or black)
        amount: Amount of coins to bet
        """
        user_id = inter.author.id
        ud = get_user_data(user_id)
        
        if amount <= 0:
            await inter.response.send_message("Bet amount must be positive.", ephemeral=True)
            return
            
        if ud["balance"] < amount:
            await inter.response.send_message(f"Not enough coins. You have {format_coins(ud['balance'])}.", ephemeral=True)
            return
            
        # Place bet
        ud["balance"] -= amount
        save_user_data()
        
        # Defer to allow for animation
        await inter.response.defer()
        
        # Wheel animation
        wheel_size = len(ROULETTE_WHEEL_EMOJIS)
        visible_section = 5  # Show 5 sections with pointer in the middle
        
        # Random result (for simplicity, just red or black)
        final_result = random.choice(["red", "black"])
        win_multiplier = 1.8
        
        # Initial message
        wheel_display = "⚫️🔴⚫️" + ROULETTE_POINTER + "🔴⚫️🔴"
        msg = await inter.edit_original_message(content=f"🎡 **WHEEL OF FORTUNE** 🎡\nBet: {format_coins(amount)} on {choice}\n\n{wheel_display}\n\nSpinning...")
        
        # Animation phases - very fast -> fast -> medium -> slow -> very slow
        # Phase 1: Ultra-fast initial spins (0.05s each)
        fast_frames = 15
        for i in range(fast_frames):
            try:
                # Create the wheel display for this frame
                start_idx = (i * 4) % wheel_size  # Move 4 steps each time for faster appearance
                section = []
                for j in range(visible_section):
                    idx = (start_idx + j) % wheel_size
                    if j == visible_section // 2:  # Middle position
                        section.append(ROULETTE_POINTER)
                    section.append(ROULETTE_WHEEL_EMOJIS[idx])
                
                wheel_display = "".join(section)
                
                await asyncio.sleep(0.05)  # Very fast
                await msg.edit(content=f"🎡 **WHEEL OF FORTUNE** 🎡\nBet: {format_coins(amount)} on {choice}\n\n{wheel_display}\n\nSpinning...")
            except:
                # In case of rate limit, continue
                pass
                
        # Phase 2: Slightly slower spins (0.1s each)
        medium_frames = 10
        for i in range(medium_frames):
            try:
                start_idx = (fast_frames * 4 + i * 3) % wheel_size  # Continue from where we left off
                section = []
                for j in range(visible_section):
                    idx = (start_idx + j) % wheel_size
                    if j == visible_section // 2:
                        section.append(ROULETTE_POINTER)
                    section.append(ROULETTE_WHEEL_EMOJIS[idx])
                
                wheel_display = "".join(section)
                
                await asyncio.sleep(0.1)  # Medium speed
                await msg.edit(content=f"🎡 **WHEEL OF FORTUNE** 🎡\nBet: {format_coins(amount)} on {choice}\n\n{wheel_display}\n\nSpinning...")
            except:
                pass
        
        # Phase 3: Gradually slowing down (increasing delay each time)
        slow_frames = 8
        for i in range(slow_frames):
            # Delay increases with each frame: 0.2s, 0.35s, 0.5s, 0.65s...
            delay = 0.2 + (i * 0.15)
            
            start_idx = (fast_frames * 4 + medium_frames * 3 + i * 2) % wheel_size
            section = []
            for j in range(visible_section):
                idx = (start_idx + j) % wheel_size
                if j == visible_section // 2:
                    section.append(ROULETTE_POINTER)
                section.append(ROULETTE_WHEEL_EMOJIS[idx])
            
            wheel_display = "".join(section)
            
            await asyncio.sleep(delay)
            await msg.edit(content=f"🎡 **WHEEL OF FORTUNE** 🎡\nBet: {format_coins(amount)} on {choice}\n\n{wheel_display}\n\nSpinning...")
        
        # Phase 4: Final slow ticks before result
        final_frames = 5
        for i in range(final_frames):
            delay = 0.8 + (i * 0.2)  # Very slow: 0.8s, 1.0s, 1.2s, 1.4s, 1.6s
            
            start_idx = (fast_frames * 4 + medium_frames * 3 + slow_frames * 2 + i) % wheel_size
            section = []
            for j in range(visible_section):
                idx = (start_idx + j) % wheel_size
                if j == visible_section // 2:
                    section.append(ROULETTE_POINTER)
                section.append(ROULETTE_WHEEL_EMOJIS[idx])
            
            wheel_display = "".join(section)
            
            await asyncio.sleep(delay)
            await msg.edit(content=f"🎡 **WHEEL OF FORTUNE** 🎡\nBet: {format_coins(amount)} on {choice}\n\n{wheel_display}\n\nSpinning...")
        
        # Final result display
        final_color_emoji = "🔴" if final_result == "red" else "⚫️"
        
        # Check if the player won
        if final_result == choice:
            win_amount = int(amount * win_multiplier)
            ud = get_user_data(user_id)  # Refresh user data
            ud["balance"] += win_amount
            save_user_data()
            result_text = f"The wheel stopped on {final_color_emoji}!\n\n🎉 **WINNER!** 🎉\nYou won {format_coins(win_amount)}!"
            
            # Check for big win
            if win_amount > BIG_WIN_THRESHOLD:
                self.bot.loop.create_task(self.announce_big_win(inter.author, win_amount, "wheel"))
        else:
            result_text = f"The wheel stopped on {final_color_emoji}!\n\nBetter luck next time!"
            
        await msg.edit(content=f"🎡 **WHEEL OF FORTUNE** 🎡\nBet: {format_coins(amount)} on {choice}\n\n{wheel_display}\n\n{result_text}")
        
    @gamble_group.sub_command(name="blackjack", description="Play a game of blackjack")
    async def blackjack(self, inter: disnake.ApplicationCommandInteraction, amount: int = commands.Param(ge=10)):
        user_id = inter.author.id
        ud = get_user_data(user_id)
        
        if amount <= 0:
            await inter.response.send_message("Bet amount must be positive.", ephemeral=True)
            return
            
        if ud["balance"] < amount:
            await inter.response.send_message(f"Not enough coins. You have {format_coins(ud['balance'])}.", ephemeral=True)
            return
            
        # Deduct bet amount from balance
        ud["balance"] -= amount
        save_user_data()
        
        # Card values
        card_values = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, 
            "J": 10, "Q": 10, "K": 10, "A": 11
        }
        
        # Create deck
        suits = ["♠️", "♥️", "♦️", "♣️"]
        values = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        deck = [f"{v}{s}" for s in suits for v in values]
        random.shuffle(deck)
        
        # Initial deal
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        
        # Function to calculate hand value
        def calculate_hand(hand):
            value = 0
            aces = 0
            
            for card in hand:
                card_value = card[:-1]  # Remove suit
                value += card_values[card_value]
                if card_value == "A":
                    aces += 1
                    
            # Adjust for aces
            while value > 21 and aces > 0:
                value -= 10
                aces -= 1
                
            return value
        
        # Initial hand display
        player_value = calculate_hand(player_hand)
        dealer_visible_value = card_values[dealer_hand[0][:-1]]  # Only show first card
        
        await inter.response.send_message(
            f"🃏 **Blackjack** 🃏\nBet: {format_coins(amount)}\n\n"
            f"Your hand: {' '.join(player_hand)} (Value: {player_value})\n"
            f"Dealer's hand: {dealer_hand[0]} ?? (Showing: {dealer_visible_value})\n\n"
            "Choose your action:"
        )
        
        # Create view with Hit/Stand buttons
        class BlackjackView(disnake.ui.View):
            def __init__(self, cog, deck, player_hand, dealer_hand):
                super().__init__(timeout=60.0)
                self.cog = cog
                self.deck = deck
                self.player_hand = player_hand
                self.dealer_hand = dealer_hand
                self.game_over = False
                
            @disnake.ui.button(label="Hit", style=disnake.ButtonStyle.primary, emoji="👊")
            async def hit_button(self, button: disnake.ui.Button, button_inter: disnake.MessageInteraction):
                if button_inter.author.id != inter.author.id:
                    await button_inter.response.send_message("This isn't your game!", ephemeral=True)
                    return
                    
                # Draw card
                self.player_hand.append(self.deck.pop())
                player_value = calculate_hand(self.player_hand)
                
                # Check if bust
                if player_value > 21:
                    self.game_over = True
                    dealer_value = calculate_hand(self.dealer_hand)
                    
                    await button_inter.response.edit_message(
                        content=f"🃏 **Blackjack** 🃏\nBet: {format_coins(amount)}\n\n"
                        f"Your hand: {' '.join(self.player_hand)} (Value: {player_value})\n"
                        f"Dealer's hand: {' '.join(self.dealer_hand)} (Value: {dealer_value})\n\n"
                        f"Bust! You went over 21 and lost {format_coins(amount)}.",
                        view=None
                    )
                    return
                    
                # Update display
                dealer_visible_value = card_values[self.dealer_hand[0][:-1]]
                await button_inter.response.edit_message(
                    content=f"🃏 **Blackjack** 🃏\nBet: {format_coins(amount)}\n\n"
                    f"Your hand: {' '.join(self.player_hand)} (Value: {player_value})\n"
                    f"Dealer's hand: {self.dealer_hand[0]} ?? (Showing: {dealer_visible_value})\n\n"
                    "Choose your action:"
                )
                
            @disnake.ui.button(label="Stand", style=disnake.ButtonStyle.primary, emoji="✋")
            async def stand_button(self, button: disnake.ui.Button, button_inter: disnake.MessageInteraction):
                if button_inter.author.id != inter.author.id:
                    await button_inter.response.send_message("This isn't your game!", ephemeral=True)
                    return
                    
                self.game_over = True
                player_value = calculate_hand(self.player_hand)
                dealer_value = calculate_hand(self.dealer_hand)
                
                # Dealer draws until 17 or higher
                dealer_draws = []
                while dealer_value < 17:
                    new_card = self.deck.pop()
                    self.dealer_hand.append(new_card)
                    dealer_draws.append(new_card)
                    dealer_value = calculate_hand(self.dealer_hand)
                
                # Determine winner
                result = ""
                win_amount = 0
                
                if dealer_value > 21:
                    # Dealer busts
                    win_amount = amount * 2
                    result = f"Dealer busts! You won {format_coins(win_amount - amount)}!"
                elif dealer_value > player_value:
                    # Dealer wins
                    result = f"Dealer wins. You lost {format_coins(amount)}."
                elif dealer_value < player_value:
                    # Player wins
                    win_amount = amount * 2
                    result = f"You win! You won {format_coins(win_amount - amount)}!"
                else:
                    # Push (tie)
                    win_amount = amount
                    result = "Push! Your bet has been returned."
                    
                # Award winnings if any
                if win_amount > 0:
                    ud = get_user_data(inter.author.id)
                    ud["balance"] += win_amount
                    save_user_data()
                    
                # Special message for blackjack (21 with 2 cards)
                if len(self.player_hand) == 2 and player_value == 21:
                    result = f"Blackjack! You won {format_coins(int(amount * 2.5) - amount)}!"
                    
                dealer_draw_text = ""
                if dealer_draws:
                    dealer_draw_text = f"Dealer drew: {' '.join(dealer_draws)}\n"
                    
                await button_inter.response.edit_message(
                    content=f"🃏 **Blackjack** 🃏\nBet: {format_coins(amount)}\n\n"
                    f"Your hand: {' '.join(self.player_hand)} (Value: {player_value})\n"
                    f"Dealer's hand: {' '.join(self.dealer_hand)} (Value: {dealer_value})\n"
                    f"{dealer_draw_text}\n"
                    f"{result}",
                    view=None
                )
                
            async def on_timeout(self):
                if not self.game_over:
                    self.game_over = True
                    player_value = calculate_hand(self.player_hand)
                    dealer_value = calculate_hand(self.dealer_hand)
                    
                    try:
                        await inter.edit_original_message(
                            content=f"🃏 **Blackjack** 🃏\nBet: {format_coins(amount)}\n\n"
                            f"Your hand: {' '.join(self.player_hand)} (Value: {player_value})\n"
                            f"Dealer's hand: {' '.join(self.dealer_hand)} (Value: {dealer_value})\n\n"
                            f"Game timed out. You lost {format_coins(amount)}.",
                            view=None
                        )
                    except:
                        pass
        
        # Start game
        view = BlackjackView(self, deck, player_hand, dealer_hand)
        await inter.edit_original_message(view=view)
        
    @gamble_group.sub_command(name="poker", description="Play a game of five card draw poker")
    async def poker(self, inter: disnake.ApplicationCommandInteraction, amount: int = commands.Param(ge=10)):
        user_id = inter.author.id
        ud = get_user_data(user_id)
        
        if amount <= 0:
            await inter.response.send_message("Bet amount must be positive.", ephemeral=True)
            return
            
        if ud["balance"] < amount:
            await inter.response.send_message(f"Not enough coins. You have {format_coins(ud['balance'])}.", ephemeral=True)
            return
            
        # Deduct bet amount from balance
        ud["balance"] -= amount
        save_user_data()
        
        # Create deck and deal cards
        suits = ["♠️", "♥️", "♦️", "♣️"]
        values = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        deck = [f"{v}{s}" for s in suits for v in values]
        random.shuffle(deck)
        
        hand = [deck.pop() for _ in range(5)]
        hand.sort(key=lambda card: values.index(card[:-1]))  # Sort by value
        
        await inter.response.send_message(
            f"🃏 **Five Card Draw Poker** 🃏\nBet: {format_coins(amount)}\n\n"
            f"Your hand: {' '.join(hand)}\n\n"
            "Select cards to discard:"
        )
        
        # Create discard options
        class PokerView(disnake.ui.View):
            def __init__(self, cog, deck, hand):
                super().__init__(timeout=60.0)
                self.cog = cog
                self.deck = deck
                self.hand = hand
                self.discard_selections = [False] * 5
                
                # Card toggle buttons
                for i in range(5):
                    button = disnake.ui.Button(
                        label=f"Card {i+1}", 
                        style=disnake.ButtonStyle.secondary,
                        custom_id=f"card_{i}"
                    )
                    button.callback = self.card_toggle
                    self.add_item(button)
                    
                # Draw button
                draw_button = disnake.ui.Button(
                    label="Draw", 
                    style=disnake.ButtonStyle.primary,
                    emoji="🎴"
                )
                draw_button.callback = self.draw_cards
                self.add_item(draw_button)
                
            async def card_toggle(self, button_inter: disnake.MessageInteraction):
                if button_inter.author.id != inter.author.id:
                    await button_inter.response.send_message("This isn't your game!", ephemeral=True)
                    return
                    
                card_idx = int(button_inter.component.custom_id.split("_")[1])
                self.discard_selections[card_idx] = not self.discard_selections[card_idx]
                
                # Update highlighted cards
                hand_display = []
                for i, card in enumerate(self.hand):
                    if self.discard_selections[i]:
                        hand_display.append(f"[{card}]")  # Highlight selected cards
                    else:
                        hand_display.append(card)
                        
                await button_inter.response.edit_message(
                    content=f"🃏 **Five Card Draw Poker** 🃏\nBet: {format_coins(amount)}\n\n"
                    f"Your hand: {' '.join(hand_display)}\n\n"
                    "Select cards to discard:"
                )
                
            async def draw_cards(self, button_inter: disnake.MessageInteraction):
                if button_inter.author.id != inter.author.id:
                    await button_inter.response.send_message("This isn't your game!", ephemeral=True)
                    return
                    
                # Discard and draw new cards
                discarded_indices = [i for i, selected in enumerate(self.discard_selections) if selected]
                
                for i in sorted(discarded_indices, reverse=True):
                    self.hand.pop(i)
                    
                for _ in range(len(discarded_indices)):
                    self.hand.append(self.deck.pop())
                    
                self.hand.sort(key=lambda card: values.index(card[:-1]))  # Sort by value
                
                # Evaluate poker hand
                hand_rank, description = self.evaluate_poker_hand(self.hand)
                
                # Set win multiplier based on hand rank
                multipliers = {
                    "High Card": 0,
                    "One Pair": 1,
                    "Two Pair": 2,
                    "Three of a Kind": 3,
                    "Straight": 4,
                    "Flush": 5,
                    "Full House": 8,
                    "Four of a Kind": 15,
                    "Straight Flush": 50,
                    "Royal Flush": 250
                }
                
                win_amount = 0
                multiplier = multipliers.get(hand_rank, 0)
                
                if multiplier > 0:
                    win_amount = amount * multiplier
                    ud = get_user_data(inter.author.id)
                    ud["balance"] += win_amount
                    save_user_data()
                    
                    result = f"**{hand_rank}!** {description}\nPayout: {multiplier}x\nYou won {format_coins(win_amount)}!"
                else:
                    result = f"**{hand_rank}.** {description}\nNo payout for this hand. You lost {format_coins(amount)}."
                
                await button_inter.response.edit_message(
                    content=f"🃏 **Five Card Draw Poker** 🃏\nBet: {format_coins(amount)}\n\n"
                    f"Your hand: {' '.join(self.hand)}\n\n"
                    f"{result}",
                    view=None
                )
                
            def evaluate_poker_hand(self, cards):
                # Extract values and suits
                card_values = [card[:-1] for card in cards]
                card_suits = [card[-1] for card in cards]
                
                # Convert face cards to numerical values for straights
                value_order = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
                numerical_values = [value_order[v] for v in card_values]
                numerical_values.sort()
                
                # Check for flush (all same suit)
                is_flush = len(set(card_suits)) == 1
                
                # Check for straight (consecutive values)
                is_straight = (len(set(numerical_values)) == 5 and max(numerical_values) - min(numerical_values) == 4)
                
                # Special case: A-2-3-4-5 straight
                if set(numerical_values) == {2, 3, 4, 5, 14}:
                    is_straight = True
                    
                # Count values
                value_counts = Counter(card_values)
                counts = sorted(value_counts.values(), reverse=True)
                
                # Check for royal flush
                royal_values = {"10", "J", "Q", "K", "A"}
                is_royal = is_flush and is_straight and set(card_values) == royal_values
                
                if is_royal:
                    return "Royal Flush", "10 through Ace of the same suit"
                    
                if is_flush and is_straight:
                    return "Straight Flush", "Five consecutive cards of the same suit"
                    
                if counts == [4, 1]:
                    four_kind = [v for v, count in value_counts.items() if count == 4][0]
                    return "Four of a Kind", f"Four {four_kind}'s"
                    
                if counts == [3, 2]:
                    three_kind = [v for v, count in value_counts.items() if count == 3][0]
                    pair = [v for v, count in value_counts.items() if count == 2][0]
                    return "Full House", f"Three {three_kind}'s and a pair of {pair}'s"
                    
                if is_flush:
                    return "Flush", "Five cards of the same suit"
                    
                if is_straight:
                    return "Straight", "Five consecutive cards"
                    
                if counts == [3, 1, 1]:
                    three_kind = [v for v, count in value_counts.items() if count == 3][0]
                    return "Three of a Kind", f"Three {three_kind}'s"
                    
                if counts == [2, 2, 1]:
                    pairs = [v for v, count in value_counts.items() if count == 2]
                    return "Two Pair", f"Pair of {pairs[0]}'s and pair of {pairs[1]}'s"
                    
                if counts == [2, 1, 1, 1]:
                    pair = [v for v, count in value_counts.items() if count == 2][0]
                    return "One Pair", f"Pair of {pair}'s"
                    
                # High card
                high_card = card_values[numerical_values.index(max(numerical_values))]
                return "High Card", f"{high_card} high"
                
            async def on_timeout(self):
                try:
                    await inter.edit_original_message(
                        content=f"🃏 **Five Card Draw Poker** 🃏\nBet: {format_coins(amount)}\n\n"
                        f"Game timed out. You lost {format_coins(amount)}.",
                        view=None
                    )
                except:
                    pass
        
        # Start game
        view = PokerView(self, deck, hand)
        await inter.edit_original_message(view=view)
        
    # --- High Stakes Gambling Commands ---
    @commands.slash_command(name="gamble_hs")
    async def gamble_hs_group(self, inter: disnake.ApplicationCommandInteraction):
        """High stakes gambling games (min bet: 1000)"""
        pass
        
    @gamble_hs_group.sub_command(name="slots", description="High stakes slots (min bet: 1000)")
    async def hs_slots(self, inter: disnake.ApplicationCommandInteraction, 
                       amount: int = commands.Param(ge=HIGH_STAKES_MIN_BET)):
        # Re-use the slots command with high stakes
        await self.slots(inter, amount)
        
    @gamble_hs_group.sub_command(name="dice", description="High stakes dice game (min bet: 1000)")
    async def hs_dice(self, inter: disnake.ApplicationCommandInteraction,
                      guess: int = commands.Param(ge=1, le=6), 
                      amount: int = commands.Param(ge=HIGH_STAKES_MIN_BET)):
        # Re-use the dice command with high stakes
        await self.dice(inter, guess, amount)
        
    @gamble_hs_group.sub_command(name="redblack", description="High stakes red/black (min bet: 1000)")
    async def hs_redblack(self, inter: disnake.ApplicationCommandInteraction,
                          choice: str = commands.Param(choices=["red", "black"]),
                          amount: int = commands.Param(ge=HIGH_STAKES_MIN_BET)):
        # Re-use the redblack command with high stakes
        await self.redblack(inter, choice, amount)
        
    async def announce_big_win(self, user, amount, game_type):
        """Announce a big win in the announcement channel"""
        try:
            channel = self.bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
            if channel:
                await channel.send(f"💰 **BIG WIN!** 💰\n{user.mention} just won {format_coins(amount)} coins from {game_type}!")
        except Exception as e:
            logger.error(f"Failed to announce big win: {e}")
            
class LotteryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="lottery")
    async def lottery_group(self, inter: disnake.ApplicationCommandInteraction):
        """Lottery commands"""
        pass
        
    @lottery_group.sub_command(name="buy", description="Buy lottery tickets")
    async def lottery_buy(self, inter: disnake.ApplicationCommandInteraction, tickets: int = commands.Param(ge=1, default=1)):
        user_id = inter.author.id
        ud = get_user_data(user_id)
        
        total_cost = tickets * LOTTERY_TICKET_PRICE
        
        if ud["balance"] < total_cost:
            await inter.response.send_message(f"Not enough coins. You need {format_coins(total_cost)} but have {format_coins(ud['balance'])}.", ephemeral=True)
            return
            
        # Purchase tickets
        ud["balance"] -= total_cost
        
        # Add tickets to the lottery
        for _ in range(tickets):
            bot_data.setdefault("lottery_tickets", []).append(user_id)
            
        # Add to the pot
        bot_data["lottery_pot"] = bot_data.get("lottery_pot", 0.0) + total_cost
        
        # Add to community goal progress
        bot_data["community_goals_progress"]["lottery_donations"] = bot_data["community_goals_progress"].get("lottery_donations", 0) + total_cost
        
        # Save data
        save_bot_data()
        
        await inter.response.send_message(
            f"🎟️ {inter.author.mention} purchased {tickets} lottery ticket{'s' if tickets > 1 else ''}!\n"
            f"Total pot is now {format_coins(bot_data['lottery_pot'])}!"
        )
        
    @lottery_group.sub_command(name="info", description="Get information about the current lottery")
    async def lottery_info(self, inter: disnake.ApplicationCommandInteraction):
        pot = bot_data.get("lottery_pot", 0.0)
        tickets = bot_data.get("lottery_tickets", [])
        ticket_count = len(tickets)
        
        # Calculate time until next drawing
        next_draw = self.bot.lottery_drawing.next_iteration
        time_until = "Unknown"
        if next_draw:
            now = datetime.datetime.now(timezone.utc)
            delta = next_draw - now
            hours, remainder = divmod(delta.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_until = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            
        embed = disnake.Embed(
            title="🎟️ Lottery Information",
            description=f"Current pot: {format_coins(pot)} coins\n"
                       f"Tickets sold: {ticket_count}\n"
                       f"Ticket price: {LOTTERY_TICKET_PRICE} coins\n"
                       f"Next drawing in: {time_until}\n"
                       f"Odds of winning: 1/{ticket_count if ticket_count > 0 else '∞'}",
            color=disnake.Color.gold()
        )
        
        await inter.response.send_message(embed=embed)
        
class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="shop", description="Browse the server shop")
    async def shop(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        
        # Get active shop items
        active_items = []
        now = datetime.datetime.now(timezone.utc)
        
        for item_id, item in shop_items.items():
            # Skip expired items
            if item.get("expires_at"):
                try:
                    expires_at = datetime.datetime.fromisoformat(item["expires_at"].replace('Z', '+00:00'))
                    if expires_at <= now:
                        continue
                except (ValueError, TypeError):
                    pass
                    
            active_items.append(item)
            
        if not active_items:
            await inter.edit_original_message(content="The shop is currently empty. Check back later!")
            return
            
        # Sort items by ID
        active_items.sort(key=lambda x: x.get("id", ""))
        
        # Create embed
        embed = disnake.Embed(
            title="🛒 Server Shop",
            description="Click on an item to purchase or gift it.",
            color=disnake.Color.green()
        )
        
        # Check if shop is open
        shop_open = is_shop_open()
        if not shop_open:
            embed.description += f"\n\n⚠️ **The shop is currently CLOSED**\nHours: {SHOP_OPEN_TIME.strftime('%H:%M')} - {SHOP_CLOSE_TIME.strftime('%H:%M')} {SHOP_TIMEZONE_STR}"
            
        # Add items to embed
        for i, item in enumerate(active_items, 1):
            item_name = item.get("name", "Unknown Item")
            
            # Handle price display based on credit_cost and usd_price
            credit_cost = item.get("credit_cost")
            usd_price = item.get("usd_price")
            
            price_display = ""
            
            # USD-only logic
            if credit_cost in (0, "0", "N/A"):
                if isinstance(usd_price, str):
                    price_display = f"USD: {usd_price}"
                elif isinstance(usd_price, (int, float)):
                    price_display = f"USD: ${usd_price:.2f}"
                else:
                    price_display = "Price: Contact shopkeeper"
            # Credit cost with optional USD price
            elif isinstance(credit_cost, (int, float)) and credit_cost > 0:
                price_display = f"{format_coins(credit_cost)} coins"
                if usd_price:
                    if isinstance(usd_price, str):
                        price_display += f" / USD: {usd_price}"
                    elif isinstance(usd_price, (int, float)):
                        price_display += f" / USD: ${usd_price:.2f}"
            # Fallback
            else:
                price_display = "Price: Contact shopkeeper"
                
            # Add expiration if applicable
            if item.get("expires_at"):
                try:
                    expires_at = datetime.datetime.fromisoformat(item["expires_at"].replace('Z', '+00:00'))
                    delta = expires_at - now
                    days, remainder = divmod(delta.total_seconds(), 86400)
                    hours, remainder = divmod(remainder, 3600)
                    minutes, _ = divmod(remainder, 60)
                    
                    expires_in = ""
                    if days > 0:
                        expires_in += f"{int(days)}d "
                    if hours > 0:
                        expires_in += f"{int(hours)}h "
                    if minutes > 0:
                        expires_in += f"{int(minutes)}m"
                        
                    price_display += f"\nExpires in: {expires_in}"
                except (ValueError, TypeError):
                    pass
                    
            embed.add_field(
                name=f"{i}. {item_name}",
                value=price_display,
                inline=True
            )
            
        # Footer with timezone info
        embed.set_footer(text=f"Shop timezone: {SHOP_TIMEZONE_STR}")
        
        # Create view with buttons for each item
        view = DynamicShopView(active_items, shop_open)
        
        await inter.edit_original_message(embed=embed, view=view)
        
class DynamicShopView(disnake.ui.View):
    def __init__(self, items, shop_open):
        super().__init__(timeout=300)  # 5 minute timeout
        self.items = items
        self.shop_open = shop_open
        
        # Add numbered buttons for each item
        for i, item in enumerate(items, 1):
            button = disnake.ui.Button(
                style=disnake.ButtonStyle.primary,
                label=str(i),
                custom_id=f"shop_item_{item.get('id')}",
                disabled=not shop_open
            )
            button.callback = self.item_callback
            self.add_item(button)
            
    async def item_callback(self, inter: disnake.MessageInteraction):
        # Extract item_id from custom_id
        item_id = inter.component.custom_id.replace("shop_item_", "")
        
        # Find the item
        selected_item = None
        for item in self.items:
            if item.get("id") == item_id:
                selected_item = item
                break
                
        if not selected_item:
            await inter.response.send_message("This item is no longer available.", ephemeral=True)
            return
            
        # Show confirmation view
        confirm_view = GiftConfirmationView(selected_item)
        await inter.response.send_message(
            f"You selected: **{selected_item.get('name')}**\nWould you like to buy this for yourself or gift it to someone?",
            view=confirm_view,
            ephemeral=True
        )
        
class GiftConfirmationView(disnake.ui.View):
    def __init__(self, item):
        super().__init__(timeout=120)  # 2 minute timeout
        self.item = item
        
    @disnake.ui.button(label="Buy for Myself", style=disnake.ButtonStyle.primary)
    async def buy_self(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Show payment method view
        payment_view = PaymentMethodView(self.item, None)  # None = self purchase
        await inter.response.edit_message(
            content=f"How would you like to pay for **{self.item.get('name')}**?",
            view=payment_view
        )
        
    @disnake.ui.button(label="Gift to Someone", style=disnake.ButtonStyle.secondary)
    async def gift_other(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Show modal to enter recipient
        modal = GiftRecipientModal(self.item)
        await inter.response.send_modal(modal)
        
class GiftRecipientModal(disnake.ui.Modal):
    def __init__(self, item):
        self.item = item
        components = [
            disnake.ui.TextInput(
                label="Recipient User ID or Mention",
                placeholder="Enter user ID or mention (e.g., @user or 123456789012345678)",
                custom_id="recipient",
                style=disnake.TextInputStyle.short,
                required=True
            )
        ]
        super().__init__(title="Select Gift Recipient", components=components)
        
    async def callback(self, inter: disnake.ModalInteraction):
        recipient_input = inter.text_values["recipient"].strip()
        
        # Try to extract user ID from mention format
        if recipient_input.startswith("<@") and recipient_input.endswith(">"):
            recipient_input = recipient_input[2:-1]
            if recipient_input.startswith("!"):  # Legacy mention format
                recipient_input = recipient_input[1:]
                
        # Try to convert to integer
        try:
            recipient_id = int(recipient_input)
            # Try to fetch the user
            try:
                recipient = await inter.bot.get_or_fetch_user(recipient_id)
                
                if not recipient:
                    await inter.response.send_message("I couldn't find that user. Please check the ID and try again.", ephemeral=True)
                    return
                    
                if recipient.bot:
                    await inter.response.send_message("You can't gift items to bots.", ephemeral=True)
                    return
                    
                # Show payment method view
                payment_view = PaymentMethodView(self.item, recipient)
                await inter.response.send_message(
                    content=f"How would you like to pay for **{self.item.get('name')}** for {recipient.mention}?",
                    view=payment_view,
                    ephemeral=True
                )
            except Exception as e:
                await inter.response.send_message(f"Error finding user: {e}", ephemeral=True)
        except ValueError:
            await inter.response.send_message("Invalid user ID format. Please use a numeric ID or proper mention.", ephemeral=True)
            
class PaymentMethodView(disnake.ui.View):
    def __init__(self, item, gift_recipient):
        super().__init__(timeout=120)  # 2 minute timeout
        self.item = item
        self.gift_recipient = gift_recipient
        
        # Check if item has valid credit cost
        credit_cost = item.get("credit_cost")
        has_valid_credit_cost = isinstance(credit_cost, (int, float)) and credit_cost > 0
        
        # Check if item has valid USD price
        usd_price = item.get("usd_price")
        has_valid_usd_price = usd_price is not None
        
        # Add/Configure buttons based on available payment methods
        credits_button = disnake.ui.Button(
            label="Pay with Credits",
            style=disnake.ButtonStyle.success,
            disabled=not has_valid_credit_cost
        )
        credits_button.callback = self.pay_credits_callback
        self.add_item(credits_button)
        
        usd_button = disnake.ui.Button(
            label="Pay with USD/Other",
            style=disnake.ButtonStyle.primary,
            disabled=not has_valid_usd_price
        )
        usd_button.callback = self.pay_usd_callback
        self.add_item(usd_button)
        
    async def pay_credits_callback(self, inter: disnake.MessageInteraction):
        buyer = inter.author
        recipient = self.gift_recipient or buyer
        
        # Handle global boost item specially
        if self.item.get("id") == GLOBAL_BOOST_ITEM_ID:
            if self.gift_recipient:
                await inter.response.send_message(
                    "Global coin boosts cannot be gifted. They benefit everyone on the server.",
                    ephemeral=True
                )
                return
                
            await self.process_global_boost(inter)
            return
            
        # Get credit cost
        credit_cost = self.item.get("credit_cost")
        if not isinstance(credit_cost, (int, float)) or credit_cost <= 0:
            await inter.response.send_message("This item cannot be purchased with credits.", ephemeral=True)
            return
            
        # Check buyer's balance
        buyer_data = get_user_data(buyer.id)
        if buyer_data["balance"] < credit_cost:
            await inter.response.send_message(
                f"You don't have enough coins. This costs {format_coins(credit_cost)} but you have {format_coins(buyer_data['balance'])}.",
                ephemeral=True
            )
            return
            
        # Deduct coins from buyer
        buyer_data["balance"] -= credit_cost
        save_user_data()
        
        # Notify shopkeepers
        purchase_info = {
            "item_name": self.item.get("name", "Unknown Item"),
            "buyer": buyer,
            "recipient": recipient,
            "price": f"{format_coins(credit_cost)} coins",
            "payment_method": "Credits"
        }
        await self.notify_shopkeepers(inter.bot, purchase_info)
        
        # Confirmation message
        if recipient.id == buyer.id:
            await inter.response.send_message(
                f"✅ {buyer.mention} purchased **{self.item.get('name')}** for {format_coins(credit_cost)} coins!",
                ephemeral=False  # Public confirmation
            )
        else:
            # Send public confirmation
            await inter.response.send_message(
                f"✅ {buyer.mention} gifted **{self.item.get('name')}** to {recipient.mention} for {format_coins(credit_cost)} coins!",
                ephemeral=False
            )
            
            # Send DM to recipient
            try:
                recipient_dm = await recipient.create_dm()
                await recipient_dm.send(f"🎁 {buyer.display_name} has gifted you **{self.item.get('name')}**!")
            except:
                pass  # Silently fail if DM can't be sent
    
    async def process_global_boost(self, inter: disnake.MessageInteraction):
        """Special handling for the global coin boost item"""
        credit_cost = self.item.get("credit_cost", GLOBAL_BOOST_ITEM_COST)
        
        # Check buyer's balance
        buyer_data = get_user_data(inter.author.id)
        if buyer_data["balance"] < credit_cost:
            await inter.response.send_message(
                f"You don't have enough coins. This costs {format_coins(credit_cost)} but you have {format_coins(buyer_data['balance'])}.",
                ephemeral=True
            )
            return
            
        # Deduct coins from buyer
        buyer_data["balance"] -= credit_cost
        save_user_data()
        
        # Handle the boost
        now = datetime.datetime.now(timezone.utc)
        boost_duration = timedelta(hours=GLOBAL_BOOST_DURATION_HOURS)
        
        if bot_data.get("global_coin_boost_active", False):
            # Extend existing boost
            current_end = bot_data.get("global_coin_boost_ends_at")
            if isinstance(current_end, str):
                try:
                    current_end = datetime.datetime.fromisoformat(current_end.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    current_end = now
            
            if not current_end or current_end < now:
                # Boost expired, set new end time
                new_end_time = now + boost_duration
            else:
                # Extend existing boost
                new_end_time = current_end + boost_duration
                
            bot_data["global_coin_boost_ends_at"] = new_end_time
            
            # Calculate total remaining time
            remaining = new_end_time - now
            hours, remainder = divmod(remaining.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            time_str = f"{int(hours)}h {int(minutes)}m"
            
            boost_message = f"🚀 {inter.author.mention} extended the global {GLOBAL_BOOST_MULTIPLIER}x coin boost!\nBoost will now last for {time_str}!"
        else:
            # Activate new boost
            bot_data["global_coin_boost_active"] = True
            bot_data["global_coin_boost_ends_at"] = now + boost_duration
            
            boost_message = f"🚀 {inter.author.mention} activated a global {GLOBAL_BOOST_MULTIPLIER}x coin boost for {GLOBAL_BOOST_DURATION_HOURS} hours!"
            
        save_bot_data()
        
        # Send confirmation
        await inter.response.send_message(boost_message, ephemeral=False)
        
        # Also announce in announcement channel
        try:
            announce_channel = inter.bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
            if announce_channel and announce_channel.id != inter.channel.id:
                await announce_channel.send(boost_message)
        except Exception as e:
            logger.error(f"Failed to announce boost in announcement channel: {e}")
            
    async def pay_usd_callback(self, inter: disnake.MessageInteraction):
        buyer = inter.author
        recipient = self.gift_recipient or buyer
        
        usd_price = self.item.get("usd_price")
        price_display = f"${usd_price:.2f}" if isinstance(usd_price, (int, float)) else str(usd_price)
        
        # Notify shopkeepers
        purchase_info = {
            "item_name": self.item.get("name", "Unknown Item"),
            "buyer": buyer,
            "recipient": recipient,
            "price": price_display,
            "payment_method": "USD/Other"
        }
        await self.notify_shopkeepers(inter.bot, purchase_info)
        
        # Send confirmation based on price type
        if isinstance(usd_price, (int, float)):
            await inter.response.send_message(
                f"💵 {buyer.mention} selected **{self.item.get('name')}** for ${usd_price:.2f} USD.\n"
                f"A shopkeeper will contact you to arrange payment.",
                ephemeral=False  # Public message
            )
        else:
            await inter.response.send_message(
                f"💵 {buyer.mention} selected **{self.item.get('name')}** with price: {usd_price}.\n"
                f"A shopkeeper will contact you to arrange payment.",
                ephemeral=False  # Public message
            )
            
    async def notify_shopkeepers(self, bot, purchase_info):
        """Notify all users with the shopkeeper role about a purchase"""
        try:
            # Get the first guild (assuming single-server bot)
            guild = None
            for g in bot.guilds:
                guild = g
                break
                
            if not guild:
                logger.error("Cannot notify shopkeepers: No guild found")
                return
                
            # Get shopkeeper role
            shopkeeper_role = guild.get_role(SHOPKEEPER_ROLE_ID)
            if not shopkeeper_role:
                logger.error(f"Cannot notify shopkeepers: Role {SHOPKEEPER_ROLE_ID} not found")
                return
                
            # Create embed
            embed = disnake.Embed(
                title="New Purchase Alert",
                description=f"Someone has made a purchase in the shop!",
                color=disnake.Color.green(),
                timestamp=datetime.datetime.now(timezone.utc)
            )
            
            embed.add_field(name="Item", value=purchase_info["item_name"], inline=False)
            embed.add_field(name="Buyer", value=f"{purchase_info['buyer'].mention} ({purchase_info['buyer'].name}#{purchase_info['buyer'].discriminator})", inline=True)
            
            if purchase_info["recipient"].id != purchase_info["buyer"].id:
                embed.add_field(name="Recipient", value=f"{purchase_info['recipient'].mention} ({purchase_info['recipient'].name}#{purchase_info['recipient'].discriminator})", inline=True)
                
            embed.add_field(name="Price", value=purchase_info["price"], inline=True)
            embed.add_field(name="Payment Method", value=purchase_info["payment_method"], inline=True)
            
            # Notify each shopkeeper
            notified = 0
            for member in shopkeeper_role.members:
                try:
                    dm_channel = await member.create_dm()
                    await dm_channel.send(embed=embed)
                    notified += 1
                except Exception as e:
                    logger.error(f"Failed to notify shopkeeper {member.id}: {e}")
                    
            logger.info(f"Notified {notified} shopkeepers about purchase of {purchase_info['item_name']}")
            
        except Exception as e:
            logger.error(f"Error notifying shopkeepers: {e}")
            
class ShopAdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def cog_check(self, inter):
        # Only allow server owner or admin channel
        return inter.channel.id == ADMIN_CHANNEL_ID or (inter.guild and inter.author.id == inter.guild.owner_id)
        
    @commands.slash_command(name="shopadmin")
    async def shopadmin_group(self, inter: disnake.ApplicationCommandInteraction):
        """Shop administration commands"""
        pass
        
    @shopadmin_group.sub_command(name="list", description="List all shop items")
    async def list_items(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        
        if not shop_items:
            await inter.edit_original_message(content="The shop is empty.")
            return
            
        # Create embed
        embed = disnake.Embed(
            title="🛒 Shop Items",
            description=f"Total items: {len(shop_items)}",
            color=disnake.Color.blue()
        )
        
        for item_id, item in shop_items.items():
            # Format prices
            credit_cost = item.get("credit_cost")
            usd_price = item.get("usd_price")
            
            price_str = []
            if isinstance(credit_cost, (int, float)) and credit_cost > 0:
                price_str.append(f"{format_coins(credit_cost)} coins")
            elif credit_cost in ("0", "N/A"):
                price_str.append("Credits: N/A")
            
            if usd_price is not None:
                if isinstance(usd_price, (int, float)):
                    price_str.append(f"${usd_price:.2f} USD")
                else:
                    price_str.append(f"USD: {usd_price}")
                    
            # Format expiry
            expiry = "No expiration"
            if item.get("expires_at"):
                try:
                    expires_at = datetime.datetime.fromisoformat(item["expires_at"].replace('Z', '+00:00'))
                    expiry = expires_at.strftime("%Y-%m-%d %H:%M UTC")
                except (ValueError, TypeError):
                    expiry = "Invalid expiry"
                    
            embed.add_field(
                name=f"{item.get('name')} (ID: {item_id})",
                value=f"Price: {' / '.join(price_str)}\nExpires: {expiry}",
                inline=False
            )
            
        await inter.edit_original_message(embed=embed)
        
    @shopadmin_group.sub_command(name="remove", description="Remove an item from the shop")
    async def remove_item(self, inter: disnake.ApplicationCommandInteraction, item_id: str):
        if item_id not in shop_items:
            await inter.response.send_message(f"Item with ID {item_id} not found.", ephemeral=True)
            return
            
        item_name = shop_items[item_id].get("name", "Unknown Item")
        del shop_items[item_id]
        save_shop_items()
        
        await inter.response.send_message(f"Removed item: {item_name} (ID: {item_id})", ephemeral=True)
        
    @shopadmin_group.sub_command(name="add", description="Add a new item to the shop")
    async def add_item(self, inter: disnake.ApplicationCommandInteraction):
        # Show modal to enter item details
        modal = ShopItemAddModal()
        await inter.response.send_modal(modal)
        
class ShopItemAddModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Item Name",
                placeholder="Enter the item name",
                custom_id="item_name",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100
            ),
            disnake.ui.TextInput(
                label="Credit Cost (or '0'/'N/A' for USD-only)",
                placeholder="Enter cost in credits (numbers only, or '0'/'N/A')",
                custom_id="credit_cost",
                style=disnake.TextInputStyle.short,
                required=False
            ),
            disnake.ui.TextInput(
                label="USD Price (optional, can be text)",
                placeholder="Enter USD price (e.g., 5.99 or 'Negotiable')",
                custom_id="usd_price",
                style=disnake.TextInputStyle.short,
                required=False
            ),
            disnake.ui.TextInput(
                label="Duration in Hours (0 for no expiry)",
                placeholder="How long before this item expires (number of hours)",
                custom_id="duration",
                style=disnake.TextInputStyle.short,
                value="0",
                required=True
            ),
            disnake.ui.TextInput(
                label="Custom Item ID (optional)",
                placeholder="Enter custom ID or leave blank for auto-generated",
                custom_id="custom_id",
                style=disnake.TextInputStyle.short,
                required=False
            )
        ]
        super().__init__(title="Add Shop Item", components=components)
        
    async def callback(self, inter: disnake.ModalInteraction):
        # Extract values
        name = inter.text_values["item_name"].strip()
        credit_cost_input = inter.text_values["credit_cost"].strip()
        usd_price_input = inter.text_values["usd_price"].strip()
        duration_input = inter.text_values["duration"].strip()
        custom_id = inter.text_values["custom_id"].strip()
        
        # Validate credit cost
        credit_cost = None
        if credit_cost_input.lower() in ("", "0", "n/a"):
            credit_cost = "N/A" if credit_cost_input.lower() == "n/a" else 0
        else:
            try:
                credit_cost = float(credit_cost_input)
                if credit_cost <= 0:
                    await inter.response.send_message("Credit cost must be positive or explicitly '0'/'N/A'.", ephemeral=True)
                    return
            except ValueError:
                await inter.response.send_message("Invalid credit cost format. Use a number, '0', or 'N/A'.", ephemeral=True)
                return
                
        # Process USD price
        usd_price = None
        if usd_price_input:
            try:
                usd_price = float(usd_price_input)
            except ValueError:
                # It's a text price like "Negotiable"
                usd_price = usd_price_input
                
        # Ensure at least one valid price is provided
        if (credit_cost in (0, "0", "N/A") or credit_cost is None) and not usd_price:
            await inter.response.send_message("You must provide either a valid credit cost or USD price.", ephemeral=True)
            return
            
        # Validate duration
        try:
            duration = int(duration_input)
            if duration < 0:
                await inter.response.send_message("Duration cannot be negative.", ephemeral=True)
                return
        except ValueError:
            await inter.response.send_message("Invalid duration format. Use a whole number.", ephemeral=True)
            return
            
        # Generate item ID if not provided
        item_id = custom_id if custom_id else str(uuid.uuid4())[:8].upper()
        
        # Check for ID collision
        if item_id in shop_items:
            await inter.response.send_message(f"An item with ID {item_id} already exists. Use a different custom ID or leave it blank.", ephemeral=True)
            return
            
        # Calculate expiry time
        expires_at = None
        if duration > 0:
            expires_at = (datetime.datetime.now(timezone.utc) + timedelta(hours=duration)).isoformat()
            
        # Create item
        new_item = {
            "id": item_id,
            "name": name,
            "credit_cost": credit_cost,
            "usd_price": usd_price,
            "expires_at": expires_at,
            "added_by": inter.author.id,
            "added_at": datetime.datetime.now(timezone.utc).isoformat()
        }
        
        # Add to shop
        shop_items[item_id] = new_item
        save_shop_items()
        
        # Format response
        credit_cost_display = f"{format_coins(credit_cost)} coins" if isinstance(credit_cost, (int, float)) and credit_cost > 0 else "N/A"
        usd_price_display = f"${usd_price:.2f}" if isinstance(usd_price, (int, float)) else (usd_price if usd_price else "N/A")
        
        await inter.response.send_message(
            f"✅ Added item: **{name}** (ID: {item_id})\n"
            f"Credit Cost: {credit_cost_display}\n"
            f"USD Price: {usd_price_display}\n"
            f"Expires: {'Never' if not expires_at else f'In {duration} hours'}",
            ephemeral=True
        )
        
class AdminCoinsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def cog_check(self, inter):
        # Only allow server owner or admin channel
        return inter.channel.id == ADMIN_CHANNEL_ID or (inter.guild and inter.author.id == inter.guild.owner_id)
        
    @commands.slash_command(name="admincoins")
    async def admincoins_group(self, inter: disnake.ApplicationCommandInteraction):
        """Admin economy commands"""
        pass
        
    @admincoins_group.sub_command(name="give", description="Give coins to a user")
    async def give_coins(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User, amount: int):
        if amount <= 0:
            await inter.response.send_message("Amount must be positive.", ephemeral=True)
            return
            
        ud = get_user_data(user.id)
        ud["balance"] += amount
        save_user_data()
        
        await inter.response.send_message(f"Gave {format_coins(amount)} coins to {user.mention}. New balance: {format_coins(ud['balance'])}.", ephemeral=True)
        
    @admincoins_group.sub_command(name="take", description="Take coins from a user")
    async def take_coins(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User, amount: int):
        if amount <= 0:
            await inter.response.send_message("Amount must be positive.", ephemeral=True)
            return
            
        ud = get_user_data(user.id)
        ud["balance"] = max(0, ud["balance"] - amount)
        save_user_data()
        
        await inter.response.send_message(f"Took {format_coins(amount)} coins from {user.mention}. New balance: {format_coins(ud['balance'])}.", ephemeral=True)
        
    @admincoins_group.sub_command(name="set", description="Set a user's coins to a specific amount")
    async def set_coins(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User, amount: int):
        if amount < 0:
            await inter.response.send_message("Amount cannot be negative.", ephemeral=True)
            return
            
        ud = get_user_data(user.id)
        ud["balance"] = amount
        save_user_data()
        
        await inter.response.send_message(f"Set {user.mention}'s balance to {format_coins(amount)}.", ephemeral=True)
        
    @admincoins_group.sub_command(name="setjackpot", description="Set the slot jackpot pool amount")
    async def set_jackpot(self, inter: disnake.ApplicationCommandInteraction, amount: float):
        if amount < 0:
            await inter.response.send_message("Amount cannot be negative.", ephemeral=True)
            return
            
        bot_data["slot_jackpot_pool"] = amount
        save_bot_data()
        
        await inter.response.send_message(f"Set slot jackpot pool to {format_coins(amount)}.", ephemeral=True)
        
    @admincoins_group.sub_command(name="setjackpotcontribution", description="Set the jackpot contribution percentage")
    async def set_jackpot_contribution(self, inter: disnake.ApplicationCommandInteraction, percentage: float = commands.Param(ge=0, le=100)):
        rate = percentage / 100.0
        bot_data["slot_jackpot_contribution"] = rate
        save_bot_data()
        
        await inter.response.send_message(f"Set jackpot contribution rate to {percentage}%.", ephemeral=True)
        
    @admincoins_group.sub_command(name="setjackpotchance", description="Set the jackpot override chance percentage")
    async def set_jackpot_chance(self, inter: disnake.ApplicationCommandInteraction, percentage: float = commands.Param(ge=0, le=100)):
        rate = percentage / 100.0
        bot_data["slot_jackpot_override_chance"] = rate
        save_bot_data()
        
        await inter.response.send_message(f"Set jackpot override chance to {percentage}%.", ephemeral=True)
        
class RolePerksButtonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="supporter")
    async def supporter_commands(self, inter: disnake.ApplicationCommandInteraction):
        """Supporter perks commands"""
        pass
        
    @supporter_commands.sub_command(name="nickname", description="Set your display name (supporter only)")
    async def set_nickname(self, inter: disnake.ApplicationCommandInteraction, new_nickname: str = None):
        # Check if user has the Supporter role
        if not is_supporter(inter.author):
            await inter.response.send_message("This command is only available to Supporters.", ephemeral=True)
            return
            
        # Check if nickname is provided
        if new_nickname:
            try:
                await inter.author.edit(nick=new_nickname)
                await inter.response.send_message(f"Your nickname has been set to: {new_nickname}", ephemeral=True)
            except Exception as e:
                await inter.response.send_message(f"Error setting nickname: {e}", ephemeral=True)
        else:
            # If no nickname provided, reset to default
            try:
                await inter.author.edit(nick=None)
                await inter.response.send_message("Your nickname has been reset to your username.", ephemeral=True)
            except Exception as e:
                await inter.response.send_message(f"Error resetting nickname: {e}", ephemeral=True)
                
    @commands.slash_command(name="vip")
    async def vip_commands(self, inter: disnake.ApplicationCommandInteraction):
        """VIP perks commands"""
        pass
        
    @vip_commands.sub_command(name="embed", description="Send a fancy embed message (VIP only)")
    async def send_embed(self, inter: disnake.ApplicationCommandInteraction, message: str):
        # Check if user has the VIP role
        if not is_vip(inter.author):
            await inter.response.send_message("This command is only available to VIPs.", ephemeral=True)
            return
            
        # Create and send embed
        embed = disnake.Embed(
            description=message,
            color=disnake.Color.gold()
        )
        embed.set_author(name=inter.author.display_name, icon_url=inter.author.display_avatar.url)
        
        await inter.response.send_message(embed=embed)
        
    async def cog_command_error(self, inter, error):
        if isinstance(error, commands.CheckFailure):
            await inter.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
        else:
            await inter.response.send_message(
                f"An error occurred: {error}",
                ephemeral=True
            )
            logger.error(f"Command error in RolePerksButtonCog: {error}")
            
class VoiceChannelRentalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="rentvc", description="Rent a private voice channel")
    async def rentvc(self, inter: disnake.ApplicationCommandInteraction, 
                    duration_hours: int = commands.Param(ge=1, le=24),
                    user_limit: int = commands.Param(ge=0, le=99),
                    channel_name: str = None,
                    allowed_users_str: str = None):
        """Rent a private voice channel
        
        Parameters
        ----------
        duration_hours: How many hours to rent the channel for (1-24)
        user_limit: Maximum number of users (0 for unlimited)
        channel_name: Optional custom name for the channel
        allowed_users_str: Optional space-separated list of user IDs to allow
        """
        # Calculate cost
        total_cost = VC_RENT_COST_PER_HOUR * duration_hours
        
        # Check user balance
        user_id = inter.author.id
        ud = get_user_data(user_id)
        
        if ud["balance"] < total_cost:
            await inter.response.send_message(
                f"You don't have enough coins to rent a voice channel for {duration_hours} hours.\n"
                f"Cost: {format_coins(total_cost)} coins\n"
                f"Your balance: {format_coins(ud['balance'])} coins",
                ephemeral=True
            )
            return
            
        # Deduct coins
        ud["balance"] -= total_cost
        save_user_data()
        
        # Process allowed users
        allowed_users = []
        if allowed_users_str:
            user_ids = allowed_users_str.split()
            for uid in user_ids:
                # Clean up mentions if they exist
                uid = uid.strip()
                if uid.startswith("<@") and uid.endswith(">"):
                    uid = uid[2:-1]
                    if uid.startswith("!"):
                        uid = uid[1:]
                
                try:
                    allowed_users.append(int(uid))
                except ValueError:
                    pass  # Skip invalid IDs
        
        # Create voice channel
        await inter.response.defer(ephemeral=True)
        
        try:
            # Determine channel name
            vc_name = channel_name if channel_name else f"{inter.author.display_name}'s VC"
            
            # Determine category
            category = None
            if VC_RENT_CATEGORY_ID:
                category = inter.guild.get_channel(VC_RENT_CATEGORY_ID)
            
            # Create overwrites
            overwrites = {
                inter.guild.default_role: disnake.PermissionOverwrite(connect=False, view_channel=False),
                inter.guild.me: disnake.PermissionOverwrite(connect=True, view_channel=True, manage_channels=True),
                inter.author: disnake.PermissionOverwrite(connect=True, view_channel=True, speak=True, stream=True)
            }
            
            # Add permissions for allowed users
            for uid in allowed_users:
                try:
                    user = await inter.bot.get_or_fetch_user(uid)
                    member = inter.guild.get_member(uid)
                    if member:
                        overwrites[member] = disnake.PermissionOverwrite(connect=True, view_channel=True, speak=True, stream=True)
                except:
                    pass  # Skip if user can't be found
            
            # Create the channel
            vc = await inter.guild.create_voice_channel(
                name=vc_name,
                category=category,
                user_limit=user_limit if user_limit > 0 else None,
                overwrites=overwrites
            )
            
            # Calculate expiry time
            expiry_time = datetime.datetime.now(timezone.utc) + timedelta(hours=duration_hours)
            
            # Store in bot_data
            bot_data.setdefault("rented_vcs", {})[str(vc.id)] = {
                "owner_id": inter.author.id,
                "expires_at": expiry_time
            }
            save_bot_data()
            
            # Send confirmation
            allowed_users_mentions = ""
            if allowed_users:
                mentions = []
                for uid in allowed_users:
                    user = await inter.bot.get_or_fetch_user(uid)
                    if user:
                        mentions.append(user.mention)
                if mentions:
                    allowed_users_mentions = "\nAllowed users: " + ", ".join(mentions)
            
            await inter.edit_original_message(
                content=f"✅ Voice channel created: {vc.mention}\n"
                f"Duration: {duration_hours} hour{'s' if duration_hours > 1 else ''}\n"
                f"Expires: <t:{int(expiry_time.timestamp())}:R>\n"
                f"Cost: {format_coins(total_cost)} coins"
                f"{allowed_users_mentions}"
            )
            
            logger.info(f"User {inter.author.id} created rented VC {vc.id} that expires at {expiry_time.isoformat()}")
            
        except Exception as e:
            # Refund if creation fails
            ud["balance"] += total_cost
            save_user_data()
            
            await inter.edit_original_message(
                content=f"❌ Failed to create voice channel: {e}\nYour coins have been refunded."
            )
            logger.error(f"Error creating rented VC for {inter.author.id}: {e}")
            
class GoalsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="goals", description="View community goals progress")
    async def goals(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        
        embed = disnake.Embed(
            title="🎯 Community Goals",
            description="Progress towards server-wide goals",
            color=disnake.Color.blue()
        )
        
        # Add fields for each goal
        for goal_id, goal_data in COMMUNITY_GOALS.items():
            current = bot_data["community_goals_progress"].get(goal_id, 0)
            target = goal_data["target"]
            reward = goal_data["reward"]
            
            # Calculate percentage
            percentage = min(100, int(current / target * 100)) if target > 0 else 0
            
            # Create progress bar
            progress_bar_length = 20
            filled_length = int(progress_bar_length * percentage / 100)
            progress_bar = "▓" * filled_length + "░" * (progress_bar_length - filled_length)
            
            embed.add_field(
                name=goal_id.replace("_", " ").title(),
                value=f"**Progress:** {current:,}/{target:,} ({percentage}%)\n"
                      f"**Reward:** {reward}\n"
                      f"**[{progress_bar}]**",
                inline=False
            )
            
        await inter.edit_original_message(embed=embed)
        
class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="help", description="Show available commands")
    async def help_command(self, inter: disnake.ApplicationCommandInteraction):
        user = inter.author
        is_admin = inter.channel.id == ADMIN_CHANNEL_ID or (inter.guild and user.id == inter.guild.owner_id) or (inter.guild and user.guild_permissions.administrator)
        
        # Create main embed
        embed = disnake.Embed(
            title="🤖 Bot Commands",
            description="Here are the commands you can use:",
            color=disnake.Color.blue()
        )
        
        # Economy commands
        economy_cmds = [
            "/balance - Check your coin balance",
            "/pay - Send coins to another user",
            "/daily - Claim your daily coins",
            "/leaderboard - See who has the most coins"
        ]
        embed.add_field(name="💰 Economy", value="\n".join(economy_cmds), inline=False)
        
        # Savings commands
        savings_cmds = [
            "/savings setpin - Set your savings account PIN",
            "/savings balance - Check your savings balance",
            "/savings deposit - Move coins to savings",
            "/savings withdraw - Move coins from savings"
        ]
        embed.add_field(name="🏦 Savings Account", value="\n".join(savings_cmds), inline=False)
        
        # Gambling commands
        gambling_cmds = [
            "/gamble slots - Bet on slot machine",
            "/gamble dice - Bet on dice roll",
            "/gamble redblack - Bet on red or black",
            "/gamble wheel - Spin the wheel"
        ]
        embed.add_field(name="🎲 Gambling", value="\n".join(gambling_cmds), inline=False)
        
        # High stakes gambling
        high_stakes_cmds = [
            f"/gamble_hs slots - High stakes slots (min {HIGH_STAKES_MIN_BET})",
            f"/gamble_hs dice - High stakes dice (min {HIGH_STAKES_MIN_BET})",
            f"/gamble_hs redblack - High stakes red/black (min {HIGH_STAKES_MIN_BET})"
        ]
        embed.add_field(name="💎 High Stakes Gambling", value="\n".join(high_stakes_cmds), inline=False)
        
        # Lottery commands
        lottery_cmds = [
            "/lottery buy - Buy lottery tickets",
            "/lottery info - See lottery pot details"
        ]
        embed.add_field(name="🎟️ Lottery", value="\n".join(lottery_cmds), inline=False)
        
        # Inventory commands
        inventory_cmds = [
            "/inventory view - View your inventory items",
            "/inventory use - Use an item from your inventory"
        ]
        embed.add_field(name="🎒 Inventory", value="\n".join(inventory_cmds), inline=False)
        
        # Minigame commands
        minigame_cmds = [
            "/minigame list - View available minigames",
            "/minigame play - Play a minigame"
        ]
        embed.add_field(name="🎮 Minigames", value="\n".join(minigame_cmds), inline=False)
        
        # Tournament commands
        tournament_cmds = [
            "/tournament list - View available tournaments",
            "/tournament join - Join a tournament"
        ]
        embed.add_field(name="🏆 Tournaments", value="\n".join(tournament_cmds), inline=False)
        
        # Shop and other features
        other_cmds = [
            "/shop - Browse available items",
            "/goals - View community goals progress",
            "/rentvc - Rent a private voice channel"
        ]
        embed.add_field(name="🛒 Shop & Features", value="\n".join(other_cmds), inline=False)
        
        # Role-specific commands
        if is_supporter(user):
            supporter_cmds = ["/supporter nickname - Change your display name"]
            embed.add_field(name="⭐ Supporter Commands", value="\n".join(supporter_cmds), inline=False)
            
        if is_vip(user):
            vip_cmds = ["/vip embed - Send a fancy message"]
            embed.add_field(name="💎 VIP Commands", value="\n".join(vip_cmds), inline=False)
            
        # Admin commands
        if is_admin:
            admin_cmds = [
                "/shopadmin list - List all shop items",
                "/shopadmin add - Add item to shop",
                "/shopadmin remove - Remove shop item",
                "/admincoins give - Give coins to user",
                "/admincoins take - Take coins from user", 
                "/admincoins set - Set user's balance",
                "/admincoins setjackpot - Set jackpot amount"
            ]
            embed.add_field(name="🔑 Admin Commands", value="\n".join(admin_cmds), inline=False)
            
        # Add footer about web interface
        embed.set_footer(text="Visit the web interface to manage tournaments, inventory, and more!")
        
        await inter.response.send_message(embed=embed, ephemeral=True)
        
# --- Event Handling ---
async def on_message(message):
    if message.author.bot:
        return
        
    # Add coins for each message
    coins_earned = 1
    
    # Check for global boost
    if bot_data.get("global_coin_boost_active", False):
        boost_end = bot_data.get("global_coin_boost_ends_at")
        now = datetime.datetime.now(timezone.utc)
        
        if boost_end:
            # Convert string to datetime if needed
            if isinstance(boost_end, str):
                try:
                    boost_end = datetime.datetime.fromisoformat(boost_end.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    boost_end = None
            
            # Apply boost if active
            if boost_end and now < boost_end:
                coins_earned *= GLOBAL_BOOST_MULTIPLIER
    
    # Add to user balance
    user_id = message.author.id
    ud = get_user_data(user_id)
    ud["balance"] += coins_earned
    
    # Update community goal for messages
    if "messages_sent" in bot_data["community_goals_progress"]:
        bot_data["community_goals_progress"]["messages_sent"] += 1
    
# --- Utility Functions ---
async def save_all_data():
    save_user_data()
    save_shop_items()
    save_bot_data()
    logger.info("Saved all data via autosave")

# --- Bot Initialization ---
def run_bot():
    intents = disnake.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True
    
    bot = EconomyBot(command_sync_flags=commands.CommandSyncFlags.default(), intents=intents)
    
    # Register event handlers
    bot.add_listener(on_message, 'on_message')
    
    # Load data
    load_user_data()
    load_shop_items()
    load_bot_data()
    
    # Add cogs
    bot.add_cog(BalanceCog(bot))
    bot.add_cog(SavingsCog(bot))
    bot.add_cog(GamblingCog(bot))
    bot.add_cog(LotteryCog(bot))
    bot.add_cog(ShopCog(bot))
    bot.add_cog(ShopAdminCog(bot))
    bot.add_cog(AdminCoinsCog(bot))
    bot.add_cog(RolePerksButtonCog(bot))
    bot.add_cog(VoiceChannelRentalCog(bot))
    bot.add_cog(GoalsCog(bot))
    bot.add_cog(HelpCog(bot))
    
    # Import and add new cogs
    try:
        from bot_cogs import InventoryCog, TournamentCog, MinigameCog
        bot.add_cog(InventoryCog(bot))
        bot.add_cog(TournamentCog(bot))
        bot.add_cog(MinigameCog(bot))
        logger.info("Successfully loaded inventory, tournament, and minigame cogs")
    except Exception as e:
        logger.error(f"Error loading new cogs: {e}")
    
    # Run the bot
    bot.run(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    run_bot()
