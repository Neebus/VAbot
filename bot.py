# =======================
# IMPORTS
# =======================
import discord
import json
from discord.ext import commands, tasks
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta, date
import os
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
import time
from collections import defaultdict
from io import BytesIO
from collections import Counter
import itertools
import math












# =======================
# DATABASE – Setup
# =======================
def setup_database():
    """Ensures all required database tables exist in bot.db."""
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    # -----------------------
    # User profiles and stats
    # -----------------------
    c.execute('''CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        about TEXT DEFAULT "I'm mysterious",
        status TEXT DEFAULT "Single",
        crush TEXT,
        contentment INTEGER DEFAULT 0,
        rep_count INTEGER DEFAULT 0,
        kek_count INTEGER DEFAULT 0,
        marriages INTEGER DEFAULT 0,
        ex_spouses TEXT,
        currency INTEGER DEFAULT 0,
        last_payday TIMESTAMP,
        last_rep TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # -----------------------
    # Quotes log
    # -----------------------
    c.execute('''CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT,
        author_id INTEGER,
        channel_id INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # -----------------------
    # Marriage tracking
    # -----------------------
    c.execute('''CREATE TABLE IF NOT EXISTS marriages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1_id INTEGER,
        user2_id INTEGER,
        married_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

   

    # -----------------------
    # Kekw Reaction Log
    # -----------------------
    c.execute('''
    CREATE TABLE IF NOT EXISTS kekw_log (
        reactor_id INTEGER,
        author_id INTEGER,
        message_id INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()



# =======================
# DATABASE – Utility Functions
# =======================

def ensure_profile(user_id):
    """Ensures a user profile exists in the database (does nothing if it already exists)."""
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO profiles (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()


# =======================
# BOT STARTUP – Init & Globals
# =======================
# =========================
# Jackpot Saving
# =========================
JACKPOT_FILE = "jackpot.json"

# Load jackpot from file or initialize
def load_jackpot():
    if os.path.exists(JACKPOT_FILE):
        with open(JACKPOT_FILE, "r") as f:
            return json.load(f)
    return {"amount": 0}

# Save jackpot anytime it's changed
def save_jackpot():
    with open(JACKPOT_FILE, "w") as f:
        json.dump(jackpot, f)

# Load the actual jackpot dict on startup
jackpot = load_jackpot()



# Set up all necessary database tables
setup_database()

# Active game sessions (e.g., Blackjack, Duels, etc.)
active_games = {}

# Temporary quote buffer for logging or review before saving
quotes = []

# Stores simple fortune memory to avoid getting the same fortune per day
daily_fortunes = defaultdict(lambda: {"date": None, "used": set()})


#Horserace Jackpot
carry_over_pot = 0


# =======================
# CONFIGURATION - Setup
# =======================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.guilds = True
intents.members = True
intents.reactions = True



bot = commands.Bot(command_prefix='=', help_command=None, intents=intents)


CHANNEL_IDS = {
    'DEGENERAL': 1347325579686314014,
    'QUOTES': 1361748419261108466,
    'BEST_OF': 1361744217319276777,
    'CASINO': 1361744369178251497
}

# =======================
# CONFIGURATION – Intents
# =======================

intents = discord.Intents.default()
intents.message_content = True   # Required to read user messages
intents.reactions = True         # Required to track emoji reactions
intents.members = True           # Required for member join/leave/events



# =======================
# CONFIGURATION – Role Shop
# =======================

ROLE_SHOP = {
    "Azure": 50000,
    "Blue": 50000,
    "Navy": 50000,
    "Teal": 50000,
    "Green": 50000,
    "Neon Green": 50000,
    "Canary": 50000,
    "Coral": 50000,
    "Red": 50000,
    "Purple": 50000,
    "Lavender": 50000,
    "Black": 50000,
    "Pink": 50000,
    "Magenta": 50000,

    "Gambler": 100000,
    "Pushin 🅿️": 250000,
    "Step-Bro": 250000,
    "Step-Sis": 250000,

    "Horny X": 2500000,
    "High Roller": 2500000,
    "pussyslayer": 2500000,
    "Gluck Gluck 2000": 2500000,

    "No-Simping": 1000000,
    "Corn Queen": 1000000,
    "1,000,000 Tendies": 1000000,
    "5,000,000 Tendies": 5000000,
    "20 Million Tendies": 20000000,
    "50 million Tendies": 50000000,

    "Taco King": 10000000,
    "Rizzinator": 10000000
}
# =======================
# CONFIGURATION – Potion Healing
# =======================

POTION_HEALING = {
    "Small Potion": 30,
    "Minor Healing Elixir": 40,
    "Potion": 50,
    "Mega Potion": 75,
    "Elixir of Immortality": 100
}




# =======================
# GLOBAL STATE – Cooldowns
# =======================
work_cooldowns = defaultdict(lambda: 0)
allin_cooldowns = defaultdict(lambda: 0)
slots_cooldowns = defaultdict(float)
cooldown_timer = 120  # in seconds
rob_cooldowns = defaultdict(lambda: 0)



# =======================
# DATABASE FUNCTIONS
# =======================

# =======================
# HELPER FUNCTIONS – Card Game Tools
# =======================

def draw_hand(deck, n=5):
    """Draws `n` cards from the deck by popping them off the end."""
    if len(deck) < n:
        raise ValueError("Not enough cards in the deck to draw a full hand.")
    return [deck.pop() for _ in range(n)]


# =======================
# HELPER FUNCTIONS – Card Game Tools
# =======================

def create_deck():
    """Creates a standard 52-card deck using suits and values."""
    suits = ['♠', '♥', '♦', '♣']
    values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    return [f"{v}{s}" for s in suits for v in values]

# =======================
# GAME DATA – Suits as Emoji
# =======================

SUITS = {
    '♠': '♠️',
    '♥': '♥️',
    '♦': '♦️',
    '♣': '♣️'
}



# =======================
# HELPER FUNCTIONS – Blackjack Hand Value
# =======================

def evaluate_hand_with_name(hand, community):
    """Evaluates a poker hand and returns a tuple of (rank, values, hand name)."""
    
    cards = hand + community
    values = []
    suits = []

    # Extract value and suit from each card
    for card in cards:
        val = card[:-1]  # '10H' -> '10', 'KS' -> 'K'
        suit = card[-1]  # '10H' -> 'H', 'KS' -> 'S'
        suits.append(suit)
        if val == 'A':
            values.append(14)
        elif val == 'K':
            values.append(13)
        elif val == 'Q':
            values.append(12)
        elif val == 'J':
            values.append(11)
        else:
            try:
                values.append(int(val))
            except ValueError:
                # ⚠️ Optional: catch malformed card input
                continue

    values.sort(reverse=True)
    val_counts = Counter(values)
    suit_counts = Counter(suits)

    def has_flush():
        return any(count >= 5 for count in suit_counts.values())

    def has_straight():
        unique = sorted(set(values), reverse=True)
        for i in range(len(unique) - 4):
            if unique[i] - unique[i + 4] == 4:
                return True
        # Ace-low straight (A, 2, 3, 4, 5)
        if {14, 2, 3, 4, 5}.issubset(set(values)):
            return True
        return False

    # Hand ranking logic
    if has_flush() and has_straight():
        return (8, values, "Straight Flush")
    if 4 in val_counts.values():
        return (7, values, "Four of a Kind")
    if 3 in val_counts.values() and 2 in val_counts.values():
        return (6, values, "Full House")
    if has_flush():
        return (5, values, "Flush")
    if has_straight():
        return (4, values, "Straight")
    if 3 in val_counts.values():
        return (3, values, "Three of a Kind")
    if list(val_counts.values()).count(2) >= 2:
        return (2, values, "Two Pair")
    if 2 in val_counts.values():
        return (1, values, "One Pair")
    return (0, values, "High Card")


# =======================
# HELPER FUNCTIONS – Horse Name Generator
# =======================

import random  # Ensure this is at the top of your file if not already imported

adjectives = [
    "Blazing", "Majestic", "Wild", "Crimson", "Gay", "Silver",
    "Thunder", "Velvet", "Shadow", "Golden", "Stormy"
]

nouns = [
    "Whirl", "Runner", "Spirit", "Bolt", "Loser", "Dream",
    "Streak", "Dash", "Gale", "Hoof", "Wind"
]

def generate_horse_names(amount=5):
    """Generate a list of unique and fun horse names."""
    horse_names = set()
    while len(horse_names) < amount:
        name = f"{random.choice(adjectives)} {random.choice(nouns)}"
        horse_names.add(name)
    return list(horse_names)




# =======================
# GAME DATA – Tarot Cards
# =======================

tarot_cards = {
    "The Fool": "New beginnings, innocence, spontaneity.",
    "The Magician": "Manifestation, power, resourcefulness.",
    "The High Priestess": "Intuition, subconscious, divine feminine.",
    "The Empress": "Fertility, nurturing, abundance.",
    "The Emperor": "Authority, structure, control.",
    "The Lovers": "Love, harmony, choices.",
    "The Chariot": "Determination, control, victory.",
    "Strength": "Courage, inner strength, patience.",
    "The Hermit": "Introspection, solitude, guidance.",
    "Wheel of Fortune": "Cycles, luck, fate.",
    "Justice": "Fairness, truth, law.",
    "The Hanged Man": "Letting go, new perspective, pause.",
    "Death": "Endings, transformation, transition.",
    "Temperance": "Balance, moderation, harmony.",
    "The Devil": "Addiction, materialism, shadow self.",
    "The Tower": "Upheaval, chaos, revelation.",
    "The Star": "Hope, inspiration, spirituality.",
    "The Moon": "Illusion, fear, intuition.",
    "The Sun": "Joy, success, celebration.",
    "Judgement": "Reflection, reckoning, awakening.",
    "The World": "Completion, accomplishment, integration."
}


# =======================
# GAME DATA – Fortunes
# =======================

fortunes = [
    "You will moan in your sleep tonight. Loudly. Your mic will be on.",
    "Someone will say “step on me” unironically. It might be you.",
    "You’ll accidentally send the thirst trap to the family group chat.",
    "A demon is watching you scroll. They’re judging your kinks.",
    "You will reply “lol” to a trauma dump. The universe saw that.",
    "Your next crush will be toxic, broke, and hot. Again.",
    "The ghosts in your room saw what you did last night. They’re telling the others.",
    "You will get exactly one unsolicited pic today. It's not the kind you want.",
    "The algorithm knows your type — and it’s exposing you.",
    "You will accidentally flirt with a customer service rep. They’ll flirt back.",
    "Today you will gaslight, gatekeep, and girlboss — in that order.",
    "Your phone will autocorrect ‘haha’ to ‘I love you.’ You won’t notice in time.",
    "Someone will call you 'mommy' today. It won’t be a child.",
    "You will overshare in a group chat. A screenshot is already being sent elsewhere.",
    "You will feel mysterious today. But mostly because you forgot deodorant.",
    "Someone will fall in love with you because of a meme. Their standards are low.",
    "You will make eye contact with someone too long. Now you’re engaged.",
    "You will be haunted by a typo in a thirst trap caption. It will be biblical.",
    "You will accidentally double tap a 2014 selfie. War has begun.",
    "You will read into a ‘hey’ and spiral for 3–5 business days.",
    "Your cat knows your secrets. They are not impressed.",
    "You’ll make a playlist for someone who ghosts you immediately.",
    "Someone will say ‘we need to talk.’ You will stop breathing.",
    "You will look stunning today. To someone deeply unhinged.",
    "You’ll say 'it’s fine' but start plotting emotional revenge.",
    "You will get a compliment. You’ll question it for 7 hours.",
    "Your ex will post a quote that’s clearly about you. You will win the passive-aggression war.",
    "You will pretend to understand a meme. You will be exposed.",
    "A stranger will hit on you today. It will be unsettling and somehow involve anime.",
    "You will dream of someone inappropriate. And wake up confused and aroused.",
    "You’ll say “just one drink” and wake up in a stranger’s bathtub.",
    "Mercury is in retrograde. So is your will to live.",
    "Your favorite song will remind you of someone you ghosted. Deserved.",
    "You will send a risky message. Then instantly regret it. But it’s too late.",
    "Your FBI agent took screenshots. For fun.",
    "You will get attention today. The wrong kind. From the weirdest man alive.",
    "You will radiate ✨feral slut energy✨. No one will stop you.",
    "You’re one coffee away from committing war crimes in the group chat.",
    "Someone will confess a kink to you today. You will not recover.",
    "You will run into an ex while looking *unholy* on a Target run."
]

# =======================
# GAME DATA – Poker Hand Ranks
# =======================

# Poker hand rankings from highest to lowest
POKER_HAND_RANKS = [
    "Royal Flush",
    "Straight Flush",
    "Four of a Kind",
    "Full House",
    "Flush",
    "Straight",
    "Three of a Kind",
    "Two Pair",
    "One Pair",
    "High Card"
]



# =======================
# CLASSES – BlackjackGame
# =======================

class BlackjackGame:
    def __init__(self, player_id, bet):
        self.player_id = player_id
        self.bet = bet
        self.deck = self.create_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.game_over = False
        self.msg = None  # Optional: Used to store the message object if needed for editing

    def create_deck(self):
        """Creates and shuffles a standard 52-card deck."""
        suits = ['♠', '♥', '♦', '♣']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [f"{v}{s}" for s in suits for v in values]
        random.shuffle(deck)
        return deck

    def calculate_hand(self, hand):
        """Calculates the value of a blackjack hand."""
        value = 0
        aces = 0
        for card in hand:
            val = card[:-1]
            if val in ['J', 'Q', 'K']:
                value += 10
            elif val == 'A':
                aces += 1
            else:
                value += int(val)

        for _ in range(aces):
            # Choose best ace value without busting
            value += 11 if value + 11 <= 21 else 1
        return value

    def format_hand(self, hand):
        """Returns a formatted string of the hand with emoji suits."""
        return ', '.join([f"{c[:-1]}{SUITS.get(c[-1], c[-1])}" for c in hand])




# =======================
# EVENTS - Bot Lifecycle
# =======================

@bot.event
async def on_ready():
    print(f'{bot.user} is online.')

    # Start background tasks only once
    if not post_random_quote.is_running():
        post_random_quote.start()



# =======================
# EVENTS – on_message
# =======================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    ensure_profile(user_id)

    # -----------------------
    # XP SYSTEM
    # -----------------------
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    xp_gain = random.randint(5, 15)
    c.execute('SELECT xp, level FROM profiles WHERE user_id = ?', (user_id,))
    row = c.fetchone()

    if row:
        xp, level = row
        new_xp = xp + xp_gain
        next_level = int((level + 1) ** 2 * 10)

        if new_xp >= next_level:
            new_level = level + 1
            new_xp -= next_level
            c.execute('UPDATE profiles SET xp = ?, level = ? WHERE user_id = ?', (new_xp, new_level, user_id))
            await message.channel.send(f"🌟 {message.author.mention} leveled up to **Level {new_level}**!")
        else:
            c.execute('UPDATE profiles SET xp = ? WHERE user_id = ?', (new_xp, user_id))

    conn.commit()
    conn.close()

    # -----------------------
    # QUOTE SYSTEM
    # -----------------------
    if message.reference and message.content.lower() == "quote":
        try:
            original = await message.channel.fetch_message(message.reference.message_id)
        except discord.NotFound:
            return await message.channel.send("⚠️ Couldn’t find the referenced message.")

        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute(
            'INSERT INTO quotes (content, author_id, channel_id) VALUES (?, ?, ?)',
            (original.content, original.author.id, original.channel.id)
        )
        conn.commit()
        conn.close()

        quote_channel = bot.get_channel(CHANNEL_IDS['QUOTES'])
        if quote_channel:
            embed = discord.Embed(description=original.content, color=discord.Color.blue())
            embed.set_author(name=original.author.name)
            await quote_channel.send(embed=embed)

    # -----------------------
    # Forward to command processor
    # -----------------------
    await bot.process_commands(message)

# =======================
# EVENTS – on_reaction_add
# =======================
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    if not hasattr(reaction.emoji, "name") or reaction.emoji.name.lower() != "kekw":
        return

    message = reaction.message
    author = message.author

    # Ensure profile exists for the message author
    ensure_profile(author.id)

    # Count kekw reactions on the message
    kekw_count = 0
    for react in message.reactions:
        if hasattr(react.emoji, "name") and react.emoji.name.lower() == "kekw":
            kekw_count = react.count
            break

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    # ✅ Always increment kek_count by 1 for the author of the kekw’d message
    c.execute('UPDATE profiles SET kek_count = kek_count + 1 WHERE user_id = ?', (author.id,))

    # ✅ If the message *just hit* 4 kekw reactions, post it to best-of
    if kekw_count == 4:
        best_of = bot.get_channel(CHANNEL_IDS['BEST_OF'])
        if best_of:
            embed = discord.Embed(description=message.content, color=discord.Color.orange())
            embed.set_author(name=author.display_name)
            embed.set_footer(text=f"From #{message.channel.name}")
            await best_of.send(embed=embed)

    # ✅ Log kekw interaction
    c.execute(
        'INSERT INTO kekw_log (reactor_id, author_id, message_id) VALUES (?, ?, ?)',
        (user.id, author.id, message.id)
    )

    # ✅ Auto-update crush based on most kekw’d author
    c.execute('''
        SELECT author_id, COUNT(*) as total
        FROM kekw_log
        WHERE reactor_id = ?
        GROUP BY author_id
        ORDER BY total DESC
        LIMIT 1
    ''', (user.id,))
    top_result = c.fetchone()

    if top_result:
        top_crush_id = top_result[0]
        top_crush_member = message.guild.get_member(top_crush_id)
        if top_crush_member:
            c.execute(
                'UPDATE profiles SET crush = ? WHERE user_id = ?',
                (top_crush_member.display_name, user.id)
            )

    # ✅ Commit all changes after everything is done
    conn.commit()
    conn.close()

# =======================
# TASKS – Background Quote Poster
# =======================

@tasks.loop(hours=1.0)
async def post_random_quote():
    """Sends a random quote to the DEGENERAL channel every 30 minutes."""
    try:
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute('SELECT content FROM quotes ORDER BY RANDOM() LIMIT 1')
        row = c.fetchone()
        conn.close()

        if row and row[0].strip():  # Ensure the quote isn't empty or whitespace
            channel = bot.get_channel(CHANNEL_IDS['DEGENERAL'])
            if channel:
                await channel.send(row[0])

    except Exception as e:
        print(f"[Quote Post Error] {e}")




# =======================
# BOT COMMANDS
# =======================


# =======================
# COMMANDS – Fun / Rob
# =======================
@bot.command()
async def rob(ctx, target: discord.Member):
    """Attempt to rob another user for VAbux."""
    if ctx.author == target:
        return await ctx.send("🤨 You can't rob yourself.")
    if target.bot:
        return await ctx.send("🤖 Robbing a bot? Grow up.")

    robber_id = ctx.author.id
    target_id = target.id

    # Cooldown check (1 hour)
    now = time.time()
    if now - rob_cooldowns[robber_id] < 3600:
        wait = int(3600 - (now - rob_cooldowns[robber_id]))
        return await ctx.send(f"🕒 You're laying low. Try again in {wait // 60}m {wait % 60}s.")
    rob_cooldowns[robber_id] = now

    ensure_profile(robber_id)
    ensure_profile(target_id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    # Check balances
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (target_id,))
    target_balance = c.fetchone()[0]
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (robber_id,))
    robber_balance = c.fetchone()[0]

    if target_balance < 2000:
        conn.close()
        return await ctx.send(f"💼 {target.display_name} doesn’t have enough VAbux to rob.")

    # Attempt robbery (25% success)
    success = random.random() < 0.25
    if success:
        stolen = random.randint(2000, min(20000, target_balance))
        c.execute('UPDATE profiles SET currency = currency - ? WHERE user_id = ?', (stolen, target_id))
        c.execute('UPDATE profiles SET currency = currency + ? WHERE user_id = ?', (stolen, robber_id))
        conn.commit()
        conn.close()
        await ctx.send(f"🕶️ {ctx.author.display_name} successfully robbed {target.display_name} for 💰 **{stolen:,} VAbux**!")
    else:
        fine = random.randint(2000, 10000)
        fine_paid = min(fine, robber_balance)
        c.execute('UPDATE profiles SET currency = currency - ? WHERE user_id = ?', (fine_paid, robber_id))
        conn.commit()
        conn.close()

        response = f"🚨 You were **caught** trying to rob {target.display_name} and paid a **{fine_paid:,} VAbux** fine!"

        if fine_paid < fine:
            prisoner_role = discord.utils.get(ctx.guild.roles, name="Prisoner")
            if prisoner_role:
                await ctx.author.add_roles(prisoner_role)
                response += f"\n🏛️ You couldn’t pay the full fine and were thrown in **prison**!"
            else:
                response += "\n⚠️ 'Prisoner' role not found."

        await ctx.send(response)


# =======================
# COMMANDS – Fun / iReally
# =======================
@bot.command()
async def ireally(ctx, member: discord.Member = None):
    """Overlays the 'I really' meme on a user's avatar."""
    member = member or ctx.author

    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            if resp.status != 200:
                return await ctx.send("Couldn't download the avatar 😢")
            data = io.BytesIO(await resp.read())

    avatar = Image.open(data).convert("RGBA").resize((512, 512))
    overlay = Image.open("ireally_overlay.png").convert("RGBA").resize((512, 512))

    combined = Image.alpha_composite(avatar, overlay)

    with io.BytesIO() as image_binary:
        combined.save(image_binary, "PNG")
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename="ireally.png"))

# =======================
# COMMANDS – Fun / Penis
# =======================
@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)  # 1 use per 5 seconds per user
async def penis(ctx, *members: discord.Member):
    """Measures the... uh, digital endowment of one or more members."""
    if not members:
        members = [ctx.author]

    response = ""

    for member in members:
        # Seed RNG with user ID and current date (UTC) for daily consistency
        today = datetime.utcnow().date().isoformat()
        seed = f"{member.id}-{today}"
        random.seed(seed)

        size = random.randint(0, 20)
        dong = "8" + ("=" * size) + "D"

        if size == 0:
            comment = "🔍 Where is it?"
        elif size < 4:
            comment = "🥒 Little pickle."
        elif size < 10:
            comment = "📏 Eh.... Average I guess."
        elif size < 16:
            comment = "🍆 Now that's a dong!"
        else:
            comment = "🚒 That's a WMD."

        response += f"**{member.display_name}’s size:**\n{dong}\n{comment}\n\n"

    await ctx.send(response.strip())

    # Reset random seed to avoid affecting other logic
    random.seed()

# =======================
# COMMANDS – Fun / Sanity
# =======================

@bot.command()
async def sanity(ctx, member: discord.Member = None):
    member = member or ctx.author
    percent = random.randint(0, 100)
    bar = "█" * (percent // 5) + "░" * (20 - (percent // 5))
    embed = discord.Embed(
        title=f"{member.display_name}'s Sanity Check",
        description=f"[{bar}] {percent}%",
        color=0x7289da
    )
    await ctx.send(embed=embed)

# =======================
# COMMANDS – Fun / Simprate
# =======================

@bot.command()
async def simprate(ctx, member: discord.Member = None):
    member = member or ctx.author
    percent = random.randint(0, 100)
    bar = "█" * (percent // 5) + "░" * (20 - (percent // 5))
    embed = discord.Embed(
        description=f"**{member.display_name}** is {percent}% simp 🥺\n[{bar}] {percent}%",
        color=0xff69b4
    )
    await ctx.send(embed=embed)

# =======================
# COMMANDS – Fun / IQ
# =======================

@bot.command()
async def iq(ctx, member: discord.Member = None):
    member = member or ctx.author
    iq_score = random.choices(
        [1, random.randint(50, 150), 200],
        weights=[0.1, 0.85, 0.05],
        k=1
    )[0]
    emoji = "😔" if iq_score <= 50 else "🧠" if iq_score < 150 else "🧙"
    embed = discord.Embed(
        description=f"**{member.display_name}**'s IQ\n**{iq_score}** {emoji}",
        color=0xabcdef
    )
    await ctx.send(embed=embed)











# =======================
# COMMANDS – Admin Tools / Currency
# =======================

@bot.command()
@commands.has_permissions(administrator=True)
async def givebucks(ctx, member: discord.Member):
    """Gives 1000 VAbux to the mentioned user."""
    user_id = member.id

    # Use local connection to avoid global DB issues
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (user_id,))
    result = c.fetchone()

    if not result:
        conn.close()
        await ctx.send("❌ That user doesn’t have a profile.")
        return

    new_balance = result[0] + 1000
    c.execute('UPDATE profiles SET currency = ? WHERE user_id = ?', (new_balance, user_id))
    conn.commit()
    conn.close()

    await ctx.send(
        f"💸 Gave **1000 VAbux** to {member.display_name}. "
        f"They now have **{new_balance:,} VAbux**."
    )


# =======================
# COMMANDS – Currency / Jobs
# =======================

@bot.command()
async def work(ctx):
    """Earns currency once every 30 minutes with a randomly chosen cursed job title."""
    user_id = ctx.author.id
    now = time.time()

    COOLDOWN_SECONDS = 1800  # 30 minutes

    # Check cooldown
    if now - work_cooldowns[user_id] < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - (now - work_cooldowns[user_id]))
        return await ctx.send(
            f"🕒 You need to wait {remaining // 60} minutes and {remaining % 60} seconds before working again."
        )

    work_cooldowns[user_id] = now

    jobs = [
        "TikTok toe-lick challenge moderator",
        "beanbag deflator via body slam",
        "waffle house bouncer at 3am",
        "unofficial exorcist for haunted Roombas",
        "AI bot flirter (must pass CAPTCHA)",
        "emotional support himbo (paid in cuddles)",
        "cryptid paparazzi",
        "dungeon NPC screamer (remote OK)",
        "professional overthinker with benefits",
        "feral raccoon translator",
        "OnlyFans foot photographer",
        "subway pole pole-dancer (unlicensed)",
        "emergency fart jar technician",
        "NPC moaner in hentai visual novels",
        "sock sniff quality assurance intern",
        "bidet temperature tester",
        "toilet seat warmer with personal cheeks",
        "anime orgasm dubber (volunteer)",
        "shadow government sleep paralysis demon",
        "virtual furry convention janitor"
    ]

    job = random.choice(jobs)
    pay = random.randint(1, 5000)

    ensure_profile(user_id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('UPDATE profiles SET currency = currency + ? WHERE user_id = ?', (pay, user_id))
    conn.commit()
    conn.close()

    await ctx.send(
        f"💼 You worked as a **{job}** and earned **{pay:,} VABux**."
    )


# =======================
# COMMANDS – Currency / Payday
# =======================
@bot.command()
async def payday(ctx):
    """Collect your daily 10,000 VAbux payday (every 24 hours)."""
    ensure_profile(ctx.author.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT currency, last_payday FROM profiles WHERE user_id = ?', (ctx.author.id,))
    currency, last = c.fetchone()
    now = datetime.now()

    # Handle cooldown
    if last:
        try:
            last_time = datetime.strptime(last, '%Y-%m-%d %H:%M:%S')
            if now - last_time < timedelta(hours=24):
                remaining = timedelta(hours=24) - (now - last_time)
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes = remainder // 60
                await ctx.send(f"🕒 You need to wait **{hours}h {minutes}m** before claiming payday again.")
                conn.close()
                return
        except ValueError:
            # fallback: invalid timestamp format
            pass

    # Grant reward
    currency += 10_000
    new_time = now.strftime('%Y-%m-%d %H:%M:%S')
    c.execute(
        'UPDATE profiles SET currency = ?, last_payday = ? WHERE user_id = ?',
        (currency, new_time, ctx.author.id)
    )
    conn.commit()
    conn.close()

    await ctx.send(f"💰 You received **10,000 VAbux**! New balance: **{currency:,}**")


# =======================
# COMMANDS – Currency / Transfer
# =======================

@bot.command()
async def transfer(ctx, member: discord.Member, amount: int):
    """Transfers VAbux to another member."""
    if amount <= 0:
        return await ctx.send("❌ Amount must be greater than zero.")
    if member == ctx.author:
        return await ctx.send("❌ You can't transfer currency to yourself.")

    ensure_profile(ctx.author.id)
    ensure_profile(member.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    # Check sender balance
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (ctx.author.id,))
    sender_balance = c.fetchone()[0]

    if sender_balance < amount:
        conn.close()
        return await ctx.send("💸 You don’t have enough VAbux for that transfer.")

    # Perform the transfer
    c.execute('UPDATE profiles SET currency = currency - ? WHERE user_id = ?', (amount, ctx.author.id))
    c.execute('UPDATE profiles SET currency = currency + ? WHERE user_id = ?', (amount, member.id))

    conn.commit()
    conn.close()

    await ctx.send(f"💸 {ctx.author.mention} sent **{amount:,} VAbux** to {member.mention}!")


# =======================
# COMMANDS – Currency / Balance Check
# =======================
@bot.command()
async def balance(ctx, member: discord.Member = None):
    """Check your or another user's currency balance."""
    member = member or ctx.author
    ensure_profile(member.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (member.id,))
    result = c.fetchone()
    conn.close()

    balance = result[0] if result else 0
    await ctx.send(f"💰 **{member.display_name}** has **{balance:,} VAbux**.")




# =======================
# COMMANDS – Currency / Role Shop
# =======================

@bot.command()
async def shop(ctx):
    """Displays the role shop with prices, paginated by reactions."""
    role_list = list(ROLE_SHOP.items())
    pages = [role_list[i:i + 10] for i in range(0, len(role_list), 10)]  # 10 per page
    total_pages = len(pages)
    current_page = 0

    def get_embed(page_index):
        embed = discord.Embed(
            title=f"🛒 Role Shop — Page {page_index + 1}/{total_pages}",
            color=discord.Color.teal()
        )

        chunk = pages[page_index]
        left_col = ""
        right_col = ""

        for i, (role, price) in enumerate(chunk):
            line = f"**{role}**\n💰 {price:,}\n\n"
            if i % 2 == 0:
                left_col += line
            else:
                right_col += line

        embed.add_field(name="Role", value=left_col or "\u200b", inline=True)
        embed.add_field(name="Price", value=right_col or "\u200b", inline=True)

        return embed

    # Send the initial message and add reactions
    message = await ctx.send(embed=get_embed(current_page))
    for emoji in ["⬅️", "➡️"]:
        await message.add_reaction(emoji)

    def check(reaction, user):
        return (
            user == ctx.author and 
            str(reaction.emoji) in ["⬅️", "➡️"] and 
            reaction.message.id == message.id
        )

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=120.0, check=check)

            if str(reaction.emoji) == "⬅️" and current_page > 0:
                current_page -= 1
                await message.edit(embed=get_embed(current_page))
            elif str(reaction.emoji) == "➡️" and current_page < total_pages - 1:
                current_page += 1
                await message.edit(embed=get_embed(current_page))

            try:
                await message.remove_reaction(reaction, user)
            except discord.Forbidden:
                pass  # Bot can't remove reactions

        except asyncio.TimeoutError:
            break



# =======================
# COMMANDS – Currency / Buy Role
# =======================

@bot.command()
async def buy(ctx, *, role_name):
    """Purchase a role from the shop using VAbux (case-insensitive)."""
    role_name = role_name.strip().lower()

    # Find the role in the shop, case-insensitive
    matched_name = next((r for r in ROLE_SHOP if r.lower() == role_name), None)
    if not matched_name:
        return await ctx.send("❌ That role isn't in the shop.")

    role_price = ROLE_SHOP[matched_name]

    # Find the actual Role object in the server
    guild_role = discord.utils.get(ctx.guild.roles, name=matched_name)
    if guild_role is None:
        return await ctx.send("❌ That role doesn’t exist in this server.")

    if guild_role in ctx.author.roles:
        return await ctx.send("⚠️ You already have that role.")

    ensure_profile(ctx.author.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (ctx.author.id,))
    balance = c.fetchone()[0]

    if balance < role_price:
        conn.close()
        return await ctx.send(
            f"💸 You need **{role_price:,} VAbux** to buy that role. You only have **{balance:,}**."
        )

    # Deduct currency and apply role
    c.execute('UPDATE profiles SET currency = currency - ? WHERE user_id = ?', (role_price, ctx.author.id))
    conn.commit()
    conn.close()

    try:
        await ctx.author.add_roles(guild_role)
        await ctx.send(f"🛍️ You bought the **{matched_name}** role for **{role_price:,} VAbux**!")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to give you that role.")










# =======================
# COMMANDS – Utility / Avatar
# =======================

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    """Displays the full-size avatar of the specified user (defaults to yourself)."""
    member = member or ctx.author

    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url

    embed = discord.Embed(
        title=f"{member.display_name}'s Avatar",
        color=discord.Color.purple()
    )
    embed.set_image(url=avatar_url)

    await ctx.send(embed=embed)




# =======================
# COMMANDS – Profile / Social
# =======================

@bot.command()
async def about(ctx, member: discord.Member = None):
    """Displays a user's profile info (defaults to yourself)."""
    member = member or ctx.author
    ensure_profile(member.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''
        SELECT about, status, crush, contentment, rep_count, marriages, ex_spouses, currency
        FROM profiles WHERE user_id = ?
    ''', (member.id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return await ctx.send("❌ Could not find a profile for that user.")

    about, status, crush, contentment, reps, marriages, exes, currency = row

    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url

    embed = discord.Embed(
        title=f"{member.display_name}'s Profile",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=avatar_url)       # Small avatar
    embed.set_image(url=avatar_url)           # Large banner avatar

    embed.add_field(name="About", value=about or "No bio set.", inline=False)
    embed.add_field(name="Status", value=status or "No status.")
    embed.add_field(name="Crush", value=crush or "None")
    embed.add_field(name="Contentment", value=contentment)
    embed.add_field(name="Reps", value=reps)
    embed.add_field(name="Marriages", value=marriages)
    embed.add_field(name="Ex-Spouses", value=exes or "None")
    embed.add_field(name="Currency", value=f"{currency:,} VAbux")

    await ctx.send(embed=embed)



# =======================
# COMMANDS – Profile / Edit
# =======================

@bot.command(name="setabout")
async def set_about(ctx, *, text):
    """Sets your 'About Me' profile section."""
    if len(text) > 250:
        return await ctx.send("❌ Your bio is too long. Please keep it under 250 characters.")

    ensure_profile(ctx.author.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('UPDATE profiles SET about = ? WHERE user_id = ?', (text, ctx.author.id))
    conn.commit()
    conn.close()

    await ctx.send("✅ Your profile has been updated.")

# =======================
# COMMANDS – Social / Rep System
# =======================
@bot.command()
async def rep(ctx, member: discord.Member):
    """Gives someone a reputation point (10-minute cooldown). Extra reward for spouses."""
    if member == ctx.author:
        return await ctx.send("❌ You can't rep yourself.")

    ensure_profile(ctx.author.id)
    ensure_profile(member.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    # Check last rep timestamp
    c.execute('SELECT last_rep FROM profiles WHERE user_id = ?', (ctx.author.id,))
    last = c.fetchone()[0]
    now = datetime.now()

    if last:
        try:
            last_time = datetime.strptime(last, '%Y-%m-%d %H:%M:%S')
            if now - last_time < timedelta(minutes=10):
                wait = timedelta(minutes=10) - (now - last_time)
                minutes, seconds = divmod(wait.seconds, 60)
                await ctx.send(f"⏳ You need to wait **{minutes}m {seconds}s** before repping again.")
                conn.close()
                return
        except ValueError:
            pass  # fallback if timestamp was invalid

    # ✅ Give rep and set cooldown
    c.execute('UPDATE profiles SET rep_count = rep_count + 1 WHERE user_id = ?', (member.id,))
    c.execute('UPDATE profiles SET last_rep = ? WHERE user_id = ?', (now.strftime('%Y-%m-%d %H:%M:%S'), ctx.author.id))

    # ✅ Check for spouse bonus
    c.execute('''
        SELECT * FROM marriages
        WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
    ''', (ctx.author.id, member.id, member.id, ctx.author.id))
    
    if c.fetchone():
        c.execute('UPDATE profiles SET contentment = contentment + 10 WHERE user_id = ?', (member.id,))
        msg = f"💖 You repped your spouse {member.mention}! (+10 Contentment)"
    else:
        msg = f"👍 You repped {member.mention}!"

    conn.commit()
    conn.close()
    await ctx.send(msg)


# =======================
# COMMANDS – Social / Repcheck
# =======================


@bot.command(name="repcheck")
async def reps(ctx, member: discord.Member = None):
    """Shows how many reputation points a member has."""
    member = member or ctx.author
    ensure_profile(member.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT rep_count FROM profiles WHERE user_id = ?', (member.id,))
    row = c.fetchone()
    conn.close()

    reps = row[0] if row else 0
    await ctx.send(f"📊 **{member.display_name}** has **{reps}** rep point{'s' if reps != 1 else ''}.")

# =======================
# COMMANDS – Social / Rep Leaderboard
# =======================

@bot.command()
async def replb(ctx):
    """Shows the top 10 users with the most rep."""
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT user_id, rep_count FROM profiles ORDER BY rep_count DESC LIMIT 10')
    top = c.fetchall()
    conn.close()

    embed = discord.Embed(title="🏆 Rep Leaderboard", color=discord.Color.gold())

    for i, (uid, count) in enumerate(top, 1):
        try:
            user = await bot.fetch_user(uid)
            name = user.name
        except:
            name = f"User ID {uid}"

        embed.add_field(
            name=f"{i}. {name}",
            value=f"{count:,} rep{'s' if count != 1 else ''}",
            inline=False
        )

    await ctx.send(embed=embed)

# =======================
# COMMANDS – Social / Kek Leaderboard
# =======================

@bot.command()
async def keklb(ctx):
    """Shows the top 10 users with the most kekw reactions received."""
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT user_id, kek_count FROM profiles ORDER BY kek_count DESC LIMIT 10')
    top = c.fetchall()
    conn.close()

    embed = discord.Embed(title="😂 Kek Leaderboard", color=discord.Color.green())

    for i, (uid, count) in enumerate(top, 1):
        try:
            user = await bot.fetch_user(uid)
            name = user.name
        except:
            name = f"User ID {uid}"

        embed.add_field(
            name=f"{i}. {name}",
            value=f"{count:,} kek{'s' if count != 1 else ''}",
            inline=False
        )

    await ctx.send(embed=embed)


# =======================
# COMMANDS – Social / Kekcheck Leaderboard
# =======================
@bot.command(name="kekcheck")
async def keks(ctx, member: discord.Member = None):
    """Shows how many kekw reactions a user has received."""
    member = member or ctx.author

    ensure_profile(member.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT kek_count FROM profiles WHERE user_id = ?', (member.id,))
    row = c.fetchone()
    conn.close()

    count = row[0] if row else 0

    await ctx.send(f"😂 **{member.display_name}** has received **{count:,}** kek{'s' if count != 1 else ''}.")


# =======================
# COMMANDS – Social / Level Leaderboard
# =======================
@bot.command()
async def levellb(ctx):
    """Shows the top 10 users by level and XP, and your own rank if not in top 10."""
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT user_id, level, xp FROM profiles ORDER BY level DESC, xp DESC')
    all_users = c.fetchall()
    conn.close()

    # Top 10 only
    top = all_users[:10]
    user_id = ctx.author.id

    embed = discord.Embed(
        title="🏆 Level Leaderboard",
        color=discord.Color.gold()
    )

    # Add top 10 users
    for i, (uid, level, xp) in enumerate(top, 1):
        user = bot.get_user(uid) or await bot.fetch_user(uid)
        name = user.display_name if user else f"User ID {uid}"
        embed.add_field(
            name=f"{i}. {name}",
            value=f"Level {level} | {xp:,} XP",
            inline=False
        )

    # Check if author is in the list already
    if user_id not in [uid for uid, _, _ in top]:
        for i, (uid, level, xp) in enumerate(all_users, 1):
            if uid == user_id:
                user = ctx.author
                embed.add_field(
                    name=f"🔹 Your Rank: {i}. {user.display_name}",
                    value=f"Level {level} | {xp:,} XP",
                    inline=False
                )
                break

    await ctx.send(embed=embed)

# =======================
# COMMANDS – Social / Level Check
# =======================
@bot.command()
async def level(ctx, member: discord.Member = None):
    """Displays your current level and XP progress."""
    member = member or ctx.author
    ensure_profile(member.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT xp, level FROM profiles WHERE user_id = ?', (member.id,))
    xp, level = c.fetchone()
    conn.close()

    next_level = int((level + 1) ** 2 * 10)
    progress = f"{xp:,} / {next_level:,} XP"

    embed = discord.Embed(
        title=f"📈 {member.display_name}'s Level",
        color=discord.Color.green()
    )
    embed.add_field(name="Level", value=f"{level}", inline=True)
    embed.add_field(name="XP", value=progress, inline=True)

    await ctx.send(embed=embed)



# =======================
# COMMANDS – Social / Marriage Proposal
# =======================
@bot.command()
async def marry(ctx, partner: discord.Member):
    """Propose marriage to another user (costs 200,000 VAbux)."""
    if partner == ctx.author:
        return await ctx.send("❌ You can't marry yourself.")

    ensure_profile(ctx.author.id)
    ensure_profile(partner.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

# Prevent duplicate marriages with the same person
    c.execute('''SELECT 1 FROM marriages WHERE 
                (user1_id = ? AND user2_id = ?) OR 
                (user1_id = ? AND user2_id = ?)''',
            (ctx.author.id, partner.id, partner.id, ctx.author.id))
    if c.fetchone():
        conn.close()
        return await ctx.send("💍 You're already married to that person!")

    # Currency check
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (ctx.author.id,))
    currency = c.fetchone()[0]
    if currency < 200_000:
        conn.close()
        return await ctx.send("💸 You need **200,000 VAbux** to propose marriage.")

    # Ask for acceptance
    await ctx.send(f"💍 {partner.mention}, do you accept the proposal from {ctx.author.mention}? (yes/no)")

    def check(m):
        return m.author == partner and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

    try:
        msg = await bot.wait_for("message", timeout=30.0, check=check)
        if msg.content.lower() == "no":
            conn.close()
            return await ctx.send("❌ Marriage proposal declined.")
    except asyncio.TimeoutError:
        conn.close()
        return await ctx.send("⏳ Marriage proposal timed out.")

    # Record marriage
    c.execute('INSERT INTO marriages (user1_id, user2_id) VALUES (?, ?)', (ctx.author.id, partner.id))
    c.execute('UPDATE profiles SET status = "Married", currency = currency - 200000, marriages = marriages + 1 WHERE user_id = ?', (ctx.author.id,))
    c.execute('UPDATE profiles SET status = "Married", marriages = marriages + 1 WHERE user_id = ?', (partner.id,))
    # Tied the Knot achievement
    c.execute("INSERT OR IGNORE INTO achievements (user_id, name, unlocked) VALUES (?, 'Tied the Knot', 1)", (ctx.author.id,))
    c.execute("INSERT OR IGNORE INTO achievements (user_id, name, unlocked) VALUES (?, 'Tied the Knot', 1)", (partner.id,))

    # Polygamist achievement
    c.execute('SELECT COUNT(*) FROM marriages WHERE user1_id = ? OR user2_id = ?', (ctx.author.id, ctx.author.id))
    author_marriages = c.fetchone()[0]
    if author_marriages > 1:
        c.execute("INSERT OR IGNORE INTO achievements (user_id, name, unlocked) VALUES (?, 'Polygamist', 1)", (ctx.author.id,))

    c.execute('SELECT COUNT(*) FROM marriages WHERE user1_id = ? OR user2_id = ?', (partner.id, partner.id))
    partner_marriages = c.fetchone()[0]
    if partner_marriages > 1:
        c.execute("INSERT OR IGNORE INTO achievements (user_id, name, unlocked) VALUES (?, 'Polygamist', 1)", (partner.id,))

    conn.commit()
    conn.close()

    await ctx.send(f"💒 {ctx.author.mention} and {partner.mention} are now **married**!")






# =======================
# COMMANDS – Social / Divorce
# =======================
@bot.command()
async def divorce(ctx, partner: discord.Member):
    """Divorces your partner. May cost 100,000 VAbux if contested."""
    if partner == ctx.author:
        return await ctx.send("❌ You can't divorce yourself.")

    ensure_profile(ctx.author.id)
    ensure_profile(partner.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    # Confirm marriage exists
    c.execute('''SELECT 1 FROM marriages 
                 WHERE (user1_id = ? AND user2_id = ?) 
                    OR (user1_id = ? AND user2_id = ?)''',
              (ctx.author.id, partner.id, partner.id, ctx.author.id))
    if not c.fetchone():
        conn.close()
        return await ctx.send("💔 You're not married to that person.")

    await ctx.send(f"💔 {partner.mention}, do you agree to divorce {ctx.author.mention}? (yes/no)")

    def check(m):
        return m.author == partner and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

    try:
        msg = await bot.wait_for('message', timeout=30.0, check=check)
        if msg.content.lower() == "no":
            # Attempt forced divorce
            c.execute('SELECT currency FROM profiles WHERE user_id = ?', (ctx.author.id,))
            currency = c.fetchone()[0]
            if currency < 100_000:
                conn.close()
                return await ctx.send("💸 Divorce refused and you don’t have **100,000 VAbux** to force it.")
            # Forced divorce payment
            c.execute('UPDATE profiles SET currency = currency - 100000 WHERE user_id = ?', (ctx.author.id,))
            c.execute('UPDATE profiles SET currency = currency + 100000 WHERE user_id = ?', (partner.id,))
            await ctx.send(f"💰 {ctx.author.mention} paid **100,000 VAbux** to force the divorce.")
    except asyncio.TimeoutError:
        conn.close()
        return await ctx.send("⏳ Divorce request timed out.")

    # Process divorce
    c.execute('DELETE FROM marriages WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)',
              (ctx.author.id, partner.id, partner.id, ctx.author.id))

    for user_id, ex_id in [(ctx.author.id, partner.id), (partner.id, ctx.author.id)]:
        c.execute('SELECT ex_spouses FROM profiles WHERE user_id = ?', (user_id,))
        current_exes = c.fetchone()[0] or ""
        ex_list = set(current_exes.split(', ')) if current_exes else set()
        ex_list.add(str(ex_id))
        updated_exes = ', '.join(sorted(ex_list))
        c.execute('UPDATE profiles SET status = "Divorced", ex_spouses = ? WHERE user_id = ?', (updated_exes, user_id))

    conn.commit()
    conn.close()

    await ctx.send(f"💔 {ctx.author.mention} and {partner.mention} are now **divorced**.")




# =======================
# COMMANDS – Social / Spouse Check
# =======================

@bot.command()
async def spouses(ctx, member: discord.Member = None):
    """Shows who a user is currently married to."""
    member = member or ctx.author

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    # Find all users they're married to
    c.execute('''
        SELECT user1_id, user2_id FROM marriages
        WHERE user1_id = ? OR user2_id = ?
    ''', (member.id, member.id))
    marriages = c.fetchall()
    conn.close()

    spouses = set()
    for u1, u2 in marriages:
        spouse_id = u2 if u1 == member.id else u1
        spouses.add(spouse_id)

    if not spouses:
        return await ctx.send(f"💔 **{member.display_name}** isn't married to anyone.")

    names = []
    for spouse_id in spouses:
        try:
            user = await bot.fetch_user(spouse_id)
            names.append(user.mention)
        except:
            names.append(f"User ID {spouse_id}")

    spouse_list = ', '.join(names)
    await ctx.send(f"💍 **{member.display_name}** is married to: {spouse_list}")

# =======================
# COMMANDS – Casino / Blackjack
# =======================
@bot.command()
async def bj(ctx, amount: int):
    if ctx.channel.id != CHANNEL_IDS['CASINO']:
        return await ctx.send("This command must be used in the #casino channel.")
    if amount <= 0:
        return await ctx.send("Bet must be positive.")

    ensure_profile(ctx.author.id)

    if ctx.author.id in active_games:
        return await ctx.send("You're already in a game!")

    # Check balance
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (ctx.author.id,))
    balance = c.fetchone()[0]
    if balance < amount:
        return await ctx.send("You don't have enough currency.")
    c.execute('UPDATE profiles SET currency = currency - ? WHERE user_id = ?', (amount, ctx.author.id))
    # Big Winner achievement

    conn.commit()
    conn.close()

    # Start game
    game = BlackjackGame(ctx.author.id, amount)
    active_games[ctx.author.id] = game
    game.player_hand = [game.deck.pop(), game.deck.pop()]
    game.dealer_hand = [game.deck.pop(), game.deck.pop()]

    async def update_embed(result=None, winnings=None, final=False):
        embed = discord.Embed(
            title="🎰 The Market Casino | Blackjack",
            color=discord.Color.green() if result == "Winner!" else discord.Color.red() if result else discord.Color.blurple()
        )
        embed.add_field(
            name=f"{ctx.author.display_name}'s Hand",
            value=f"{game.format_hand(game.player_hand)}\nScore: {game.calculate_hand(game.player_hand)}",
            inline=True
        )
        embed.add_field(
            name="Dealer's Hand",
            value=(
                f"{game.format_hand(game.dealer_hand)}\nScore: {game.calculate_hand(game.dealer_hand)}"
                if final else
                f"{game.dealer_hand[0][:-1]}{SUITS[game.dealer_hand[0][-1]]}, ?"
            ),
            inline=True
        )
        if result:
            embed.add_field(name="Outcome", value=result, inline=False)
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)
            if winnings > 0:
                embed.add_field(name="🏆", value=f"Congratulations, you just won {winnings:,} VABux!", inline=False)
            else:
                embed.add_field(name="💀", value=f"Sorry, you didn't win anything.", inline=False)
            conn = sqlite3.connect('bot.db')
            c = conn.cursor()
            c.execute('SELECT currency FROM profiles WHERE user_id = ?', (ctx.author.id,))
            new_balance = c.fetchone()[0]
            conn.close()
            embed.add_field(name="Remaining Balance", value=f"{new_balance:,} VABux", inline=False)
        else:
            embed.add_field(name="Commands", value="Type: `hit`, `stay`, or `double`", inline=False)

        if not game.msg:
            game.msg = await ctx.send(embed=embed)
        else:
            await game.msg.edit(embed=embed)

    await update_embed()

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['hit', 'stay', 'double']

    while not game.game_over:
        try:
            msg = await bot.wait_for('message', timeout=30, check=check)
        except asyncio.TimeoutError:
            await ctx.send("⏳ Game timed out.")
            del active_games[ctx.author.id]
            return

        action = msg.content.lower()

        if action == 'hit':
            game.player_hand.append(game.deck.pop())
            if game.calculate_hand(game.player_hand) > 21:
                game.game_over = True
                await update_embed("Bust! You lose.", winnings=0, final=True)
                del active_games[ctx.author.id]
                return
            await update_embed()

        elif action == 'stay':
            while game.calculate_hand(game.dealer_hand) < 17:
                game.dealer_hand.append(game.deck.pop())

            p = game.calculate_hand(game.player_hand)
            d = game.calculate_hand(game.dealer_hand)
            game.game_over = True

            if d > 21 or p > d:
                winnings = game.bet * 2
                result = "Winner!"
            elif p < d:
                winnings = 0
                result = "House Wins!"
            else:
                winnings = game.bet
                result = "Pushed"

            # update balance
            conn = sqlite3.connect('bot.db')
            c = conn.cursor()
            c.execute('UPDATE profiles SET currency = currency + ? WHERE user_id = ?', (winnings, ctx.author.id))
            # Big Winner achievement
            if winnings > 10000:
                c.execute("INSERT OR IGNORE INTO achievements (user_id, name, unlocked) VALUES (?, 'Big Winner', 1)", (ctx.author.id,))

            conn.commit()
            conn.close()

            await update_embed(result, winnings, final=True)
            del active_games[ctx.author.id]
            return

        elif action == 'double':
            if len(game.player_hand) != 2:
                await ctx.send("You can only double on your first turn.")
                continue

            conn = sqlite3.connect('bot.db')
            c = conn.cursor()
            c.execute('SELECT currency FROM profiles WHERE user_id = ?', (ctx.author.id,))
            extra = c.fetchone()[0]
            if extra < game.bet:
                await ctx.send("You don’t have enough currency to double.")
                conn.close()
                continue

            c.execute('UPDATE profiles SET currency = currency - ? WHERE user_id = ?', (game.bet, ctx.author.id))

            conn.commit()
            conn.close()

            game.bet *= 2
            game.player_hand.append(game.deck.pop())

            if game.calculate_hand(game.player_hand) > 21:
                game.game_over = True
                await update_embed("Bust after double!", winnings=0, final=True)
                del active_games[ctx.author.id]
                return

            action = 'stay'


# =======================
# COMMANDS – Casino / Poker
# =======================


@bot.command()
async def poker(ctx, opponent: discord.Member):
    if ctx.channel.id != CHANNEL_IDS['CASINO']:
        return await ctx.send("🎰 You can only play poker in the **#casino** channel!")

    if opponent.bot:
        return await ctx.send("🤖 You can't challenge bots.")
    if opponent == ctx.author:
        return await ctx.send("🃏 You can't challenge yourself.")

    await ctx.send(f"{opponent.mention}, do you accept the poker challenge from {ctx.author.mention}? React with ✅ within 30 seconds.")

    try:
        def check(reaction, user):
            return user == opponent and str(reaction.emoji) == "✅" and reaction.message.channel == ctx.channel

        msg = await ctx.send("Waiting for response...")
        await msg.add_reaction("✅")
        await bot.wait_for("reaction_add", timeout=30.0, check=check)

    except asyncio.TimeoutError:
        return await ctx.send("⏳ Challenge timed out.")

    # Check balances BEFORE starting the game
    entry_fee = 5000
    ensure_profile(ctx.author.id)
    ensure_profile(opponent.id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (ctx.author.id,))
    p1_bal = c.fetchone()[0]
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (opponent.id,))
    p2_bal = c.fetchone()[0]

    if p1_bal < entry_fee or p2_bal < entry_fee:
        conn.close()
        return await ctx.send("❌ Both players must have at least **5,000 VABux** to play poker.")

    # Deduct entry fee
    c.execute('UPDATE profiles SET currency = currency - ? WHERE user_id = ?', (entry_fee, ctx.author.id))
    c.execute('UPDATE profiles SET currency = currency - ? WHERE user_id = ?', (entry_fee, opponent.id))
    # Big Winner achievement

    conn.commit()
    conn.close()

    await ctx.send(f"🎲 {ctx.author.mention} vs {opponent.mention} — Let the game begin!")

    # Deck generation
    suits = {"♠": "♠️", "♥": "♥️", "♦": "♦️", "♣": "♣️"}
    values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    deck = [f"{v}{s}" for s in suits for v in values]
    random.shuffle(deck)

    player_hand = [deck.pop(), deck.pop()]
    opponent_hand = [deck.pop(), deck.pop()]
    community_cards = [deck.pop() for _ in range(5)]

    def emoji_hand(hand):
        return ' '.join([f"{card[:-1]}{suits[card[-1]]}" for card in hand])

    table_msg = await ctx.send("🃏 Dealing cards...")

    await asyncio.sleep(1)
    await table_msg.edit(content=f"**{ctx.author.display_name}** was dealt: `?? ??`")
    await asyncio.sleep(1)
    await table_msg.edit(content=f"**{ctx.author.display_name}** was dealt: `{emoji_hand(player_hand)}`")

    await asyncio.sleep(1)
    await table_msg.edit(content=f"**{ctx.author.display_name}**: `{emoji_hand(player_hand)}`\n**{opponent.display_name}** was dealt: `?? ??`")
    await asyncio.sleep(1)
    await table_msg.edit(content=f"**{ctx.author.display_name}**: `{emoji_hand(player_hand)}`\n**{opponent.display_name}**: `{emoji_hand(opponent_hand)}`")

    await asyncio.sleep(1.5)
    await table_msg.edit(content=f"**Flop:** `?? ?? ??`")
    await asyncio.sleep(1)
    await table_msg.edit(content=f"**Flop:** `{emoji_hand(community_cards[:3])}`")
    await asyncio.sleep(1)
    await table_msg.edit(content=f"**Flop:** `{emoji_hand(community_cards[:3])}`\n**Turn:** `??`")
    await asyncio.sleep(1)
    await table_msg.edit(content=f"**Flop:** `{emoji_hand(community_cards[:3])}`\n**Turn:** `{emoji_hand([community_cards[3]])}`")
    await asyncio.sleep(1)
    await table_msg.edit(content=f"**Flop:** `{emoji_hand(community_cards[:3])}`\n**Turn:** `{emoji_hand([community_cards[3]])}`\n**River:** `??`")
    await asyncio.sleep(1)
    await table_msg.edit(content=f"**Flop:** `{emoji_hand(community_cards[:3])}`\n**Turn:** `{emoji_hand([community_cards[3]])}`\n**River:** `{emoji_hand([community_cards[4]])}`")

    # Evaluate hands
    p_score, p_vals, p_name = evaluate_hand_with_name(player_hand, community_cards)
    o_score, o_vals, o_name = evaluate_hand_with_name(opponent_hand, community_cards)

    pot = entry_fee * 2
    result = ""

    if p_score > o_score or (p_score == o_score and p_vals > o_vals):
        winner = ctx.author
        result = f"🏆 **{ctx.author.display_name}** wins with a **{p_name}**!\n💰 Prize: **{pot:,} VABux**"
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute('UPDATE profiles SET currency = currency + ? WHERE user_id = ?', (pot, ctx.author.id))

        conn.commit()
        conn.close()
    elif o_score > p_score or (p_score == o_score and o_vals > p_vals):
        winner = opponent
        result = f"🏆 **{opponent.display_name}** wins with a **{o_name}**!\n💰 Prize: **{pot:,} VABux**"
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute('UPDATE profiles SET currency = currency + ? WHERE user_id = ?', (pot, opponent.id))

        conn.commit()
        conn.close()
    else:
        result = "🤝 It's a tie! Both players get their **5,000 VABux** back."
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute('UPDATE profiles SET currency = currency + ? WHERE user_id = ?', (entry_fee, ctx.author.id))
        c.execute('UPDATE profiles SET currency = currency + ? WHERE user_id = ?', (entry_fee, opponent.id))
        conn.commit()
        conn.close()

    await ctx.send(
        f"**Showdown!**\n"
        f"{ctx.author.mention}: `{emoji_hand(player_hand)}` — **{p_name}**\n"
        f"{opponent.mention}: `{emoji_hand(opponent_hand)}` — **{o_name}**\n\n"
        f"{result}"
    )



# =======================
# COMMANDS – Casino / Slots
# =======================
@bot.command()
async def slots(ctx, amount: int):
    """Play a slot machine. Triple diamonds win the jackpot!"""
    if ctx.channel.id != CHANNEL_IDS['CASINO']:
        return await ctx.send("🎰 You can only use this command in the **#casino** channel!")

    if amount <= 0:
        return await ctx.send("❌ Your bet must be a positive number.")

    # Cooldown check
    now = time.time()
    if now - slots_cooldowns[ctx.author.id] < 5:
        wait = round(5 - (now - slots_cooldowns[ctx.author.id]), 1)
        return await ctx.send(f"🕒 Slow down! Try again in {wait} seconds.")

    slots_cooldowns[ctx.author.id] = now

    user_id = ctx.author.id
    ensure_profile(user_id)

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (user_id,))
    balance = c.fetchone()[0]

    if balance < amount:
        conn.close()
        return await ctx.send("💸 You don't have enough VAbux to make that bet.")

    # Deduct bet
    c.execute('UPDATE profiles SET currency = currency - ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

    # Weighted symbols based on bet amount (maxes out at 1,000,000)
    def get_weighted_symbols(bet):
        base = {
            "🍒": 10,
            "💎": 1,  # base diamond chance
            "🍀": 10,
            "💀": 8,
            "🍌": 10,
            "🔥": 10,
        }
        diamond_bonus = min(100, int(bet / 10000))  # Up to 100 weight for 1M
        base["💎"] += diamond_bonus
        symbols_weighted = []
        for sym, weight in base.items():
            symbols_weighted.extend([sym] * weight)
        return symbols_weighted

    symbols = get_weighted_symbols(amount)
    rows = [[random.choice(symbols) for _ in range(3)] for _ in range(3)]

    # Initial suspense
    display = await ctx.send("🎰 Spinning the slots...")

    for i in range(3):
        line1 = " | ".join(rows[0][:i+1] + ["❔"] * (2 - i))
        line2 = " | ".join(rows[1][:i+1] + ["❔"] * (2 - i))
        line3 = " | ".join(rows[2][:i+1] + ["❔"] * (2 - i))
        content = f"""
🎰 **SLOTS MACHINE** 🎰

`| {line1} |`
`| {line2} |` ←
`| {line3} |`
        """
        await display.edit(content=content.strip())
        await asyncio.sleep(0.6)

    final_row = rows[1]

    def calc_win(row):
        if "💀" in row:
            return 0, "💀 You hit a cursed skull! You lose everything."
        elif row.count(row[0]) == 3:
            return amount * 3, "🎉 JACKPOT! Triple match!"
        elif len(set(row)) == 2:
            return amount * 2, "✨ Two matched!"
        else:
            return 0, "😢 No matches. House wins."

    winnings, result_msg = calc_win(final_row)

    # Jackpot logic if triple diamonds
    if final_row == ["💎", "💎", "💎"]:
        if jackpot["amount"] > 0:
            winnings = jackpot["amount"]
            jackpot["amount"] = 0
            save_jackpot()
            result_msg = f"💎💎💎 **JACKPOT!!!** 💎💎💎\n\n**{ctx.author.mention}** just hit the **TRIPLE DIAMONDS** and won the entire pot of **{winnings:,} VAbux**! 🎉🎰💰"

            # Broadcast to casino
            announcement = discord.Embed(
                title="🎉 JACKPOT WINNER 🎉",
                description=(
                    f"💎💎💎 **TRIPLE DIAMONDS** 💎💎💎\n\n"
                    f"**{ctx.author.display_name}** just won the **jackpot** worth **{winnings:,} VAbux** in the slot machine!\n"
                    f"Try your luck in the #casino now!"
                ),
                color=discord.Color.gold()
            )
            casino_channel = bot.get_channel(CHANNEL_IDS['CASINO'])
            if casino_channel:
                await casino_channel.send(embed=announcement)
        else:
            winnings = amount * 5
            result_msg = "💎💎💎 You hit TRIPLE DIAMONDS — but the pot was empty. You still win **5× your bet**!"

    elif winnings == 0:
        jackpot["amount"] += amount
        save_jackpot()

    # Update balance
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('UPDATE profiles SET currency = currency + ? WHERE user_id = ?', (winnings, user_id))
    if winnings > 10000:
        c.execute("INSERT OR IGNORE INTO achievements (user_id, name, unlocked) VALUES (?, 'Big Winner', 1)", (user_id,))
    conn.commit()
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (user_id,))
    new_balance = c.fetchone()[0]
    conn.close()

    delta = winnings - amount
    result = f"**You {'won' if delta > 0 else 'lost'} {abs(delta):,} VAbux**"
    jackpot_status = f"🎯 Current Jackpot: **{jackpot['amount']:,} VAbux**"

    final_display = f"""
🎰 **SLOTS MACHINE** 🎰

`| {' | '.join(rows[0])} |`
`| {' | '.join(rows[1])} |` ←
`| {' | '.join(rows[2])} |`

{result_msg}
{result}
**New Balance:** {new_balance:,} VAbux
{jackpot_status}
    """
    await display.edit(content=final_display.strip())



# =======================
# COMMANDS – Casino / All In
# =======================
@bot.command()
async def allin(ctx):
    """Gamble your entire balance for a shot at riches — or ruin."""
    if ctx.channel.id != CHANNEL_IDS['CASINO']:
        return await ctx.send("🎰 You can only use this command in the **#casino** channel!")

    user_id = ctx.author.id
    now = time.time()

    if now - allin_cooldowns[user_id] < 30:
        remaining = int(30 - (now - allin_cooldowns[user_id]))
        return await ctx.send(f"🕒 Slow down, gambler. Try again in {remaining} seconds.")

    allin_cooldowns[user_id] = now

    ensure_profile(user_id)
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (user_id,))
    balance = c.fetchone()[0]

    if balance <= 0:
        conn.close()
        return await ctx.send("💸 You have no VAbux to bet!")

    # Deduct entire balance
    c.execute('UPDATE profiles SET currency = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

    # Weighted symbol generation based on balance
    def get_weighted_symbols(bet):
        base = {
            "🍒": 10,
            "💎": 1,  # base chance
            "🍀": 10,
            "💀": 10,
            "🍌": 10,
            "🔥": 10,
        }
        bonus = min(100, int(bet / 10000))  # +1 weight per 10k up to 100
        base["💎"] += bonus
        weighted = []
        for sym, weight in base.items():
            weighted.extend([sym] * weight)
        return weighted

    symbols = get_weighted_symbols(balance)
    rows = [[random.choice(symbols) for _ in range(3)] for _ in range(3)]

    display = await ctx.send("🎰 Spinning the slots...")
    for i in range(3):
        line1 = " | ".join(rows[0][:i+1] + ["❔"] * (2 - i))
        line2 = " | ".join(rows[1][:i+1] + ["❔"] * (2 - i))
        line3 = " | ".join(rows[2][:i+1] + ["❔"] * (2 - i))
        content = f"""
🎰 **ALL IN SLOT MACHINE** 🎰

`| {line1} |`\n`| {line2} |`\n`| {line3} |`
        """
        await display.edit(content=content.strip())
        await asyncio.sleep(0.6)

    final_slots = rows[1]
    winnings = 0
    result_msg = ""
    jackpot_message = ""

    if final_slots == ["💎", "💎", "💎"]:
        if jackpot["amount"] > 0:
            winnings = jackpot["amount"]
            result_msg = f"💎💎💎 **JACKPOT!!!** 💎💎💎\n\n**{ctx.author.mention}** just hit **TRIPLE DIAMONDS** and won **{winnings:,} VAbux**! 🎉🎰💰"
            jackpot["amount"] = 0
            save_jackpot()

            # Announce to casino
            jackpot_embed = discord.Embed(
                title="🎉 JACKPOT WINNER 🎉",
                description=(
                    f"💎💎💎 **TRIPLE DIAMONDS** 💎💎💎\n\n"
                    f"**{ctx.author.display_name}** won the **ALL IN jackpot** worth **{winnings:,} VAbux**!\n"
                    f"Feeling lucky? Try `=allin` or `=slots` next!"
                ),
                color=discord.Color.gold()
            )
            casino_channel = bot.get_channel(CHANNEL_IDS['CASINO'])
            if casino_channel:
                await casino_channel.send(embed=jackpot_embed)
        else:
            winnings = balance * 5
            result_msg = "💎💎💎 You hit TRIPLE DIAMONDS — but the pot was empty. You still win **5× your bet**!"
    elif "💀" in final_slots:
        winnings = 0
        result_msg = "💀 You hit a cursed skull! You lose everything."
        jackpot["amount"] += balance
        save_jackpot()
        jackpot_message = f"\n💰 The entire bet was added to the **jackpot**! (+{balance:,} VAbux)"
    elif final_slots.count(final_slots[0]) == 3:
        winnings = balance * 3
        result_msg = "🎉 JACKPOT! Triple match!"
    elif len(set(final_slots)) == 2:
        winnings = balance * 2
        result_msg = "✨ Two matched!"
    else:
        winnings = 0
        result_msg = "😢 No matches. The house wins."
        jackpot["amount"] += balance
        save_jackpot()
        jackpot_message = f"\n💰 The entire bet was added to the **jackpot**! (+{balance:,} VAbux)"

    # Update balance
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('UPDATE profiles SET currency = currency + ? WHERE user_id = ?', (winnings, user_id))
    if winnings > 10000:
        c.execute("INSERT OR IGNORE INTO achievements (user_id, name, unlocked) VALUES (?, 'Big Winner', 1)", (user_id,))
    conn.commit()
    c.execute('SELECT currency FROM profiles WHERE user_id = ?', (user_id,))
    new_balance = c.fetchone()[0]
    conn.close()

    delta = winnings - balance
    result = f"**You {'won' if delta > 0 else 'lost'} {abs(delta):,} VAbux**"

    final = f"""
🎰 **ALL IN SLOT MACHINE** 🎰

`| {' | '.join(rows[0])} |`\n`| {' | '.join(rows[1])} |`\n`| {' | '.join(rows[2])} |`

{result_msg}
{result}
**New Balance:** {new_balance:,} VAbux{jackpot_message}
    """
    await display.edit(content=final.strip())

# =======================
# COMMANDS – Casino / Horserace
# =======================
@bot.command()
async def horserace(ctx, base_pot: int = 1000):
    global carry_over_pot

    if ctx.channel.id != CHANNEL_IDS['CASINO']:
        return await ctx.send("🎰 You can only start a race in the **#casino** channel.")
    if base_pot <= 0:
        return await ctx.send("❌ Pot must be a positive number.")

    join_msg = await ctx.send(
    f"🏇 **Horse Race Starting!** React with 🐎 to join the race! You have 30 seconds!\n"
    f"Click 🐎 to join the race!\n\n💰 **Carry-over Pot:** {carry_over_pot:,} VABux"
)
    await join_msg.add_reaction("🐎")

    def join_check(reaction, user):
        return str(reaction.emoji) == "🐎" and reaction.message.id == join_msg.id and not user.bot

    participants = set()

    try:
        while True:
            reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=join_check)
            participants.add(user)
    except asyncio.TimeoutError:
        pass

    if len(participants) < 2:
        return await ctx.send("❌ Not enough participants. At least 2 players are required.")

    # Ask each player how much they're betting
    await ctx.send(f"{', '.join([p.mention for p in participants])}, please type how much you're betting!")

    bets = {}
    def bet_check(m):
        return m.author in participants and m.channel == ctx.channel and m.content.isdigit()

    try:
        while len(bets) < len(participants):
            bet_msg = await bot.wait_for("message", timeout=30.0, check=bet_check)
            amount = int(bet_msg.content)
            if amount <= 0:
                await ctx.send(f"{bet_msg.author.mention}, invalid bet.")
                continue

            ensure_profile(bet_msg.author.id)
            conn = sqlite3.connect('bot.db')
            c = conn.cursor()
            c.execute('SELECT currency FROM profiles WHERE user_id = ?', (bet_msg.author.id,))
            bal = c.fetchone()[0]
            conn.close()

            if bal < amount:
                await ctx.send(f"{bet_msg.author.mention}, you don't have enough VABux.")
                continue

            bets[bet_msg.author] = amount
    except asyncio.TimeoutError:
        return await ctx.send("⏳ Bet entry timed out.")

    # Deduct the money
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    for user, amt in bets.items():
        c.execute('UPDATE profiles SET currency = currency - ? WHERE user_id = ?', (amt, user.id))

    conn.commit()
    conn.close()

    total_pot = sum(bets.values()) + base_pot
    total_pot += carry_over_pot
    carry_over_pot = 0

    await ctx.send(f"🏆 The total pot for this race is **{total_pot:,} VABux**.")

    # Generate horse names
    adjectives = ["Blazing", "Majestic", "Wild", "Crimson", "Silver", "Thunder", "Velvet", "Shadow", "Golden", "Stormy"]
    nouns = ["Whirl", "Runner", "Spirit", "Bolt", "Dream", "Streak", "Dash", "Gale", "Hoof", "Wind"]
    horse_pool = set()
    while len(horse_pool) < 5:
        horse_pool.add(f"{random.choice(adjectives)} {random.choice(nouns)}")
    horses = list(horse_pool)


    await ctx.send(f"Horses in this race are:\n" + "\n".join([f"- **{h}**" for h in horses]))
    await ctx.send("🐴 Players, **pick your horse** by typing its name exactly!")

    horse_choices = {}

    def horse_check(m):
        return m.author in participants and m.content in horses and m.author not in horse_choices

    try:
        while len(horse_choices) < len(participants):
            msg = await bot.wait_for("message", timeout=30.0, check=horse_check)
            horse_choices[msg.author] = msg.content
    except asyncio.TimeoutError:
        return await ctx.send("⏳ Horse selection timed out.")

    ...
    await ctx.send("🎬 Get ready...")

    # Countdown
    for i in ["1...", "2...", "3...", "And they're off!"]:
        await ctx.send(i)
        await asyncio.sleep(1)

    # Start race
    positions = {horse: 0 for horse in horses}
    finish_line = 20
    race_messages = []

    race_display = await ctx.send("🏁 Starting positions...")

    def render_race():
        return "\n".join(
            [f"{horse:<15}  " + "—" * pos + "🐎" + " " * (finish_line - pos) + "🏁" for horse, pos in positions.items()]
        )


    for _ in range(30):
        advancing = random.sample(horses, k=random.randint(1, len(horses)))
        for horse in advancing:
            positions[horse] += 1
            if positions[horse] >= finish_line:
                positions[horse] = finish_line

        await race_display.edit(content=f"```\n{render_race()}\n```")
        await asyncio.sleep(0.8)

        if any(pos == finish_line for pos in positions.values()):
            break

    # Determine winners
    furthest = max(positions.values())
    winning_horses = [horse for horse, pos in positions.items() if pos == furthest]

    winners = [user for user, horse in horse_choices.items() if horse in winning_horses]
    split = total_pot // len(winners) if winners else 0

    # Payout
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    for user in winners:
        c.execute('UPDATE profiles SET currency = currency + ? WHERE user_id = ?', (split, user.id))
    conn.commit()
    conn.close()

    winner_mentions = ', '.join([winner.mention for winner in winners]) if winners else "No one"
    winning_names = ', '.join(winning_horses)

    await ctx.send(f"🏁 Winning Horse(s): **{winning_names}**")
    if winners:
        await ctx.send(f"🏆 {winner_mentions} win **{split:,} VABux** each!")
    else:
        carry_over_pot += total_pot
        await ctx.send(
            f"💸 No one bet on the winning horse: **{winning_names}**.\n"
            f"The **{total_pot:,} VABux** pot rolls over to the next race!\n"
            f"🏦 New carry-over pot: **{carry_over_pot:,} VABux**"
        )

    
    

# =======================
# COMMANDS – Fun / Tarot Cards
# =======================
@bot.command()
async def tc(ctx):
    """Draws a random tarot card and reveals its meaning."""
    card = random.choice(list(tarot_cards.keys()))
    meaning = tarot_cards[card]

    display_name = f"🔮 {card}"
    meaning_text = f"*{meaning}*"
    image_path = f"tarot/{card}.jpg"

    embed = discord.Embed(
        title=display_name,
        description=meaning_text,
        color=discord.Color.dark_purple()
    )

    try:
        file = discord.File(image_path, filename="card.png")
        embed.set_image(url="attachment://card.png")
        await ctx.send(file=file, embed=embed)
    except FileNotFoundError:
        embed.set_footer(text="(No image available)")
        await ctx.send(embed=embed)


# =======================
# COMMANDS – Fun / Fortune
# =======================
from collections import defaultdict
from datetime import date

# Tracks each user's daily fortune pulls
daily_fortunes = defaultdict(lambda: {"date": None, "used": set()})

@bot.command()
async def fortune(ctx):
    """Draws a random fortune you haven’t received today."""
    if not fortunes:
        return await ctx.send("🔮 The spirits are silent...")

    user_id = ctx.author.id
    today = date.today().isoformat()
    record = daily_fortunes[user_id]

    # Reset daily record if it’s a new day
    if record["date"] != today:
        record["date"] = today
        record["used"] = set()

    # Get list of available (unseen) fortunes
    unused_fortunes = [f for f in fortunes if f not in record["used"]]

    if not unused_fortunes:
        return await ctx.send("🧘 You've received all your fortunes today. The spirits say 'rest.'")

    # Pick one the user hasn't seen today
    fortune = random.choice(unused_fortunes)
    record["used"].add(fortune)

    embed = discord.Embed(
        title="🔮 Your Fortune Awaits...",
        description=f"**{ctx.author.display_name}**, the spirits reveal:\n\n*{fortune}*",
        color=discord.Color.lighter_grey()
    )

    await ctx.send(embed=embed)








# =========================
# COMMANDS - Help Command
# =========================

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📖 Brainrot Bot Help",
        description="Here's a list of all the available commands, sorted by category.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="💸 Currency & Economy",
        value="`=work`, `=payday`, `=balance`, `=transfer`, `=shop`, `=buy`",
        inline=False
    )

    embed.add_field(
        name="🎮 Casino & Games",
        value="`=bj`, `=slots`, `=allin`, `=horserace`, `=dice`, `=poker`, `=tc`, `=fortune`",
        inline=False
    )

    embed.add_field(
        name="🗡️ Adventure & RPG",
        value="`=newchar`, `=adventure`, `=healme`, `=char`, `=respec`, `=tavern`, `=titles`",
        inline=False
    )

    embed.add_field(
        name="❤️ Social & Profile",
        value="`=about`, `=setabout`, `=rep`, `=repcheck`, `=replb`, `=kekcheck`, `=keklb`, `=level`, `=levellb`, `=marry`, `=divorce`, `=spouses`",
        inline=False
    )

    embed.add_field(
        name="🧠 Fun & Memes",
        value="`=penis`, `=iq`, `=simprate`, `=sanity`, `=ireally`, `=avatar`",
        inline=False
    )


    embed.set_footer(text="Use each command as shown. Some commands may have cooldowns or channel restrictions.")
    await ctx.send(embed=embed)


# =======================
# BRAINROT
# # =======================





# =======================
# BRAINROT
# # =======================
last_heal_times = {}

# =======================
# Database Setup
# =======================
def setup_database():
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Player Core
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        class TEXT,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        hp INTEGER DEFAULT 100,
        strength INTEGER DEFAULT 1,
        magic INTEGER DEFAULT 1,
        dexterity INTEGER DEFAULT 1,
        luck INTEGER DEFAULT 1,
        stat_points INTEGER DEFAULT 0,
        title TEXT DEFAULT 'Novice',
        special_used INTEGER DEFAULT 0
    )''')

    # Equipment
    c.execute('''CREATE TABLE IF NOT EXISTS equipment (
        user_id INTEGER PRIMARY KEY,
        head TEXT,
        chest TEXT,
        weapon TEXT
    )''')

    # Inventory
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_name TEXT,
        rarity TEXT,
        stat_bonus TEXT,
        quantity INTEGER DEFAULT 1,
        type TEXT,
        equipped INTEGER DEFAULT 0
    )''')

    # Achievements
    c.execute('''CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        description TEXT,
        earned_on TEXT,
        UNIQUE(user_id, name)
    )''')

    # Profiles (for VAbux)
    c.execute('''CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        currency INTEGER DEFAULT 0
    )''')

    # Tavern Flags
    c.execute('''CREATE TABLE IF NOT EXISTS tavern_flags (
        user_id INTEGER PRIMARY KEY
    )''')

    # Stats
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        duel_wins INTEGER DEFAULT 0,
        dice_wins INTEGER DEFAULT 0,
        deaths INTEGER DEFAULT 0
    )''')

    # Titles
    c.execute('''CREATE TABLE IF NOT EXISTS titles (
        user_id INTEGER,
        title TEXT,
        earned_on TEXT
    )''')

    # Heal Cooldowns
    c.execute('''CREATE TABLE IF NOT EXISTS heal_cooldowns (
        user_id INTEGER PRIMARY KEY,
        last_used INTEGER
    )''')

    conn.commit()
    conn.close()


@bot.event
async def on_ready():
    setup_database()
    print(f"✅ {bot.user} is online.")

# =======================
# Command: =newchar
# =======================
@bot.command()
async def newchar(ctx):
    user_id = ctx.author.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    c.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    if c.fetchone():
        await ctx.send("⚠️ You already have a character.")
        conn.close()
        return

    # Reaction wait
    class_msg = await ctx.send("🧙 Choose your class: ⚔️ Warrior | 🧪 Mage | 🗡️ Rogue")
    for emoji in ["⚔️", "🧪", "🗡️"]:
        await class_msg.add_reaction(emoji)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["⚔️", "🧪", "🗡️"] and reaction.message.id == class_msg.id

    try:
        reaction, _ = await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("⌛ You took too long to choose a class.")
        return

    emoji_to_class = {
        "⚔️": "Warrior",
        "🧪": "Mage",
        "🗡️": "Rogue"
    }
    chosen_class = emoji_to_class.get(str(reaction.emoji), "Warrior")

    # ✅ Safety re-check
    c.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    if c.fetchone():
        await ctx.send("⚠️ You already have a character.")
        conn.close()
        return

    try:
        c.execute('''INSERT INTO players (
            user_id, username, class, level, xp, hp,
            strength, magic, dexterity, luck, stat_points
        ) VALUES (?, ?, ?, 1, 0, 100, 1, 1, 1, 1, 0)''',
        (user_id, ctx.author.name, chosen_class))

        c.execute("INSERT INTO equipment (user_id) VALUES (?)", (user_id,))
        c.execute("INSERT OR IGNORE INTO profiles (user_id) VALUES (?)", (user_id,))
        conn.commit()
        await ctx.send(f"🆕 Character created! You are now a **{chosen_class}**. Use `=char` to view your stats.")

    except sqlite3.IntegrityError:
        await ctx.send("⚠️ You already have a character.")
    finally:
        conn.close()

# =======================
# Command: =char
# =======================
@bot.command()
async def char(ctx):
    user_id = ctx.author.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    c.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    row = c.fetchone()

    if not row:
        await ctx.send("❌ You don't have a character yet. Use `=newchar`.")
        conn.close()
        return

    (uid, uname, cls, lvl, xp, hp, str_, mag, dex, luk, pts, title, special_used) = row

    # Get gear
    c.execute("SELECT head, chest, weapon FROM equipment WHERE user_id = ?", (user_id,))
    eq = c.fetchone()
    head = eq[0] if eq and eq[0] else "None"
    chest = eq[1] if eq and eq[1] else "None"
    weapon = eq[2] if eq and eq[2] else "None"

    # Get VAbux
    c.execute("SELECT currency FROM profiles WHERE user_id = ?", (user_id,))
    profile = c.fetchone()
    vabux = profile[0] if profile else 0

    # Build embed
    display_name = f"{uname} – {title}" if title else uname
    embed = discord.Embed(title=f"📜 {display_name}'s Character Sheet", color=discord.Color.teal())
    embed.add_field(name="Class", value=cls, inline=True)
    embed.add_field(name="Level", value=lvl, inline=True)
    embed.add_field(name="XP", value=f"{xp}/{lvl * 500}", inline=True)
    embed.add_field(name="HP", value=hp, inline=True)
    embed.add_field(name="Gold", value=f"{vabux} VAbux", inline=True)
    embed.add_field(name="STR", value=str_, inline=True)
    embed.add_field(name="MAG", value=mag, inline=True)
    embed.add_field(name="DEX", value=dex, inline=True)
    embed.add_field(name="LUK", value=luk, inline=True)
    embed.add_field(name="Stat Points", value=pts, inline=True)
    embed.add_field(name="Weapon", value=weapon, inline=True)
    embed.add_field(name="Armor", value=chest, inline=True)
    embed.add_field(name="Helmet", value=head, inline=True)

    message = await ctx.send(embed=embed)

    if pts > 0:
        for emoji in ["💪", "🧠", "🩰", "🍀"]:
            await message.add_reaction(emoji)

    conn.close()


# =======================
# ADVENTURE STATE
# =======================
adventure_active = False
adventure_party = []
adventure_leader = None
adventure_difficulty = None
adventure_rooms = []
current_room_index = 0
adventure_cooldown = False
cooldown_timer = 120  # in seconds

# =======================
# DIFFICULTY SCALING
# =======================
def calculate_difficulty(total_level):
    if total_level >= 200:
        return "Hell"
    elif total_level >= 100:
        return "Nightmare"
    elif total_level >= 50:
        return "Hard"
    elif total_level >= 10:
        return "Normal"
    else:
        return "Easy"

# =======================
# ROOM GENERATOR
# =======================
def generate_rooms():
    types = ["Monster", "Trap", "Loot", "Healing"]
    weights = [0.5, 0.2, 0.2, 0.1]
    dungeon = random.choices(types, weights=weights, k=4)
    dungeon.append("Boss")
    return dungeon

# =======================
# JOIN EMBED
# =======================
def build_join_embed():
    return discord.Embed(
        title="🗺️ Adventure Begins!",
        description="React with ✅ to join! You have 30 seconds.",
        color=discord.Color.blurple()
    )

# =======================
# ADVENTURE COMMAND
# =======================
@bot.command()
async def adventure(ctx):
    global adventure_active, adventure_party, adventure_leader, adventure_difficulty
    global adventure_rooms, current_room_index, adventure_cooldown

    if adventure_active:
        await ctx.send("❌ Please wait until this adventure completes to start a new adventure.")
        return

    if adventure_cooldown:
        await ctx.send("⏳ The dungeon is resting. Please wait a moment.")
        return

    # Character check
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id = ?", (ctx.author.id,))
    if not c.fetchone():
        await ctx.send("❌ You need to create a character first using `=newchar`.")
        conn.close()
        return
    conn.close()

    # Begin join phase
    adventure_active = True
    adventure_party.clear()
    adventure_leader = ctx.author

    join_embed = build_join_embed()
    join_msg = await ctx.send(embed=join_embed)
    await join_msg.add_reaction("✅")

    await asyncio.sleep(30)
    join_msg = await ctx.channel.fetch_message(join_msg.id)

    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    for reaction in join_msg.reactions:
        if reaction.emoji == "✅":
            async for user in reaction.users():
                if user.bot:
                    continue
                c.execute("SELECT level, dexterity, luck, hp FROM players WHERE user_id = ?", (user.id,))
                row = c.fetchone()
                if row:
                    level, dex, luk, hp = row
                    if hp <= 0:
                        continue  # dead players can’t join
                    adventure_party.append({
                        "user": user,
                        "level": level,
                        "dex": dex,
                        "luck": luk,
                        "hp": hp,
                        "revived": False,
                        "special_used": False,
                        "inventory": [],
                        "xp_gained": 0,
                        "loot_pending": []
                    })

    conn.close()

    if not adventure_party:
        await ctx.send("❌ No valid players joined. Adventure cancelled.")
        adventure_active = False
        return

    total_level = sum(p["level"] for p in adventure_party)
    adventure_difficulty = calculate_difficulty(total_level)
    adventure_rooms = generate_rooms()
    current_room_index = 0

    await ctx.send(f"🧙‍♂️ Party formed! Difficulty: **{adventure_difficulty}**")
    await start_next_room(ctx.channel)


# =======================
# ROOM HANDLERS
# =======================
async def start_next_room(channel):
    global current_room_index, adventure_rooms

    if current_room_index >= len(adventure_rooms):
        await end_adventure(channel)
        return

    room_type = adventure_rooms[current_room_index]

    if room_type == "Trap":
        await handle_trap_room(channel)
    elif room_type == "Healing":
        await handle_healing_room(channel)
    elif room_type == "Loot":
        await handle_loot_room(channel)
    elif room_type == "Monster":
        await handle_combat_room(channel, is_boss=False)
    elif room_type == "Boss":
        await handle_combat_room(channel, is_boss=True)

    current_room_index += 1
    await asyncio.sleep(5)
    await start_next_room(channel)

# =======================
# Trap Room
# =======================
async def handle_trap_room(channel):
    embed = discord.Embed(title="⚠️ Trap Room", description="React with 🏃 in 5s to try dodging the trap!")
    message = await channel.send(embed=embed)
    await message.add_reaction("🏃")
    await asyncio.sleep(5)
    message = await channel.fetch_message(message.id)

    reactors = set()
    for reaction in message.reactions:
        if reaction.emoji == "🏃":
            async for user in reaction.users():
                if not user.bot:
                    reactors.add(user.id)

    result = ""
    for player in adventure_party:
        uid = player["user"].id
        if player["hp"] <= 0:
            continue

        if uid in reactors:
            roll = random.randint(1, 20) + player["dex"] + player["luck"]
            if roll < 15:
                player["hp"] -= 25
                if player["hp"] <= 0:
                    result += f"💀 {player['user'].mention} triggered the trap and died!\n"
                else:
                    result += f"❌ {player['user'].mention} triggered the trap and lost 25 HP.\n"
            else:
                result += f"✅ {player['user'].mention} dodged the trap!\n"
        else:
            player["hp"] -= 25
            if player["hp"] <= 0:
                result += f"💀 {player['user'].mention} didn’t react and was killed by the trap!\n"
            else:
                result += f"⏱️ {player['user'].mention} didn’t react in time and took 25 damage.\n"

    embed = discord.Embed(title="🪤 Trap Results", description=result)
    await channel.send(embed=embed)


# =======================
# Healing Shrine
# =======================
async def handle_healing_room(channel):
    embed = discord.Embed(title="🩹 Healing Shrine", description="React with 🧪 in 5s to heal or revive.")
    message = await channel.send(embed=embed)
    await message.add_reaction("🧪")
    await asyncio.sleep(5)
    message = await channel.fetch_message(message.id)

    reactors = set()
    for reaction in message.reactions:
        if reaction.emoji == "🧪":
            async for user in reaction.users():
                if not user.bot:
                    reactors.add(user.id)

    result = ""
    for player in adventure_party:
        uid = player["user"].id
        if uid in reactors:
            if player["hp"] <= 0:
                player["hp"] = 25
                player["revived"] = True
                result += f"💖 {player['user'].mention} was revived with 25 HP!\n"
            else:
                heal = min(50, 100 - player["hp"])
                player["hp"] += heal
                result += f"✨ {player['user'].mention} healed {heal} HP.\n"
        else:
            result += f"⏱️ {player['user'].mention} missed the shrine’s blessing!\n"

    await channel.send(embed=discord.Embed(title="⛪ Shrine Results", description=result))


# =======================
# Loot Room
# =======================
async def handle_loot_room(channel):
    embed = discord.Embed(title="💰 Loot Room", description="React with 🎁 in 5s to scavenge for loot!")
    message = await channel.send(embed=embed)
    await message.add_reaction("🎁")
    await asyncio.sleep(5)
    message = await channel.fetch_message(message.id)

    reactors = set()
    for reaction in message.reactions:
        if reaction.emoji == "🎁":
            async for user in reaction.users():
                if not user.bot:
                    reactors.add(user.id)

    result = ""
    for player in adventure_party:
        uid = player["user"].id
        if player["hp"] <= 0:
            result += f"☠️ {player['user'].mention} is dead and can’t loot.\n"
            continue
        if uid in reactors:
            roll = random.randint(1, 20) + player["luck"]
            if roll < 15:
                result += f"💤 {player['user'].mention} found nothing...\n"
            else:
                result += f"🎉 {player['user'].mention} found something shiny! (TBD)\n"
                player["loot_pending"].append("TBD Item")
        else:
            result += f"⏱️ {player['user'].mention} didn’t react in time and missed their chance!\n"

    await channel.send(embed=discord.Embed(title="🎁 Loot Results", description=result))


# =======================
# COMBAT CONSTANTS
# =======================
EMOJI_ATTACK = "⚔️"
EMOJI_SPECIAL = "💥"
EMOJI_POTION = "🧪"

class_stat_map = {
    "Warrior": "strength",
    "Mage": "magic",
    "Rogue": "dexterity"
}

# =======================
# COMBAT: MONSTER ROOM (with gear bonuses + boss abilities)
# =======================

async def handle_combat_room(channel, is_boss=False):
    global adventure_party

    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    def unlock_title(user_id, title):
        c.execute("INSERT OR IGNORE INTO titles (user_id, title, earned_on) VALUES (?, ?, datetime('now'))", (user_id, title))

    difficulty_monsters = {
        "Easy": ["Slime", "Goblin"],
        "Normal": ["Orc", "Skeleton"],
        "Hard": ["Wraith", "Ogre"],
        "Nightmare": ["Lich", "Dread Knight"],
        "Hell": ["Abyss Fiend", "Voidwalker"]
    }

    boss_monsters = {
        "Easy": ["Slime King", "Fungus Fiend", "Bone Beetle"],
        "Normal": ["Grave Knight", "Rotting Minotaur", "Firebreand Troll"],
        "Hard": ["Doom Warden", "Cursed Hydra", "Soul Drinker"],
        "Nightmare": ["Void Lord", "Spectral Butcher", "Ashen Revenant"],
        "Hell": ["Demon King"]
    }

    monster_flavor = {
        "Slime": "It jiggles menacingly...",
        "Goblin": "The goblin snarls and lunges!",
        "Orc": "The orc bellows with rage!",
        "Skeleton": "Bones clatter with eerie purpose.",
        "Wraith": "A chilling wail fills the air...",
        "Ogre": "The ogre grunts, swinging wildly.",
        "Lich": "Dark energy pulses from the Lich’s staff...",
        "Dread Knight": "Steel scrapes as it raises its cursed blade.",
        "Abyss Fiend": "A void-black maw stretches open...",
        "Voidwalker": "Reality distorts around its presence.",
        "Slime King": "The crown jiggles ominously...",
        "Fungus Fiend": "Spores burst with every breath.",
        "Bone Beetle": "Chitin scrapes like swords clashing.",
        "Grave Knight": "Echoes of vengeance rattle his armor.",
        "Rotting Minotaur": "Its stench is almost visible.",
        "Firebreand Troll": "Drool sizzles as it hits the floor.",
        "Doom Warden": "Shadows bend around its hulking form.",
        "Cursed Hydra": "Seven heads whisper in unknown tongues.",
        "Soul Drinker": "Eyes glow with stolen memories.",
        "Void Lord": "Reality shudders around him.",
        "Spectral Butcher": "Your name is already on his cleaver.",
        "Ashen Revenant": "It died once. You won’t be so lucky.",
        "Demon King": "Hell itself trembles in his presence."
    }

    difficulty = adventure_difficulty
    monster_name = random.choice(boss_monsters[difficulty] if is_boss else difficulty_monsters[difficulty])
    monster_hp = 150 if is_boss else 80
    monster_max_hp = monster_hp
    monster_attack_power = 25 if is_boss else 15

    await channel.send(f"👹 **{monster_name}** appears!\n*{monster_flavor[monster_name]}*")

    while monster_hp > 0:
        def hp_bar(current, maxhp, emoji_full, emoji_empty):
            ratio = current / maxhp
            bars = int(ratio * 10)
            return emoji_full * bars + emoji_empty * (10 - bars)

        monster_display = hp_bar(monster_hp, monster_max_hp, "🟥", "⬛")
        party_display = ""

        for p in adventure_party:
            bar = hp_bar(p["hp"], 100, "🟩", "⬛") if p["hp"] > 0 else "☠️"
            party_display += f"{p['user'].display_name}: {bar}\n"

        embed = discord.Embed(title="⚔️ Combat Phase", description=f"**{monster_name} HP:** {monster_display}")
        embed.add_field(name="Party Status", value=party_display, inline=False)
        embed.set_footer(text="React with ⚔️, 💥, or 🧪")
        msg = await channel.send(embed=embed)

        for emoji in [EMOJI_ATTACK, EMOJI_SPECIAL, EMOJI_POTION]:
            await msg.add_reaction(emoji)

        await asyncio.sleep(5)
        msg = await channel.fetch_message(msg.id)

        user_actions = {}
        for reaction in msg.reactions:
            if reaction.emoji in [EMOJI_ATTACK, EMOJI_SPECIAL, EMOJI_POTION]:
                async for user in reaction.users():
                    if not user.bot:
                        user_actions[user.id] = reaction.emoji
        reacted_users = set(user_actions.keys())
        round_log = ""  # Initialize log
        user_actions = {}
        for reaction in msg.reactions:
            if reaction.emoji in [EMOJI_ATTACK, EMOJI_SPECIAL, EMOJI_POTION]:
                async for user in reaction.users():
                    if not user.bot:
                        user_actions[user.id] = reaction.emoji

        reacted_users = set(user_actions.keys())
        round_log += "\n"  # space out

        for player in adventure_party:
            uid = player["user"].id
            if player["hp"] <= 0:
                continue
            if uid not in reacted_users:
                round_log += f"⏱️ {player['user'].mention} didn't react in time and missed their turn!\n"





        round_log = ""
        damage_tracker = {}

        for player in adventure_party:
            uid = player["user"].id
            if player["hp"] <= 0:
                continue

            action = user_actions.get(uid, EMOJI_ATTACK)

            if action == EMOJI_POTION:
                if player["hp"] >= 100:
                    round_log += f"🧪 {player['user'].mention} tried to use a potion but is already full HP!\n"
                else:
                    heal = min(25, 100 - player["hp"])
                    player["hp"] += heal
                    round_log += f"🧪 {player['user'].mention} healed {heal} HP.\n"

            elif action == EMOJI_SPECIAL and not player["special_used"]:
                stat_name = class_stat_map[get_player_class(uid)]
                stat = get_effective_stat(uid, stat_name)
                luck = get_effective_stat(uid, "luck")
                dmg = (stat * 2) + random.randint(10, 20)
                monster_hp -= dmg
                damage_tracker[uid] = dmg
                player["special_used"] = True
                round_log += f"💥 {player['user'].mention} used their **Special** and dealt **{dmg} CRIT**!\n"
                if dmg >= 100:
                    unlock_title(uid, "One-Shot Wonder")
                    grant_achievement(c, uid, "One-Shot Wonder", "Dealt 100+ damage in a single attack.")
            else:
                stat_name = class_stat_map[get_player_class(uid)]
                stat = get_effective_stat(uid, stat_name)
                luck = get_effective_stat(uid, "luck")
                dmg, crit = calculate_damage(uid, stat, luck)
                monster_hp -= dmg
                damage_tracker[uid] = dmg
                hit_type = "**CRIT!**" if crit else ""
                round_log += f"⚔️ {player['user'].mention} attacked for {dmg} {hit_type}\n"
                if dmg >= 100:
                    unlock_title(uid, "One-Shot Wonder")
                    grant_achievement(c, uid, "One-Shot Wonder", "Dealt 100+ damage in a single attack.")

        # Boss special attacks
        if monster_hp > 0 and is_boss and random.random() < 0.4:
            move = random.choice(["Cleave", "Poison Cloud", "Dark Heal"])
            if move == "Cleave":
                round_log += "\n⚠️ The boss raises its weapon... **Cleave incoming!**\n"
                for player in adventure_party:
                    if player["hp"] > 0:
                        if calculate_dodge(player["user"].id, player["dex"], 0):
                            round_log += f"💨 {player['user'].mention} dodged the Cleave!\n"
                        else:
                            dmg = int(monster_attack_power * 0.75)
                            player["hp"] -= dmg
                            if player["hp"] <= 0:
                                round_log += f"💀 {player['user'].mention} was cleaved and died!\n"
                                c.execute("UPDATE stats SET deaths = deaths + 1 WHERE user_id = ?", (player["user"].id,))
                            else:
                                round_log += f"💢 {player['user'].mention} took {dmg} damage from Cleave!\n"

            elif move == "Poison Cloud":
                round_log += "\n🧪 The boss exhales a toxic **Poison Cloud**!\n"
                for player in adventure_party:
                    if player["hp"] > 0:
                        player["hp"] -= 10
                        round_log += f"🤢 {player['user'].mention} took 10 poison damage.\n"
                        if player["hp"] <= 0:
                            round_log += f"💀 {player['user'].mention} succumbed to the poison.\n"
                            c.execute("UPDATE stats SET deaths = deaths + 1 WHERE user_id = ?", (player["user"].id,))

            elif move == "Dark Heal":
                healed = random.randint(20, 40)
                monster_hp = min(monster_max_hp, monster_hp + healed)
                round_log += f"\n🖤 The boss channels dark energy and heals **{healed} HP**.\n"

        elif monster_hp > 0 and damage_tracker:
            target_id = max(damage_tracker, key=damage_tracker.get)
            target = next(p for p in adventure_party if p["user"].id == target_id)
            dex = get_effective_stat(target_id, "dexterity")
            if calculate_dodge(target_id, dex, 0):
                round_log += f"💨 {target['user'].mention} dodged the attack!\n"
            else:
                target["hp"] -= monster_attack_power
                if target["hp"] <= 0:
                    round_log += f"💀 {target['user'].mention} was struck and died!\n"
                    c.execute("UPDATE stats SET deaths = deaths + 1 WHERE user_id = ?", (target_id,))
                else:
                    round_log += f"💢 {target['user'].mention} took {monster_attack_power} damage!\n"

        await channel.send(embed=discord.Embed(title="🎯 Combat Round Results", description=round_log))

        if all(p["hp"] <= 0 for p in adventure_party):
            await channel.send("☠️ The party has been wiped! The adventure ends here.")
            await end_adventure(channel)
            return

    await channel.send(f"🏆 {monster_name} has been defeated!")
    for p in adventure_party:
        if p["hp"] > 0:
            p["xp_gained"] += 100
            if is_boss:
                unlock_title(p["user"].id, monster_name)

    conn.commit()
    conn.close()


# =======================
# XP / LEVELING 
# =======================
def get_required_xp(level):
    return level * 500

def generate_loot(difficulty):
    table = {
        "Easy": ["Rusty Dagger", "Worn Cloak", "Cracked Wand"],
        "Normal": ["Iron Sword", "Sturdy Shield", "Apprentice Staff"],
        "Hard": ["Flaming Axe", "Shadow Cloak", "Arcane Rod"],
        "Nightmare": ["Doom Blade", "Soul Robes", "Witchbinder"],
        "Hell": ["Demon Fang", "Hellforged Plate", "Void Core"]
    }
    rarity = {
        "Easy": "Common",
        "Normal": "Rare",
        "Hard": "Epic",
        "Nightmare": "Legendary",
        "Hell": "Legendary"
    }
    stat_bonus = {
        "Rusty Dagger": {"DEX": 1},
        "Worn Cloak": {"LUK": 1},
        "Cracked Wand": {"MAG": 1},
        "Iron Sword": {"STR": 2},
        "Sturdy Shield": {"DEX": 2},
        "Apprentice Staff": {"MAG": 2},
        "Flaming Axe": {"STR": 3},
        "Shadow Cloak": {"LUK": 3},
        "Arcane Rod": {"MAG": 3},
        "Doom Blade": {"STR": 5},
        "Soul Robes": {"MAG": 5},
        "Witchbinder": {"LUK": 5},
        "Demon Fang": {"STR": 6},
        "Hellforged Plate": {"DEX": 6},
        "Void Core": {"MAG": 6}
    }

    name = random.choice(table[difficulty])
    return {
        "name": name,
        "rarity": rarity[difficulty],
        "value": random.randint(100, 300),
        "bonus": stat_bonus.get(name, {})
    }

async def end_adventure(channel):
    global adventure_active, adventure_cooldown

    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    def unlock_title(user_id, title):
        c.execute("INSERT OR IGNORE INTO titles (user_id, title, earned_on) VALUES (?, ?, datetime('now'))", (user_id, title))

    summary = "📜 **Adventure Summary**\n"
    loot_section = ""
    xp_section = ""
    death_section = ""

    for player in adventure_party:
        uid = player["user"].id
        survived = player["hp"] > 0
        c.execute("SELECT level, xp FROM players WHERE user_id = ?", (uid,))
        level, xp = c.fetchone()
        gained_xp = player["xp_gained"]
        new_xp = xp + gained_xp

        leveled_up = False
        while new_xp >= get_required_xp(level):
            new_xp -= get_required_xp(level)
            level += 1
            c.execute("UPDATE players SET stat_points = stat_points + 1 WHERE user_id = ?", (uid,))
            leveled_up = True

        c.execute("UPDATE players SET xp = ?, level = ?, hp = ? WHERE user_id = ?",
                  (new_xp, level, player["hp"], uid))

        if survived:
            # Check current inventory size
            c.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (uid,))
            inventory_count = c.fetchone()[0]

            for item_name in player["loot_pending"]:
                if inventory_count >= 20:
                    loot_section += f"❌ {player['user'].mention} couldn't receive loot — inventory full!\n"
                    continue

                item = generate_loot(adventure_difficulty)
                # Check if player already owns the item
                c.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (uid, item["name"]))
                existing = c.fetchone()

                if existing:
                    current_qty = existing[0]
                    if current_qty >= 10:
                        loot_section += f"❌ {player['user'].mention} already owns 10x **{item['name']}** – stack full.\n"
                        continue
                    new_qty = min(10, current_qty + 1)
                    c.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, uid, item["name"]))
                else:
                    c.execute("INSERT INTO inventory (user_id, item_name, rarity, value, quantity, type) VALUES (?, ?, ?, ?, 1, 'misc')",
                              (uid, item["name"], item["rarity"], item["value"]))
                    inventory_count += 1

                loot_section += f"🎁 {player['user'].mention} received: **{item['name']}** ({item['rarity']})\n"
                if item["rarity"] == "Legendary":
                    unlock_title(uid, "Treasure Fiend")
                    grant_achievement(c, uid, "Treasure Fiend", "Found a legendary item in an adventure.")

        else:
            death_section += f"💀 {player['user'].mention} died and lost all loot. F.\n"

        xp_section += f"✨ {player['user'].mention} gained {gained_xp} XP"
        if leveled_up:
            xp_section += f" and leveled up to **Lv. {level}**!"
        xp_section += "\n"

    conn.commit()
    conn.close()

    embed = discord.Embed(title="🏁 Adventure Complete!", color=discord.Color.gold())
    embed.add_field(name="XP Gained", value=xp_section or "None", inline=False)
    embed.add_field(name="Loot", value=loot_section or "No survivors to claim rewards.", inline=False)
    if death_section:
        embed.add_field(name="Casualties", value=death_section, inline=False)

    await channel.send(embed=embed)
    await channel.send("🛑 Dungeon is closed for 2 minutes...")
    await asyncio.sleep(cooldown_timer)
    await channel.send("✅ Dungeon has reopened. Type `=adventure` to begin again!")

    adventure_active = False
    adventure_cooldown = True
    await asyncio.sleep(cooldown_timer)
    adventure_cooldown = False



# =======================
# USE ITEM
# =======================
@bot.command()
async def use(ctx, *, item_name):
    user_id = ctx.author.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Check if user is in an active adventure
    if adventure_active and any(p["user"].id == user_id for p in adventure_party):
        await ctx.send("⚠️ You can't use items during an adventure. Use potions through reactions.")
        conn.close()
        return

    # Fetch item details
    c.execute("SELECT quantity, type FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
    row = c.fetchone()
    if not row:
        await ctx.send("❌ You don't have that item.")
        conn.close()
        return

    qty, item_type = row
    if item_type != "potion":
        await ctx.send("⚠️ This item isn't usable.")
        conn.close()
        return

    # Heal logic
    c.execute("SELECT hp FROM players WHERE user_id = ?", (user_id,))
    current_hp = c.fetchone()[0]
    if current_hp >= 100:
        await ctx.send("💤 You're already at full health.")
        conn.close()
        return

    heal = 25
    new_hp = min(100, current_hp + heal)
    c.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))

    # Adjust inventory
    if qty > 1:
        c.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, item_name))
    else:
        c.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))

    conn.commit()
    conn.close()
    await ctx.send(f"🧪 You used a {item_name} and healed {new_hp - current_hp} HP!")

# =======================
# EQUIP ITEM
# =======================
@bot.command()
async def equip(ctx, *, item_name):
    user_id = ctx.author.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Verify item
    c.execute("SELECT type FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
    item = c.fetchone()
    if not item:
        await ctx.send("❌ You don’t have that item.")
        return

    item_type = item[0]

    # Check player class
    c.execute("SELECT class FROM players WHERE user_id = ?", (user_id,))
    user_class = c.fetchone()[0]

    # Restriction logic
    if user_class == "Mage" and item_type not in ["wand", "robe", "hood"]:
        await ctx.send("🪄 Mages can only equip **wands**, **robes**, and **hoods**.")
        return
    if user_class == "Rogue" and item_type == "helmet":
        await ctx.send("🗡️ Rogues can’t wear **helmets**.")
        return

    # Equip slot mapping
    if item_type in ["armor", "robe"]:
        slot = "chest"
    elif item_type in ["helmet", "hood"]:
        slot = "head"
    elif item_type == "weapon" or item_type == "wand":
        slot = "weapon"
    else:
        await ctx.send("⚠️ This item can’t be equipped.")
        return

    # Unequip current item in that slot
    c.execute(f"SELECT {slot} FROM equipment WHERE user_id = ?", (user_id,))
    currently_equipped = c.fetchone()[0]
    if currently_equipped:
        c.execute("UPDATE inventory SET equipped = 0 WHERE user_id = ? AND item_name = ?", (user_id, currently_equipped))

    # Equip new item
    c.execute(f"UPDATE equipment SET {slot} = ? WHERE user_id = ?", (item_name, user_id))
    c.execute("UPDATE inventory SET equipped = 1 WHERE user_id = ? AND item_name = ?", (user_id, item_name))

    conn.commit()
    conn.close()

    await ctx.send(f"✅ Equipped **{item_name}** to your {slot} slot.")

# =======================
# calculate_dodge
# =======================
def calculate_dodge(user_id, defender_dex, attacker_luk):
    base_dodge = 5 + defender_dex
    rarity_dodge_bonus = {
        "Common": 0,
        "Rare": 2,
        "Epic": 4,
        "Legendary": 7
    }
    armor_rarity = get_equipped_item_rarity(user_id, "equipped_armor")
    base_dodge += rarity_dodge_bonus.get(armor_rarity, 0)
    base_dodge -= int(attacker_luk * 0.2)
    base_dodge = max(0, min(base_dodge, 90))  # Clamp chance

    return random.randint(1, 100) <= base_dodge
# =======================
# UNEQUIP ITEM
# =======================
@bot.command()
async def unequip(ctx):
    user_id = ctx.author.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Ensure equipment row exists
    c.execute("INSERT OR IGNORE INTO equipment (user_id, head, chest, weapon) VALUES (?, '', '', '')", (user_id,))

    c.execute("SELECT head, chest, weapon FROM equipment WHERE user_id = ?", (user_id,))
    eq = c.fetchone()
    unequipped = []

    for slot, item in zip(["head", "chest", "weapon"], eq):
        if item:
            unequipped.append(item)
            c.execute(f"UPDATE equipment SET {slot} = '' WHERE user_id = ?", (user_id,))
            c.execute("UPDATE inventory SET equipped = 0 WHERE user_id = ? AND item_name = ?", (user_id, item))

    conn.commit()
    conn.close()

    if unequipped:
        await ctx.send(f"🧤 Unequipped: {', '.join(unequipped)}")
    else:
        await ctx.send("🧼 You have nothing equipped.")


# =======================
# CHARACTER STAT REACTION HANDLER
# =======================
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or reaction.message.author != bot.user:
        return

    emojis = {
        "💪": "strength",
        "🧠": "magic",
        "🩰": "dexterity",
        "🍀": "luck"
    }

    if str(reaction.emoji) not in emojis:
        return

    user_id = user.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Check stat points
    c.execute("SELECT stat_points FROM players WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row or row[0] <= 0:
        return

    # Apply stat increase
    stat = emojis[str(reaction.emoji)]
    c.execute(f"UPDATE players SET {stat} = {stat} + 1, stat_points = stat_points - 1 WHERE user_id = ?", (user_id,))
    conn.commit()

    # Fetch updated player data
    c.execute("SELECT strength, magic, dexterity, luck, stat_points FROM players WHERE user_id = ?", (user_id,))
    str_, mag, dex, luk, pts = c.fetchone()
    conn.close()

    # Edit the embed in place (optional but useful)
    embed = reaction.message.embeds[0]
    for i, field in enumerate(embed.fields):
        if field.name in ["STR", "MAG", "DEX", "LUK"]:
            new_val = {
                "STR": str_,
                "MAG": mag,
                "DEX": dex,
                "LUK": luk
            }[field.name]
            embed.set_field_at(i, name=field.name, value=new_val, inline=True)

        if field.name == "Stat Points":
            embed.set_field_at(i, name="Stat Points", value=pts, inline=True)

    await reaction.message.edit(embed=embed)

    if pts <= 0:
        await reaction.message.clear_reactions()



# ----------------------------
# Command: =titles
# ----------------------------
@bot.command()
async def titles(ctx):
    user_id = ctx.author.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Fetch all earned titles
    c.execute("SELECT title FROM titles WHERE user_id = ?", (user_id,))
    rows = c.fetchall()

    if not rows:
        await ctx.send("❌ You don’t have any titles yet.")
        return

    title_list = [row[0] for row in rows]
    emoji_map = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    emoji_to_title = dict(zip(emoji_map, title_list))

    desc = "\n".join(f"{emoji} – {title}" for emoji, title in emoji_to_title.items())
    embed = discord.Embed(title="🎖️ Your Titles", description=desc, color=discord.Color.purple())
    embed.set_footer(text="React to equip a title.")
    msg = await ctx.send(embed=embed)

    for emoji in emoji_to_title.keys():
        await msg.add_reaction(emoji)

    def check(reaction, user):
        return user == ctx.author and reaction.message.id == msg.id and str(reaction.emoji) in emoji_to_title

    try:
        reaction, _ = await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("⌛ Title selection timed out.")
        return

    new_title = emoji_to_title[str(reaction.emoji)]
    c.execute("UPDATE players SET title = ? WHERE user_id = ?", (new_title, user_id))
    conn.commit()
    conn.close()

    await ctx.send(f"✅ Title equipped: **{new_title}**")



# =======================
# Command: =flee
# =======================
@bot.command()
async def flee(ctx):
    global adventure_party, adventure_active, adventure_cooldown

    if not adventure_active:
        await ctx.send("❌ You are not currently in an adventure.")
        return

    user_id = ctx.author.id
    fleeing_player = next((p for p in adventure_party if p["user"].id == user_id), None)

    if not fleeing_player:
        await ctx.send("❌ You are not in the current adventure party.")
        return

    # Remove player from party and record them as fled
    adventure_party.remove(fleeing_player)

    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO titles (user_id, title, earned_on) VALUES (?, 'Coward', datetime('now'))", (user_id,))
    conn.commit()
    conn.close()

    await ctx.send(f"🏃‍♂️ {ctx.author.mention} has fled the dungeon. Their loot and XP will not be saved.")

    # If all players have fled or died, end the adventure
    if all(p["hp"] <= 0 for p in adventure_party) or len(adventure_party) == 0:
        await ctx.send("☠️ Everyone is gone. The adventure ends.")
        await end_adventure(ctx.channel)
        return


# =======================
# BRAINROT ADVENTURE – INVENTORY SYSTEM
# =======================
@bot.command()
async def inventory(ctx):
    user_id = ctx.author.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Fetch inventory
    c.execute("SELECT item_name, rarity, quantity, type, equipped FROM inventory WHERE user_id = ?", (user_id,))
    items = c.fetchall()
    conn.close()

    if not items:
        await ctx.send("🎒 Your inventory is empty.")
        return

    # Format inventory display
    desc = ""
    for name, rarity, qty, item_type, equipped in items:
        star = "⭐" if equipped else ""
        stack = f"x{qty}" if qty > 1 else ""
        desc += f"{star} **{name}** ({rarity}) {stack} - *{item_type}*\n"

    embed = discord.Embed(title="🎒 Inventory", description=desc[:4000], color=discord.Color.dark_gold())
    await ctx.send(embed=embed)


@bot.command()
async def respec(ctx, new_class: str = None):
    user_id = ctx.author.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    valid_classes = ["Warrior", "Mage", "Rogue"]
    if not new_class or new_class.capitalize() not in valid_classes:
        await ctx.send("🔄 Usage: `=respec [class]`\nValid classes: Warrior, Mage, Rogue")
        conn.close()
        return

    new_class = new_class.capitalize()

    # Check player
    c.execute("SELECT level FROM players WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        await ctx.send("❌ You don’t have a character. Use `=newchar` first.")
        conn.close()
        return

    level = row[0]

    # Check currency
    c.execute("SELECT currency FROM profiles WHERE user_id = ?", (user_id,))
    currency_row = c.fetchone()
    if not currency_row or currency_row[0] < 10000:
        await ctx.send("💸 You need 10,000 VAbux to respec.")
        conn.close()
        return

    # Reset stats
    c.execute('''
        UPDATE players
        SET class = ?, strength = 1, magic = 1, dexterity = 1, luck = 1,
            stat_points = ?, special_used = 0
        WHERE user_id = ?
    ''', (new_class, level - 1, user_id))

    c.execute("UPDATE profiles SET currency = currency - 10000 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    await ctx.send(f"✅ You have respecced as a **{new_class}**. Your stats have been reset.")



# =======================
# HELPER FUNCTIONS – Combat Mechanics
# =======================

def calculate_damage(user_id, attacker_stat, attacker_luk):
    base = random.randint(5, 15)
    rarity_bonus = {
        "Common": 0,
        "Rare": 3,
        "Epic": 7,
        "Legendary": 15
    }
    weapon_rarity = get_equipped_item_rarity(user_id, "equipped_weapon")
    base += rarity_bonus.get(weapon_rarity, 0)

    crit_chance = 5 + (attacker_luk * 2)
    crit = random.randint(1, 75) <= crit_chance

    return int((base + attacker_stat * 2) * (2 if crit else 1)), crit

# =======================
# HELPER FUNCTIONS – Get Equipped Item Rarity
# =======================

def get_equipped_item_rarity(user_id, slot):
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Get the item name from the correct equipment slot
    c.execute(f"SELECT {slot} FROM equipment WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if not result or not result[0]:
        conn.close()
        return "Common"

    item_name = result[0]
    c.execute("SELECT rarity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
    rarity_row = c.fetchone()
    conn.close()
    return rarity_row[0] if rarity_row else "Common"


# =======================
# GET EFFECTIVE STAT WITH GEAR BONUS
# =======================
def get_effective_stat(user_id, stat_name):
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Get base stat from players table
    c.execute(f"SELECT {stat_name} FROM players WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        return 0
    base_stat = row[0]

    # Get equipped gear
    c.execute("SELECT head, chest, weapon FROM equipment WHERE user_id = ?", (user_id,))
    eq = c.fetchone()
    gear_items = [slot for slot in eq if slot]

    bonus = 0
    for item_name in gear_items:
        c.execute("SELECT stat_bonus FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        row = c.fetchone()
        if row and row[0]:
            bonus += row[0]

    conn.close()
    return base_stat + bonus

# =======================
# =healme
# =======================
@bot.command()
async def healme(ctx):
    user_id = ctx.author.id
    now = int(time.time())

    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Check if in an adventure
    if adventure_active and any(p["user"].id == user_id for p in adventure_party):
        await ctx.send("⚠️ You can’t use this during an adventure.")
        return

    # Create cooldown table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS heal_cooldowns (
            user_id INTEGER PRIMARY KEY,
            last_used INTEGER
        )
    ''')

    # Check cooldown
    c.execute("SELECT last_used FROM heal_cooldowns WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row and now - row[0] < 43200:
        remaining = 43200 - (now - row[0])
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        await ctx.send(f"⏳ You can heal again in {hours}h {minutes}m.")
        return

    # Heal the player
    c.execute("UPDATE players SET hp = 100 WHERE user_id = ?", (user_id,))
    c.execute("REPLACE INTO heal_cooldowns (user_id, last_used) VALUES (?, ?)", (user_id, now))

    conn.commit()
    conn.close()

    await ctx.send("💊 You’ve been healed to full HP. Come back in 12 hours!")

# =======================
# Command: =tavern
# =======================
# =======================
# =tavern Main Hub
# =======================
@bot.command()
async def tavern(ctx):
    user_id = ctx.author.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Ensure only one tavern session per user
    c.execute("SELECT 1 FROM tavern_flags WHERE user_id = ?", (user_id,))
    if c.fetchone():
        await ctx.send("🍺 You're already in a tavern session!")
        return
    c.execute("INSERT INTO tavern_flags (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

    emoji_shop = "🛒"
    emoji_sell = "💰"
    emoji_exit = "🚪"

    embed = discord.Embed(
        title=f"🍻 Welcome to the Dragonkin Tavern, {ctx.author.display_name}!",
        description="What would you like to do?\n\n"
                    f"{emoji_shop} — Browse the shop\n"
                    f"{emoji_sell} — Sell your loot\n"
                    f"{emoji_exit} — Exit the tavern",
        color=discord.Color.dark_red()
    )
    msg = await ctx.send(embed=embed)
    for emoji in [emoji_shop, emoji_sell, emoji_exit]:
        await msg.add_reaction(emoji)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in [emoji_shop, emoji_sell, emoji_exit] and reaction.message.id == msg.id

    try:
        reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("🚷 Hey buddy, there’s no loitering. Get outta here.")
        conn = sqlite3.connect("brainrot.db")
        conn.execute("DELETE FROM tavern_flags WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return

    if str(reaction.emoji) == emoji_shop:
        await show_shop_menu(ctx)
    elif str(reaction.emoji) == emoji_sell:
        await show_sell_menu(ctx)
    else:
        await ctx.send("👋 Come back when you're thirsty!")

    # Clean up tavern session flag
    conn = sqlite3.connect("brainrot.db")
    conn.execute("DELETE FROM tavern_flags WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# =======================
# Tavern: Buy Menu
# =======================
async def show_shop_menu(ctx, page=0):
    user_id = ctx.author.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Static shop inventory
    shop_items = [
        {"name": "Health Potion", "price": 50, "rarity": "Common", "type": "potion"},
        {"name": "Training Sword", "price": 100, "rarity": "Common", "type": "weapon"},
        {"name": "Worn Armor", "price": 120, "rarity": "Common", "type": "armor"},
        {"name": "Old Wand", "price": 100, "rarity": "Common", "type": "wand"},
        {"name": "Leather Hood", "price": 80, "rarity": "Common", "type": "hood"},
        {"name": "Cloth Robe", "price": 90, "rarity": "Common", "type": "robe"}
    ]

    # Show 5 items per page
    per_page = 5
    pages = (len(shop_items) - 1) // per_page + 1
    items = shop_items[page * per_page:(page + 1) * per_page]

    # Get user currency
    c.execute("SELECT currency FROM profiles WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    gold = result[0] if result else 0

    embed = discord.Embed(title="🛒 Tavern Shop", description=f"VAbux: {gold}", color=discord.Color.green())
    emoji_map = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    emoji_to_item = {}

    for i, item in enumerate(items):
        emoji = emoji_map[i]
        embed.add_field(name=f"{emoji} {item['name']}",
                        value=f"{item['rarity']} {item['type'].capitalize()} – {item['price']} VAbux",
                        inline=False)
        emoji_to_item[emoji] = item

    embed.set_footer(text="React to buy an item. ⬅️➡️ to scroll.")
    msg = await ctx.send(embed=embed)

    for emoji in emoji_map[:len(items)] + ["⬅️", "➡️"]:
        await msg.add_reaction(emoji)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in emoji_map + ["⬅️", "➡️"] and reaction.message.id == msg.id

    try:
        reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("🚫 If you’re not going to buy anything, get out of here!")
        return

    if str(reaction.emoji) == "⬅️" and page > 0:
        await show_shop_menu(ctx, page - 1)
        return
    elif str(reaction.emoji) == "➡️" and page < pages - 1:
        await show_shop_menu(ctx, page + 1)
        return

    item = emoji_to_item.get(str(reaction.emoji))
    if not item:
        return

    # Validate purchase
    c.execute("SELECT currency FROM profiles WHERE user_id = ?", (user_id,))
    gold = c.fetchone()[0]
    if gold < item["price"]:
        await ctx.send("❌ You can't afford that.")
        conn.close()
        return

    # Check inventory space
    c.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (user_id,))
    count = c.fetchone()[0]
    if count >= 20:
        await ctx.send("❌ Your inventory is full.")
        conn.close()
        return

    # Check stack size
    c.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item["name"]))
    row = c.fetchone()
    if row and row[0] >= 10:
        await ctx.send("❌ You already have the max stack (10) of that item.")
        conn.close()
        return

    # Deduct currency
    c.execute("UPDATE profiles SET currency = currency - ? WHERE user_id = ?", (item["price"], user_id))

    # Add item
    if row:
        c.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?",
                  (user_id, item["name"]))
    else:
        c.execute("INSERT INTO inventory (user_id, item_name, rarity, value, quantity, type) VALUES (?, ?, ?, ?, 1, ?)",
                  (user_id, item["name"], item["rarity"], item["price"], item["type"]))

    conn.commit()
    conn.close()

    await ctx.send(f"✅ You bought **{item['name']}**!")


# =======================
# Tavern: Sell Menu
# =======================
async def show_sell_menu(ctx, page=0):
    user_id = ctx.author.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Fetch all sellable items (excluding equipped ones)
    c.execute("SELECT item_name, rarity, quantity, value, type, equipped FROM inventory WHERE user_id = ?", (user_id,))
    all_items = [row for row in c.fetchall() if row[5] == 0]  # Not equipped only

    if not all_items:
        await ctx.send("💼 You have no unequipped items to sell.")
        return

    per_page = 5
    pages = (len(all_items) - 1) // per_page + 1
    items = all_items[page * per_page:(page + 1) * per_page]

    emoji_map = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    emoji_to_item = {}

    embed = discord.Embed(title="💰 Sell Items", description="Select an item to sell (50% value)", color=discord.Color.orange())
    for i, (name, rarity, qty, value, item_type, equipped) in enumerate(items):
        emoji = emoji_map[i]
        sell_price = value // 2
        embed.add_field(
            name=f"{emoji} {name} (x{qty})",
            value=f"{rarity} {item_type} – {sell_price} VAbux each",
            inline=False
        )
        emoji_to_item[emoji] = (name, qty, sell_price)

    embed.set_footer(text="⬅️➡️ to scroll, or react to sell an item.")
    msg = await ctx.send(embed=embed)

    for emoji in emoji_map[:len(items)] + ["⬅️", "➡️"]:
        await msg.add_reaction(emoji)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in emoji_map + ["⬅️", "➡️"] and reaction.message.id == msg.id

    try:
        reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("💨 If you’re not gonna sell, stop wasting my time!")
        return

    if str(reaction.emoji) == "⬅️" and page > 0:
        await show_sell_menu(ctx, page - 1)
        return
    elif str(reaction.emoji) == "➡️" and page < pages - 1:
        await show_sell_menu(ctx, page + 1)
        return

    # Sell logic
    name, qty, sell_price = emoji_to_item.get(str(reaction.emoji), (None, 0, 0))
    if not name:
        return

    # Sell 1 quantity
    if qty > 1:
        c.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, name))
    else:
        c.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, name))

    c.execute("UPDATE profiles SET currency = currency + ? WHERE user_id = ?", (sell_price, user_id))
    conn.commit()
    conn.close()

    await ctx.send(f"🪙 Sold **{name}** for {sell_price} VAbux!")

# =======================
# Tavern: Dice
# ========
@bot.command()
async def dice(ctx, opponent: discord.Member, amount: int):
    challenger = ctx.author
    challenged = opponent

    if challenger.id == challenged.id:
        await ctx.send("❌ You can’t challenge yourself.")
        return

    if amount <= 0:
        await ctx.send("❌ Bet amount must be positive.")
        return

    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Check both players have profiles
    c.execute("SELECT currency FROM profiles WHERE user_id = ?", (challenger.id,))
    challenger_row = c.fetchone()
    c.execute("SELECT currency FROM profiles WHERE user_id = ?", (challenged.id,))
    challenged_row = c.fetchone()

    if not challenger_row or not challenged_row:
        await ctx.send("❌ Both players must have profiles.")
        conn.close()
        return

    if challenger_row[0] < amount or challenged_row[0] < amount:
        await ctx.send("💸 One of the players doesn’t have enough VAbux.")
        conn.close()
        return

    embed = discord.Embed(
        title="🎲 Dice Challenge!",
        description=f"{challenger.mention} has challenged {challenged.mention} to a {amount} VAbux bet.\n\n"
                    f"{challenged.mention}, react with 🎲 to accept!",
        color=discord.Color.green()
    )
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎲")

    def check(reaction, user):
        return user == challenged and str(reaction.emoji) == "🎲" and reaction.message.id == msg.id

    try:
        await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("⌛ Challenge expired.")
        conn.close()
        return

    # Get luck values
    c.execute("SELECT luck FROM players WHERE user_id = ?", (challenger.id,))
    luck_challenger = c.fetchone()[0]
    c.execute("SELECT luck FROM players WHERE user_id = ?", (challenged.id,))
    luck_challenged = c.fetchone()[0]

    # Roll dice + luck bonus
    roll_challenger = random.randint(1, 20) + luck_challenger
    roll_challenged = random.randint(1, 20) + luck_challenged

    winner, loser = (challenger, challenged) if roll_challenger >= roll_challenged else (challenged, challenger)
    c.execute("UPDATE profiles SET currency = currency + ? WHERE user_id = ?", (amount, winner.id))
    c.execute("UPDATE profiles SET currency = currency - ? WHERE user_id = ?", (amount, loser.id))

    # Track wins
    c.execute("INSERT INTO stats(user_id, dice_wins) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET dice_wins = dice_wins + 1", (winner.id,))

    conn.commit()
    conn.close()

    await ctx.send(f"🎉 {winner.mention} wins the dice game and earns {amount} VAbux! "
                   f"(Rolls: {challenger.display_name} `{roll_challenger}` vs {challenged.display_name} `{roll_challenged}`)")


# =======================
# Tavern: Dice
# ======================
active_duels = set()

@bot.command()
async def duel(ctx, opponent: discord.Member):
    challenger = ctx.author
    if challenger.id == opponent.id:
        await ctx.send("❌ You can’t duel yourself.")
        return

    if challenger.id in active_duels or opponent.id in active_duels:
        await ctx.send("⚔️ One of you is already in a duel.")
        return

    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    # Check both players exist and are alive
    for uid in [challenger.id, opponent.id]:
        c.execute("SELECT hp FROM players WHERE user_id = ?", (uid,))
        row = c.fetchone()
        if not row:
            await ctx.send("❌ Both players need a character.")
            conn.close()
            return
        if row[0] <= 0:
            await ctx.send("💀 Both players must be alive to duel.")
            conn.close()
            return

    embed = discord.Embed(
        title="⚔️ Duel Challenge",
        description=f"{challenger.mention} challenges {opponent.mention} to a duel!\n\n"
                    f"{opponent.mention}, react with ⚔️ to accept!",
        color=discord.Color.red()
    )
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("⚔️")

    def check(reaction, user):
        return user == opponent and str(reaction.emoji) == "⚔️" and reaction.message.id == msg.id

    try:
        await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("⌛ Duel invite expired.")
        return

    # Lock players
    active_duels.update([challenger.id, opponent.id])

    def get_stat(uid, stat):
        c.execute(f"SELECT {stat} FROM players WHERE user_id = ?", (uid,))
        return c.fetchone()[0]

    def get_class(uid):
        c.execute("SELECT class FROM players WHERE user_id = ?", (uid,))
        return c.fetchone()[0]

    def get_effective(uid, stat):
        return get_stat(uid, stat) + get_gear_bonus(uid, stat)

    def get_gear_bonus(uid, stat):
        c.execute("SELECT rarity FROM inventory WHERE user_id = ? AND equipped = 1", (uid,))
        rows = c.fetchall()
        bonus = 0
        for row in rows:
            rarity = row[0]
            bonus += {
                "Common": 0,
                "Rare": 1,
                "Epic": 2,
                "Legendary": 3
            }.get(rarity, 0)
        return bonus

    def calculate_damage(uid, stat, luck):
        base = random.randint(5, 10)
        crit_chance = 5 + luck * 2
        crit = random.randint(1, 100) <= crit_chance
        return (base + stat * 2) * (2 if crit else 1), crit

    def calculate_dodge(uid, dex, opponent_luck):
        dodge_chance = 5 + dex - int(opponent_luck * 0.5)
        return random.randint(1, 100) <= max(5, min(90, dodge_chance))

    def hp_bar(current, maxhp, emoji_full, emoji_empty):
        ratio = current / maxhp
        bars = int(ratio * 10)
        return emoji_full * bars + emoji_empty * (10 - bars)

    # Get stat mapping
    class_stat_map = {
        "Warrior": "strength",
        "Mage": "magic",
        "Rogue": "dexterity"
    }

    # Init duelist stats
    duelists = {
        challenger.id: {
            "user": challenger,
            "hp": 100,
            "stat": get_effective(challenger.id, class_stat_map[get_class(challenger.id)]),
            "dex": get_effective(challenger.id, "dexterity"),
            "luck": get_effective(challenger.id, "luck")
        },
        opponent.id: {
            "user": opponent,
            "hp": 100,
            "stat": get_effective(opponent.id, class_stat_map[get_class(opponent.id)]),
            "dex": get_effective(opponent.id, "dexterity"),
            "luck": get_effective(opponent.id, "luck")
        }
    }

    turn = challenger.id
    while all(d["hp"] > 0 for d in duelists.values()):
        attacker = duelists[turn]
        defender_id = opponent.id if turn == challenger.id else challenger.id
        defender = duelists[defender_id]

        attacker_bar = hp_bar(attacker["hp"], 100, "🟩", "⬛")
        defender_bar = hp_bar(defender["hp"], 100, "🟥", "⬛")

        embed = discord.Embed(title="🤺 Duel Round")
        embed.add_field(name=f"{attacker['user'].display_name} HP", value=attacker_bar, inline=False)
        embed.add_field(name=f"{defender['user'].display_name} HP", value=defender_bar, inline=False)
        await ctx.send(embed=embed)

        await asyncio.sleep(2)

        if calculate_dodge(defender_id, defender["dex"], attacker["luck"]):
            result = f"💨 {defender['user'].mention} dodged the attack!"
        else:
            dmg, crit = calculate_damage(turn, attacker["stat"], attacker["luck"])
            defender["hp"] -= dmg
            result = f"⚔️ {attacker['user'].mention} hit {defender['user'].mention} for {dmg} damage"
            if crit:
                result += " **(CRIT!)**"
            if defender["hp"] <= 0:
                result += f"\n💀 {defender['user'].mention} has fallen!"

        await ctx.send(result)
        await asyncio.sleep(2)
        turn = defender_id

    winner = challenger if duelists[challenger.id]["hp"] > 0 else opponent
    loser = opponent if winner == challenger else challenger

    c.execute("INSERT INTO stats(user_id, duel_wins) VALUES (?, 1) "
              "ON CONFLICT(user_id) DO UPDATE SET duel_wins = duel_wins + 1", (winner.id,))
    conn.commit()
    conn.close()

    await ctx.send(f"🏆 {winner.mention} wins the duel!")
    active_duels.discard(challenger.id)
    active_duels.discard(opponent.id)

# ==============================
#achievements
# # ==============================
def grant_achievement(c, user_id, name, description):
    c.execute('''
        INSERT OR IGNORE INTO achievements (user_id, name, description, earned_on)
        VALUES (?, ?, ?, datetime('now'))
    ''', (user_id, name, description))

@bot.command()
async def achievements(ctx):
    user_id = ctx.author.id
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    c.execute("SELECT name, description, earned_on FROM achievements WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        await ctx.send("📜 You haven't unlocked any achievements yet.")
        return

    desc = "\n".join([f"🏅 **{name}**\n_{desc}_\n🗓️ {date}" for name, desc, date in rows])
    embed = discord.Embed(title="🎖️ Your Achievements", description=desc[:4000], color=discord.Color.green())
    await ctx.send(embed=embed)

# ==============================
#leaderboard
# # ==============================
@bot.command()
async def leaderboard(ctx):
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()

    categories = {
        "1️⃣": ("xp", "🏆 Top XP Earners", "SELECT user_id, xp FROM players ORDER BY xp DESC LIMIT 10"),
        "2️⃣": ("duel_wins", "⚔️ Most Duel Wins", "SELECT user_id, duel_wins FROM stats ORDER BY duel_wins DESC LIMIT 10"),
        "3️⃣": ("dice_wins", "🎲 Most Dice Wins", "SELECT user_id, dice_wins FROM stats ORDER BY dice_wins DESC LIMIT 10"),
        "4️⃣": ("deaths", "💀 Most Deaths", "SELECT user_id, deaths FROM stats ORDER BY deaths DESC LIMIT 10"),
    }

    emoji_list = list(categories.keys())

    def get_embed(key):
        title, label, query = categories[key]
        c.execute(query)
        rows = c.fetchall()

        if not rows:
            return discord.Embed(title=label, description="No data available.", color=discord.Color.greyple())

        desc = ""
        for i, (uid, value) in enumerate(rows, start=1):
            c.execute("SELECT username, class, level FROM players WHERE user_id = ?", (uid,))
            player = c.fetchone()
            if not player:
                continue
            username, cls, lvl = player
            desc += f"**{i}.** {username} – {cls} Lv.{lvl} – `{value}`\n"

        embed = discord.Embed(title=label, description=desc, color=discord.Color.blue())
        embed.set_footer(text="Use reactions to switch leaderboard views.")
        return embed

    page = "1️⃣"
    msg = await ctx.send(embed=get_embed(page))
    for emoji in emoji_list:
        await msg.add_reaction(emoji)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in categories and reaction.message.id == msg.id

    while True:
        try:
            reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check)
            page = str(reaction.emoji)
            await msg.edit(embed=get_embed(page))
            await msg.remove_reaction(reaction.emoji, ctx.author)
        except asyncio.TimeoutError:
            break

    conn.close()


def get_player_class(user_id):
    conn = sqlite3.connect("brainrot.db")
    c = conn.cursor()
    c.execute("SELECT class FROM players WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None













# =======================
# RUN THE BOT
# =======================

bot.run(TOKEN)
