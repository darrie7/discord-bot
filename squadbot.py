import disnake
from disnake.ext import commands
from tinydb import TinyDB, Query
import os
from os.path import join, dirname
from dotenv import load_dotenv


dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

TOKEN = os.environ.get("TOKEN")


initial_extensions = ['cogs.squads',
                      'cogs.owner'
                      ]


intents = disnake.Intents.default()
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="-",case_insensitive=True, intents=intents, sync_commands_debug=True, help_command=None)
bot._db = TinyDB('db.json')
bot._query = Query()

@bot.event
async def on_ready():
    print("ready")

for extension in initial_extensions:
        bot.load_extension(extension)
        
bot.run(TOKEN, reconnect=True)
