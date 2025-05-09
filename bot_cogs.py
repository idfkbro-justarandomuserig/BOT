import disnake
from disnake.ext import commands
import asyncio
import datetime
import random
import logging
import json
import os
from datetime import timezone, timedelta
import requests

# Import helpers
from bot_utils import InventorySystem, TournamentSystem, MinigameSystem

# Configure logging
logger = logging.getLogger("bot_cogs")

class InventoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="inventory", description="View and manage your inventory")
    async def inventory_group(self, inter: disnake.ApplicationCommandInteraction):
        """Inventory commands"""
        pass
    
    @inventory_group.sub_command(name="view", description="View your inventory")
    async def view_inventory(self, inter: disnake.ApplicationCommandInteraction):
        """View your inventory items"""
        user_id = str(inter.author.id)
        
        inventory = InventorySystem.get_user_inventory(user_id)
        
        embed = disnake.Embed(
            title="🎒 Your Inventory",
            description=f"You have {len(inventory['items'])}/{inventory['capacity']} items in your inventory.",
            color=disnake.Color.blue()
        )
        
        if not inventory['items']:
            embed.add_field(name="Empty Inventory", value="You don't have any items yet. Check the `/shop` command to buy items!", inline=False)
        else:
            # Group items by rarity for better display
            rarity_order = ["legendary", "epic", "rare", "uncommon", "common"]
            rarity_emojis = {
                "legendary": "🌟",
                "epic": "💫",
                "rare": "✨",
                "uncommon": "⭐",
                "common": "⚪"
            }
            
            for rarity in rarity_order:
                items_of_rarity = [item for item in inventory['items'] if item.get('rarity', 'common') == rarity]
                if items_of_rarity:
                    item_lines = []
                    for item in items_of_rarity:
                        item_line = f"{rarity_emojis.get(rarity, '⚪')} **{item.get('name', 'Unknown Item')}**"
                        if 'quantity' in item and item['quantity'] > 1:
                            item_line += f" (x{item['quantity']})"
                        if item.get('description'):
                            item_line += f"\n*{item.get('description')}*"
                        item_lines.append(item_line)
                    
                    embed.add_field(
                        name=f"{rarity.title()} Items",
                        value="\n\n".join(item_lines) if item_lines else "None",
                        inline=False
                    )
        
        await inter.response.send_message(embed=embed, ephemeral=True)
    
    @inventory_group.sub_command(name="use", description="Use an item from your inventory")
    async def use_item(self, inter: disnake.ApplicationCommandInteraction, item_name: str):
        """Use an item from your inventory
        
        Parameters
        ----------
        item_name: The name of the item to use
        """
        user_id = str(inter.author.id)
        
        # Get user data - this will depend on how your bot stores user data
        try:
            from botX_enhanced import get_user_data, save_user_data
            ud = get_user_data(inter.author.id)
        except ImportError:
            await inter.response.send_message("Error: Could not access user data functions.", ephemeral=True)
            return
        
        inventory = InventorySystem.get_user_inventory(user_id)
        
        # Find the item by name
        item_to_use = None
        item_index = -1
        for i, item in enumerate(inventory['items']):
            if item.get('name', '').lower() == item_name.lower():
                item_to_use = item
                item_index = i
                break
        
        if not item_to_use:
            await inter.response.send_message(
                f"❌ You don't have an item named '{item_name}' in your inventory.",
                ephemeral=True
            )
            return
        
        if not item_to_use.get('usable', False):
            await inter.response.send_message(
                f"❌ The item '{item_name}' cannot be used.",
                ephemeral=True
            )
            return
        
        # Process the item effect
        effect = item_to_use.get('effect', '')
        effect_description = "No effect"
        
        # Handle different item effects - examples:
        if 'coins:' in effect:
            try:
                coins_to_add = int(effect.split('coins:')[1].strip())
                ud['balance'] += coins_to_add
                save_user_data()
                effect_description = f"You received {coins_to_add} coins!"
            except:
                effect_description = "Error processing coin effect"
        elif 'boost:' in effect:
            try:
                boost_percent = int(effect.split('boost:')[1].strip())
                # Apply a temporary boost to the user
                # Implementation would depend on how boosts are tracked
                effect_description = f"Applied a {boost_percent}% boost to your earnings!"
            except:
                effect_description = "Error processing boost effect"
        else:
            effect_description = effect if effect else "This item has no effect"
        
        # Remove the item if it's not permanent
        if not item_to_use.get('permanent', False):
            # If item has quantity, reduce it
            if 'quantity' in item_to_use and item_to_use['quantity'] > 1:
                inventory['items'][item_index]['quantity'] -= 1
            else:
                # Otherwise remove the item
                inventory['items'].pop(item_index)
            
            InventorySystem.save_user_inventory(user_id, inventory)
        
        embed = disnake.Embed(
            title=f"✅ Used {item_name}",
            description=effect_description,
            color=disnake.Color.green()
        )
        
        await inter.response.send_message(embed=embed)

class TournamentCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="tournament", description="Participate in tournaments")
    async def tournament_group(self, inter: disnake.ApplicationCommandInteraction):
        """Tournament commands"""
        pass
    
    @tournament_group.sub_command(name="list", description="View available tournaments")
    async def list_tournaments(self, inter: disnake.ApplicationCommandInteraction):
        """List all available tournaments"""
        # We need to fetch tournaments from the database
        # For now, we'll simulate fetching from our utility
        
        # Since we don't have actual DB connection here, we'll fake it through the API
        try:
            import requests
            response = requests.get(f"http://localhost:5000/api/tournaments")
            tournaments = response.json() if response.status_code == 200 else []
        except Exception as e:
            logger.error(f"Error fetching tournaments: {e}")
            # If API fails, use empty list
            tournaments = []
        
        if not tournaments:
            await inter.response.send_message(
                "❌ No tournaments are currently available. Check back later!",
                ephemeral=True
            )
            return
        
        embed = disnake.Embed(
            title="🏆 Available Tournaments",
            description="Here are the tournaments you can participate in:",
            color=disnake.Color.gold()
        )
        
        for tournament in tournaments:
            status_emoji = "🔴"  # default
            if tournament.get('status') == 'active':
                status_emoji = "🟢"
            elif tournament.get('status') == 'upcoming':
                status_emoji = "🟡"
            elif tournament.get('status') == 'completed':
                status_emoji = "⚪"
            
            # Format dates
            start_date = tournament.get('start_date', '').replace('T', ' ').split('.')[0]
            end_date = tournament.get('end_date', '').replace('T', ' ').split('.')[0]
            
            value = f"**Game Type:** {tournament.get('game_type', 'Unknown')}\n"
            value += f"**Entry Fee:** {tournament.get('entry_fee', 0)} coins\n"
            value += f"**Prize Pool:** {tournament.get('prize_pool', 0)} coins\n"
            value += f"**Dates:** {start_date} to {end_date}\n"
            value += f"**Status:** {status_emoji} {tournament.get('status', 'unknown').title()}"
            
            embed.add_field(
                name=f"#{tournament.get('id')} - {tournament.get('name', 'Unknown Tournament')}",
                value=value,
                inline=False
            )
        
        await inter.response.send_message(embed=embed, ephemeral=False)
    
    @tournament_group.sub_command(name="join", description="Join a tournament")
    async def join_tournament(self, inter: disnake.ApplicationCommandInteraction, tournament_id: int):
        """Join a tournament
        
        Parameters
        ----------
        tournament_id: The ID of the tournament to join
        """
        user_id = str(inter.author.id)
        
        # Get user data functions
        try:
            from botX_enhanced import get_user_data, save_user_data
            ud = get_user_data(inter.author.id)
        except ImportError:
            await inter.response.send_message("Error: Could not access user data functions.", ephemeral=True)
            return
        
        # First, check if the tournament exists and is joinable
        try:
            import requests
            response = requests.get(f"http://localhost:5000/api/tournaments")
            all_tournaments = response.json() if response.status_code == 200 else []
            tournament = next((t for t in all_tournaments if t.get('id') == tournament_id), None)
        except Exception as e:
            logger.error(f"Error fetching tournament {tournament_id}: {e}")
            tournament = None
        
        if not tournament:
            await inter.response.send_message(
                f"❌ Tournament #{tournament_id} not found.",
                ephemeral=True
            )
            return
        
        if tournament.get('status') != 'active' and tournament.get('status') != 'upcoming':
            await inter.response.send_message(
                f"❌ Tournament #{tournament_id} is not open for registration.",
                ephemeral=True
            )
            return
        
        # Check if user has enough coins for entry fee
        entry_fee = tournament.get('entry_fee', 0)
        
        if ud['balance'] < entry_fee:
            await inter.response.send_message(
                f"❌ You don't have enough coins to join this tournament. Entry fee: {entry_fee} coins.",
                ephemeral=True
            )
            return
        
        # Register the user
        result = TournamentSystem.register_for_tournament(user_id, tournament_id)
        
        if result.get('success', False):
            # Deduct entry fee
            ud['balance'] -= entry_fee
            save_user_data()
            
            embed = disnake.Embed(
                title="🏆 Tournament Joined!",
                description=f"You have successfully joined the tournament **{tournament.get('name')}**!",
                color=disnake.Color.green()
            )
            
            embed.add_field(name="Entry Fee", value=f"{entry_fee} coins", inline=True)
            embed.add_field(name="Current Prize Pool", value=f"{tournament.get('prize_pool') + entry_fee} coins", inline=True)
            embed.add_field(name="Game Type", value=tournament.get('game_type', 'Unknown'), inline=True)
            
            await inter.response.send_message(embed=embed)
        else:
            await inter.response.send_message(
                f"❌ Failed to join tournament: {result.get('message', 'Unknown error')}",
                ephemeral=True
            )

class MinigameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        
    @commands.slash_command(name="minigame", description="Play fun minigames to earn coins")
    async def minigame_group(self, inter: disnake.ApplicationCommandInteraction):
        """Minigame commands"""
        pass
    
    @minigame_group.sub_command(name="list", description="List available minigames")
    async def list_minigames(self, inter: disnake.ApplicationCommandInteraction):
        """List all available minigames"""
        minigames = MinigameSystem.get_available_minigames()
        
        embed = disnake.Embed(
            title="🎮 Available Minigames",
            description="Play these fun minigames to earn coins!",
            color=disnake.Color.blue()
        )
        
        for game in minigames:
            embed.add_field(
                name=game.get('name', 'Unknown Game'),
                value=f"{game.get('description', 'No description')}\n**Rewards:** {game.get('rewards', 'None')}\n**Cooldown:** {game.get('cooldown_minutes', 0)} minutes",
                inline=False
            )
        
        embed.set_footer(text="Use /minigame play [game] to start a game!")
        await inter.response.send_message(embed=embed)
    
    @minigame_group.sub_command(name="play", description="Play a minigame")
    async def play_minigame(self, inter: disnake.ApplicationCommandInteraction, 
                         game: str = commands.Param(choices=["trivia", "wordscramble", "numberguess", "rockpaperscissors", "hangman"])):
        """Play a minigame
        
        Parameters
        ----------
        game: The minigame to play
        """
        user_id = inter.author.id
        
        # Check cooldown (this would be more sophisticated in real implementation)
        if user_id in self.active_games:
            await inter.response.send_message(
                "❌ You already have an active game! Finish it before starting a new one.",
                ephemeral=True
            )
            return
        
        # Initialize the game
        if game == "trivia":
            await self.start_trivia_game(inter)
        elif game == "wordscramble":
            await self.start_wordscramble_game(inter)
        elif game == "numberguess":
            await self.start_numberguess_game(inter)
        elif game == "rockpaperscissors":
            await self.start_rps_game(inter)
        elif game == "hangman":
            await self.start_hangman_game(inter)
        else:
            await inter.response.send_message(
                f"❌ Minigame '{game}' not implemented yet. Try another game!",
                ephemeral=True
            )
    
    async def start_trivia_game(self, inter: disnake.ApplicationCommandInteraction):
        """Start a trivia game"""
        # Sample trivia questions
        trivia_questions = [
            {
                "question": "What year was Discord founded?",
                "options": ["2012", "2015", "2016", "2018"],
                "correct": "2015"
            },
            {
                "question": "Which of these is NOT a default Discord role color?",
                "options": ["Red", "Blue", "Green", "Orange"],
                "correct": "Orange"
            },
            {
                "question": "What is the maximum number of users in a Discord server?",
                "options": ["100,000", "250,000", "500,000", "1,000,000"],
                "correct": "500,000"
            }
        ]
        
        # Select a random question
        question_data = random.choice(trivia_questions)
        
        embed = disnake.Embed(
            title="🧠 Discord Trivia",
            description=question_data["question"],
            color=disnake.Color.purple()
        )
        
        # Store the game state
        self.active_games[inter.author.id] = {
            "type": "trivia",
            "correct_answer": question_data["correct"],
            "start_time": datetime.datetime.now(timezone.utc)
        }
        
        # Create option buttons
        class TriviaView(disnake.ui.View):
            def __init__(self, cog, options, correct):
                super().__init__(timeout=30.0)
                self.cog = cog
                self.correct = correct
                self.user_id = inter.author.id
                
                # Add option buttons
                for option in options:
                    button = disnake.ui.Button(
                        label=option, 
                        style=disnake.ButtonStyle.secondary,
                        custom_id=f"trivia:{option}"
                    )
                    button.callback = self.button_callback
                    self.add_item(button)
            
            async def button_callback(self, button_inter: disnake.MessageInteraction):
                # Only allow the original user to answer
                if button_inter.author.id != self.user_id:
                    await button_inter.response.send_message(
                        "❌ This isn't your game!", ephemeral=True
                    )
                    return
                
                # Extract the answer from the button
                chosen_answer = button_inter.component.custom_id.split(":")[1]
                
                # Clean up the game state
                if self.user_id in self.cog.active_games:
                    del self.cog.active_games[self.user_id]
                
                # Get user data functions
                try:
                    from botX_enhanced import get_user_data, save_user_data
                except ImportError:
                    await button_inter.response.send_message("Error: Could not access user data functions.", ephemeral=True)
                    return
                
                # Check if answer is correct
                if chosen_answer == self.correct:
                    # Award coins
                    reward = random.randint(10, 50)
                    ud = get_user_data(self.user_id)
                    ud['balance'] += reward
                    save_user_data()
                    
                    result_embed = disnake.Embed(
                        title="✅ Correct Answer!",
                        description=f"You won {reward} coins for your knowledge!",
                        color=disnake.Color.green()
                    )
                else:
                    result_embed = disnake.Embed(
                        title="❌ Wrong Answer!",
                        description=f"The correct answer was: {self.correct}",
                        color=disnake.Color.red()
                    )
                
                # Update the message with the result
                await button_inter.response.edit_message(embed=result_embed, view=None)
            
            async def on_timeout(self):
                # Remove the game from active games
                if self.user_id in self.cog.active_games:
                    del self.cog.active_games[self.user_id]
                
                # Edit the message to show timeout
                timeout_embed = disnake.Embed(
                    title="⏱️ Time's Up!",
                    description="You ran out of time to answer the question.",
                    color=disnake.Color.orange()
                )
                
                await self.message.edit(embed=timeout_embed, view=None)
        
        # Create and send the view
        view = TriviaView(self, question_data["options"], question_data["correct"])
        await inter.response.send_message(embed=embed, view=view)
        view.message = await inter.original_message()
    
    async def start_wordscramble_game(self, inter: disnake.ApplicationCommandInteraction):
        """Start a word scramble game"""
        await inter.response.send_message(
            "🎮 Word Scramble game is coming soon! Try another minigame.",
            ephemeral=True
        )
        
        # Clean up game state just in case
        if inter.author.id in self.active_games:
            del self.active_games[inter.author.id]
    
    async def start_numberguess_game(self, inter: disnake.ApplicationCommandInteraction):
        """Start a number guessing game"""
        await inter.response.send_message(
            "🎮 Number Guessing game is coming soon! Try another minigame.",
            ephemeral=True
        )
        
        # Clean up game state just in case
        if inter.author.id in self.active_games:
            del self.active_games[inter.author.id]
    
    async def start_rps_game(self, inter: disnake.ApplicationCommandInteraction):
        """Start a rock paper scissors game"""
        embed = disnake.Embed(
            title="✂️ Rock Paper Scissors",
            description="Choose your move!",
            color=disnake.Color.purple()
        )
        
        # Store the game state
        self.active_games[inter.author.id] = {
            "type": "rps",
            "start_time": datetime.datetime.now(timezone.utc)
        }
        
        # Create buttons for RPS choices
        class RPSView(disnake.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=30.0)
                self.cog = cog
                self.user_id = inter.author.id
                
                # Add choice buttons
                choices = [
                    ("🪨 Rock", "rock", disnake.ButtonStyle.gray),
                    ("📄 Paper", "paper", disnake.ButtonStyle.green),
                    ("✂️ Scissors", "scissors", disnake.ButtonStyle.danger)
                ]
                
                for label, value, style in choices:
                    button = disnake.ui.Button(
                        label=label, 
                        style=style,
                        custom_id=f"rps:{value}"
                    )
                    button.callback = self.button_callback
                    self.add_item(button)
            
            async def button_callback(self, button_inter: disnake.MessageInteraction):
                # Only allow the original user to play
                if button_inter.author.id != self.user_id:
                    await button_inter.response.send_message(
                        "❌ This isn't your game!", ephemeral=True
                    )
                    return
                
                # Extract the choice
                player_choice = button_inter.component.custom_id.split(":")[1]
                
                # Clean up the game state
                if self.user_id in self.cog.active_games:
                    del self.cog.active_games[self.user_id]
                
                # Get user data functions
                try:
                    from botX_enhanced import get_user_data, save_user_data
                except ImportError:
                    await button_inter.response.send_message("Error: Could not access user data functions.", ephemeral=True)
                    return
                
                # Bot makes a choice
                choices = ["rock", "paper", "scissors"]
                bot_choice = random.choice(choices)
                
                # Determine winner
                if player_choice == bot_choice:
                    result = "It's a tie!"
                    reward = 5
                    color = disnake.Color.blue()
                elif (player_choice == "rock" and bot_choice == "scissors") or \
                     (player_choice == "paper" and bot_choice == "rock") or \
                     (player_choice == "scissors" and bot_choice == "paper"):
                    result = "You win!"
                    reward = 15
                    color = disnake.Color.green()
                else:
                    result = "You lose!"
                    reward = 0
                    color = disnake.Color.red()
                
                # Award coins if player won or tied
                if reward > 0:
                    ud = get_user_data(self.user_id)
                    ud['balance'] += reward
                    save_user_data()
                
                # Map choices to emojis
                choice_emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
                
                result_embed = disnake.Embed(
                    title="✂️ Rock Paper Scissors Result",
                    description=f"You chose: {choice_emojis[player_choice]} {player_choice.title()}\nBot chose: {choice_emojis[bot_choice]} {bot_choice.title()}\n\n**{result}**",
                    color=color
                )
                
                if reward > 0:
                    result_embed.add_field(name="Reward", value=f"+{reward} coins", inline=False)
                
                # Update the message with the result
                await button_inter.response.edit_message(embed=result_embed, view=None)
            
            async def on_timeout(self):
                # Remove the game from active games
                if self.user_id in self.cog.active_games:
                    del self.cog.active_games[self.user_id]
                
                # Edit the message to show timeout
                timeout_embed = disnake.Embed(
                    title="⏱️ Time's Up!",
                    description="You took too long to make a choice.",
                    color=disnake.Color.orange()
                )
                
                await self.message.edit(embed=timeout_embed, view=None)
        
        # Create and send the view
        view = RPSView(self)
        await inter.response.send_message(embed=embed, view=view)
        view.message = await inter.original_message()
    
    async def start_hangman_game(self, inter: disnake.ApplicationCommandInteraction):
        """Start a hangman game"""
        # Placeholder implementation - would be more sophisticated in real bot
        await inter.response.send_message(
            "🎮 Hangman minigame is coming soon! Check back later for this exciting word guessing game.",
            ephemeral=True
        )
        
        # Clean up game state just in case
        if inter.author.id in self.active_games:
            del self.active_games[inter.author.id]