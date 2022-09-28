from discord.ext import commands
from dotenv import load_dotenv
import os
import sys
sys.path.append('../')

def setup_bot():
    load_dotenv('../.env')
    bot = commands.Bot(command_prefix='!%^@#')
    token = os.getenv("DISCORD_BOT_TOKEN")
    return bot, token
