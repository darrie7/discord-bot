from disnake.ext import commands, tasks
import disnake
import random
from table2ascii import table2ascii as t2a, PresetStyle
from asyncio import to_thread, sleep
import requests
import json
import math
from textwrap import wrap
from cryptography.fernet import Fernet

class rpsCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.loopcount1.start()
        self.testing.start()
        self.loopcount2.start()
        

    def cog_unload(self) -> None:
        self.testing.cancel()
        self.loopcount1.cancel()
        self.loopcount2.cancel()

    @tasks.loop(minutes=1)
    async def testing(self):
        await self.bot.get_channel(793878235066400809).send(f'testing: {self.testing.next_iteration}')
        await self.bot.get_channel(793878235066400809).send(f'loopcount1: {self.loopcount1.next_iteration}')
        await self.bot.get_channel(793878235066400809).send(f'loopcount2: {self.loopcount2.next_iteration}')

    @tasks.loop(minutes=1)
    async def loopcount1(self):
        await self.bot.get_channel(793878235066400809).send(f'loopcount1: {self.loopcount1.current_loop+1}')
        if self.loopcount1.current_loop+1 == 4:
            err = int("bdhjsjf")
        return

    @tasks.loop(minutes=3)
    async def loopcount2(self):
        await self.bot.get_channel(793878235066400809).send(f'loopcount2: {self.loopcount2.current_loop+1}')
        return


    # @commands.slash_command(guild_ids=[self.bot._guildid])
    # async def gpt(self, inter: disnake.ApplicationCommandInteraction, temp: float, prompt: str) -> None:
    #     """
    #     ChatGPT
        
    #     Parameters
    #     ----------
    #     temp: something about creativity
    #     prompt: what to ask chatGPT
    #     """
    #     await inter.response.defer()
    #     url = "https://api.openai.com/v1/completions"
    #     Bearer = Fernet(self.bot._enckey).decrypt(b'gAAAAABlIxdkP4ChGUpwNqlg7-r0x1XxJeGwFsIhP2TfIOhZwaz29uf6JTKQQhX6St1ysa8DAagXE2RD1LEicaMK1DBlLx4DXYI1kkn63mMH5D6BJgF6TSr_6sNgjtGE3NfM4t6e9xzwl_K9pkzMzUURIGSBx0wMWQ==').decode()
    #     headers = { "Content-Type": "application/json", "Authorization": f"Bearer {Bearer}"}
    #     data = { "model": "text-davinci-003", "prompt": prompt, "max_tokens": 2048, "temperature": temp }
    #     respon = await to_thread(requests.post, url=url, headers=headers, data=json.dumps(data))
    #     resp = respon.json()['choices'][0]['text']
    #     parts = wrap(resp, 1900, replace_whitespace=False)
    #     for part in parts:
    #         await inter.send(f"```{part}```")

        
    # @commands.slash_command(guild_ids=[self.bot._guildid])
    # async def rps(self, inter: disnake.ApplicationCommandInteraction, hand: commands.option_enum(["Rock", "Paper", "Scissors"])) -> None:
    #     """
    #     Rock Paper Scissors against Wukong

    #     Parameters
    #     ----------
    #     hand: the hand you play (Rock/Paper/Scissors)
    #     """
    #     if not self.bot._db2.search(self.bot._query.Player_id == inter.author.id):
    #         self.bot._db2.insert({"Player_id": inter.author.id, "Player_name": inter.author.display_name, "win": 0, "loss": 0, "draw": 0, "points": 0, "appg": 0})
    #     player = self.bot._db2.get(self.bot._query.Player_id == inter.author.id)
    #     wukong_hand = random.choice(["Rock", "Paper", "Scissors", "Rock", "Paper", "Scissors", "Rock", "Paper", "Scissors", "Rock", "Paper", "Scissors"])
    #     hand_wins = {"Rock": ("Scissors", "SMASHES"), "Paper": ("Rock", "COVERS"), "Scissors": ("Paper", "CUTS")}
    #     if hand == wukong_hand:
    #         result = ("DRAW", "")
    #         player["draw"] += 1
    #     elif hand_wins.get(hand)[0] == wukong_hand:
    #         result = ("YOU WIN", f":{hand.lower()}: {hand_wins.get(hand)[1]} :{wukong_hand.lower()}:")
    #         player["win"] += 1
    #     else:
    #         result = ("YOU LOSE", f":{wukong_hand.lower()}: {hand_wins.get(wukong_hand)[1]} :{hand.lower()}:")
    #         player["loss"] += 1
    #     points = player["win"]*3+player["draw"]
    #     emby = disnake.Embed(title=result[0], description=f"""***Round {player["win"]+player["loss"]+player["draw"]}\n***You used **{hand}**!\nWukong uses **{wukong_hand}**!\n{result[1]}""".replace('paper','newspaper'))
    #     emby.set_footer(text=f"""{inter.author.display_name}'s win/loss/draw is {player["win"]}/{player["loss"]}/{player["draw"]} and has {points} pts""")
    #     await inter.response.send_message(embed=emby)
    #     self.bot._db2.update({"win" : player["win"], "loss": player["loss"], "draw": player["draw"], "points": points, "appg": points/(player["win"]+player["draw"]+player["loss"])}, doc_ids = [player.doc_id])

        
    # @commands.slash_command(guild_ids=[self.bot._guildid])
    # async def rpsleaderboard(self, inter: disnake.ApplicationCommandInteraction) -> None:
    #     """
    #     Leaderboard for Rock Paper Scissors against Wukong

    #     Parameters
    #     ----------
    #     """
    #     def myFunc(e):
    #         sorting = {"Total Points": "points", "Average Points": "appg"}
    #         return e["appg"]
    #     db_list = [entry for entry in self.bot._db2]
    #     db_list.sort(reverse=True, key=myFunc)
    #     output = t2a(
    #             header=["Rank", "Player", "Plays", "Points", "Avg Points per Game"],
    #             body=[ [ x, p["Player_name"], p["win"]+p["loss"]+p["draw"], p["points"], round(p["appg"], 2) ] for x,p in enumerate(db_list, start=1)],
    #             style=PresetStyle.ascii_borderless
    #             )
    #     await inter.response.send_message(f"""```{output}```""")

    # @rps.error
    # @rpsleaderboard.error
    # async def cog_error_handler(self, error):
    #     if isinstance(error, commands.CheckFailure):
    #         pass

def setup(bot):
    bot.add_cog(rpsCog(bot))
