import discord
from discord.ext import commands
from datetime import datetime
import os
import json
import asyncio
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
CONFIG_FILE = "config.json"
LOG_FILE = "bot_logs.txt"

# Default configuration
DEFAULT_CONFIG = {
    "blocked_words": ["good morning", "gm", "shubh prabhat", "gud morning", "morning"],
    "ignored_users": [],
    "boss_users": [1368236764564553829, 1025027158567043072, 1135951424199606434],
    "responses": {
        "morning_block": "Andha nahi hai, subah ho gayi hai. Bade aaye Good Morning bolne wale 😎",
        "boss_response": "Malik, aap takleef na karein... main bol dunga sabko 😌",
        "mass_mention": "Maan ja, kyun ban khayega 😤"
    },
    "auto_react": True,
    "delete_after": 10  # seconds to delete bot messages
}

def load_config():
    """Load configuration from file or create default"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def log_action(action):
    """Log actions to file"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {action}\n")
    except Exception as e:
        logger.error(f"Failed to log action: {e}")

@bot.event
async def on_ready():
    """Bot startup event"""
    print(f"🤖 Dushman Bot v4 is online as {bot.user}")
    print(f"📊 Connected to {len(bot.guilds)} servers")
    log_action("Bot started and ready.")
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="Good Morning messages 👀")
    )

@bot.event
async def on_message(message):
    """Handle incoming messages"""
    if message.author == bot.user:
        return

    config = load_config()
    content = message.content.lower()

    # Check for blocked words
    if any(word in content for word in config["blocked_words"]):
        if message.author.id in config["boss_users"]:
            response = await message.channel.send(f"{message.author.mention} {config['responses']['boss_response']}")
            log_action(f"Ignored morning wish from boss: {message.author}")
            
            # Auto-react to boss message
            if config["auto_react"]:
                await message.add_reaction("😌")
                
        elif message.author.id in config["ignored_users"]:
            log_action(f"Ignored user sent: {content}")
            
        else:
            try:
                await message.delete()
                response = await message.channel.send(f"{message.author.mention} {config['responses']['morning_block']}")
                log_action(f"Deleted message: {message.author} said: {content}")
                
                # Delete bot message after specified time
                if config["delete_after"] > 0:
                    await asyncio.sleep(config["delete_after"])
                    await response.delete()
                    
            except discord.Forbidden:
                log_action(f"Permission error trying to delete from {message.author}")
                await message.channel.send(f"{message.author.mention} Delete karne ki permission nahi hai 😔")

    # Check for mass mentions
    if "@everyone" in message.content or "@here" in message.content:
        if message.author.id not in config["boss_users"]:
            response = await message.channel.send(f"{message.author.mention} {config['responses']['mass_mention']}")
            log_action(f"Mass mention detected by {message.author}")
            
            if config["delete_after"] > 0:
                await asyncio.sleep(config["delete_after"])
                await response.delete()

    await bot.process_commands(message)

@bot.command()
async def showlog(ctx):
    """Show recent bot logs"""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as log:
            lines = log.readlines()[-15:]  # Show last 15 lines
            if lines:
                log_content = "".join(lines)
                if len(log_content) > 1900:  # Discord message limit
                    log_content = log_content[-1900:]
                await ctx.send(f"```\n{log_content}\n```")
            else:
                await ctx.send("Log file is empty.")
    except FileNotFoundError:
        await ctx.send("No log file found.")

@bot.command()
async def addword(ctx, *, word):
    """Add a word to blocked list"""
    if ctx.author.id not in load_config()["boss_users"]:
        await ctx.send("Sirf boss hi words add kar sakte hain!")
        return
    
    config = load_config()
    word = word.lower()
    
    if word not in config["blocked_words"]:
        config["blocked_words"].append(word)
        save_config(config)
        await ctx.send(f"Word '{word}' added to blocked list ✅")
        log_action(f"Boss {ctx.author} added word: {word}")
    else:
        await ctx.send(f"Word '{word}' already in blocked list!")

@bot.command()
async def removeword(ctx, *, word):
    """Remove a word from blocked list"""
    if ctx.author.id not in load_config()["boss_users"]:
        await ctx.send("Sirf boss hi words remove kar sakte hain!")
        return
    
    config = load_config()
    word = word.lower()
    
    if word in config["blocked_words"]:
        config["blocked_words"].remove(word)
        save_config(config)
        await ctx.send(f"Word '{word}' removed from blocked list ✅")
        log_action(f"Boss {ctx.author} removed word: {word}")
    else:
        await ctx.send(f"Word '{word}' not found in blocked list!")

@bot.command()
async def listwords(ctx):
    """List all blocked words"""
    config = load_config()
    words = ", ".join(config["blocked_words"])
    await ctx.send(f"**Blocked words:** {words}")

@bot.command()
async def setstatus(ctx, *, status):
    """Set bot status (Boss only)"""
    if ctx.author.id not in load_config()["boss_users"]:
        await ctx.send("Sirf boss hi status change kar sakte hain!")
        return
    
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=status)
    )
    await ctx.send(f"Status changed to: {status} ✅")

@bot.command()
async def stats(ctx):
    """Show bot statistics"""
    config = load_config()
    embed = discord.Embed(title="🤖 Bot Statistics", color=0x00ff00)
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Blocked Words", value=len(config["blocked_words"]), inline=True)
    embed.add_field(name="Boss Users", value=len(config["boss_users"]), inline=True)
    embed.add_field(name="Ignored Users", value=len(config["ignored_users"]), inline=True)
    embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    """Show bot commands"""
    embed = discord.Embed(title="🤖 Dushman Bot Commands", color=0xff0000)
    embed.add_field(name="!showlog", value="Show recent bot logs", inline=False)
    embed.add_field(name="!stats", value="Show bot statistics", inline=False)
    embed.add_field(name="!listwords", value="List all blocked words", inline=False)
    
    embed.add_field(name="**Boss Commands:**", value="", inline=False)
    embed.add_field(name="!addword <word>", value="Add word to blocked list", inline=False)
    embed.add_field(name="!removeword <word>", value="Remove word from blocked list", inline=False)
    embed.add_field(name="!setstatus <status>", value="Change bot status", inline=False)
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found! Use `!help` for available commands.")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("Something went wrong! 😔")

# Health check for hosting platforms
@bot.event
async def on_connect():
    logger.info("Bot connected to Discord!")

# Get token from environment variable (for security)
TOKEN = os.getenv('MTM5NDYwOTI0NzQzNzg1MjcxNA.G4V0rZ.mhM_2CxQwwCJPbxww0U7VlaxxgNwLCQgAxmJBM')

if not TOKEN:
    print("❌ DISCORD_TOKEN environment variable not found!")
    print("Please set your bot token as an environment variable.")
    exit(1)

if __name__ == "__main__":
    bot.run(MTM5NDYwOTI0NzQzNzg1MjcxNA.G4V0rZ.mhM_2CxQwwCJPbxww0U7VlaxxgNwLCQgAxmJBM)
