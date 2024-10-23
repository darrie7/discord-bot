import subprocess
import disnake
from disnake.ext import commands, tasks
from asyncio import to_thread
import requests
from statistics import mean
from math import ceil

class atHomeCog(commands.Cog):
    def __init__(self, bot: object) -> None:
        self.bot = bot
        self.homeip.start()

    def cog_unload(self) -> None:
        self.homeip.cancel()

        
        
    @tasks.loop(minutes=15.0)
    async def homeip(self) -> None:
        # url = 'https://wise.com/rates/history+live?source=EUR&target=PHP&length=30&resolution=hourly&unit=day'
        # url = 'https://wise.com/rates/live?source=EUR&target=PHP&length=1'
        url = 'https://wise.com/rates/history+live?source=EUR&target=PHP&length=7&resolution=daily'
        r = await to_thread(requests.get, url = url)
        wisecurrs =  r.json()
        curr = self.bot._db5.search(self.bot._query.key == 'EURPHP')[0]
        if wisecurrs[-1].get('value') == curr.get('value'):
            return
        self.bot._db5.update({"value": wisecurrs[-1].get('value')}, doc_ids=[curr.doc_id])
        onl = [x.get('value') for x in wisecurrs]
        themean = mean(onl[:-1])
        score = (onl[-1] - themean) / themean
        if ceil(wisecurrs[-1].get('value')*2) != ceil(curr.get('value')*2):
            await self.bot.get_channel(1116887085941530756).send(content=f"""{curr.get('key')} {onl[-1]} | Previous: {wisecurrs[-1].get('value') - curr.get('value'):+.4f} | Weekly: {onl[-1] - themean:+.4f}({abs(score):.2%})  <@141149692531572736>""")
            return
        await self.bot.get_channel(1116887085941530756).send(content=f"""{curr.get('key')} {onl[-1]} | Previous: {wisecurrs[-1].get('value') - curr.get('value'):+.4f} | Weekly: {onl[-1] - themean:+.4f}({abs(score):.2%})""")


def setup(bot):
    bot.add_cog(atHomeCog(bot))
