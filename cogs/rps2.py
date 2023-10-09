from disnake.ext import commands, tasks
import disnake
import random
from table2ascii import table2ascii as t2a, PresetStyle
from asyncio import to_thread
import requests
import json
import math
from textwrap import wrap
from cryptography.fernet import Fernet

class rps2Cog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.testing.start()
        self.nterm = 0
        

    def cog_unload(self) -> None:
        self.testing.cancel()

    @tasks.loop(minutes=15)
    async def testing(self):
        await self.bot.get_channel(793878235066400809).send("Holy guac it works")
        return


def setup(bot):
    bot.add_cog(rps2Cog(bot))
