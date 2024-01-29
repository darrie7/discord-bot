import disnake
from disnake.ext import commands, tasks
from asyncio import gather, to_thread
import pytz
from feedparser import parse
import json
from datetime import datetime, timedelta, time
from table2ascii import table2ascii as t2a, PresetStyle
import traceback
import requests
from lxml import html


class PeppernewsCog(commands.Cog):
    def __init__(self, bot: object) -> None:
        self.bot = bot
        self.task_one.start()
        self.task_two.start()
        
        
    def cog_unload(self) -> None:
        self.task_one.cancel()
        self.task_two.cancel()


    @commands.slash_command(guild_ids=[self.bot._guildid])
    async def db3_remove_entry(self, inter: disnake.ApplicationCommandInteraction, title: str) -> None:
        """
        Add category to database

        Parameters
        ----------
        title: title of media to delete
        """
        if  not self.bot._db3.get(self.bot._query.title.lower() == title.lower()):
            await inter.response.send_message("This title is not in the database", ephemeral=True)
            return
        media = self.bot._db3.get(self.bot._query.title.lower() == title.lower())
        self.bot._db3.remove(doc_ids=[media.doc_id])
        return
        


    @commands.slash_command(guild_ids=[self.bot._guildid])
    async def pepper(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    
    @pepper.sub_command()
    async def add(self,
                    inter: disnake.ApplicationCommandInteraction,
                    category: str,
                    max_price: int
                    ) -> None:
        """
        Add category to database

        Parameters
        ----------
        category: category name on pepper
        max_price: maximum price to filter for
        """
        if self.bot._db4.get(self.bot._query.category == category.lower()):
            await inter.response.send_message("This category is already added", ephemeral=True)
            return
        self.bot._db4.insert({"category": category.lower(), "max_price": max_price})
        await inter.response.send_message(f"{category.title()} has been added", ephemeral=True)

    
    @pepper.sub_command()
    async def remove(self,
                       inter: disnake.ApplicationCommandInteraction,
                       category: str
                       ) -> None:
        """
        Remove an entry

        Parameters
        ----------
        category: category name on pepper
        """
        if  not self.bot._db4.get(self.bot._query.category == category.lower()):
            await inter.response.send_message("This category is not in the database", ephemeral=True)
            return
        media = self.bot._db4.get(self.bot._query.category == category.lower())
        self.bot._db4.remove(doc_ids=[media.doc_id])
        await inter.response.send_message(f"{category.title()} has been removed", ephemeral=True)


    @pepper.sub_command()
    async def database(self,
                       inter: disnake.ApplicationCommandInteraction
                        ) -> None:
        """
        Show all entries in database

        Parameters
        ----------
        """
        output = t2a(
                header=["category", "max_price"],
                body=[ [ x.get("category").title(), x.get("max_price") ] for x in self.bot._db4 ],
                style=PresetStyle.ascii_borderless
                )
        await inter.response.send_message(f"""```{output}```""", ephemeral=True)


    async def pepperasync(self, url: str, pricelimit: int, timedelt: int) -> None:
        r = await to_thread(requests.get, url = url)
        for f in parse(r.text).get("entries"):
            if not (datetime.strptime(f.get("published"), "%a, %d %b %Y %H:%M:%S %z") > (datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Europe/Amsterdam")) - timedelta(seconds = timedelt))):
                break
            if "pepper_merchant" in f and "price" in f.get("pepper_merchant"):
                if (float(f.get("pepper_merchant").get("price").replace("€", "").replace(".","").replace(",", ".")) < float(pricelimit)):
                    title_pep = f"""{f.get("title")}, PRICE: {f.get("pepper_merchant").get("price")}"""
                else:
                    continue
            else:
                title_pep = f.get("title")
            await self.bot.get_channel(679029900299993113).send(embed=disnake.Embed(title = title_pep, description = f"""{html.fromstring(f.get("description")).text_content()[:1500]}...""", url = f.get("link")))
   
        
    @tasks.loop(minutes=15.0)
    async def task_one(self) -> None:
        list_pepper = [ (x.get("category"), x.get("max_price")) for x in self.bot._db4 ]
        await gather(*[self.pepperasync(f"""https://nl.pepper.com/rss/groep/{x[0]}""", x[1], 915) for x in list_pepper])


    @tasks.loop(time=[time(hour=11)])
    async def task_two(self) -> None:
        r = await to_thread(requests.get, 
                            url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json?version=3e6fc15a391103cb8eec35d93d70eab2",
                            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36"}
                            )
        lis = [ x for x in r.json() if x["country"] == "USD" and datetime.strptime(x["date"], "%Y-%m-%dT%H:%M:%S%z").astimezone(tz=pytz.timezone("Europe/Amsterdam")).strftime("%d/%m") == datetime.now().astimezone(tz=pytz.timezone("Europe/Amsterdam")).strftime("%d/%m") ]
        body = list()
        for x in lis:
            body.append([ datetime.strptime(x["date"], "%Y-%m-%dT%H:%M:%S%z").astimezone(tz=pytz.timezone("Europe/Amsterdam")).strftime("%H:%M"), x["title"], x["impact"]])
        output = t2a(
                header=["DateTime", "Title", "Impact"],
                body=body,
                style=PresetStyle.thin_compact
                )
        return await self.bot.get_channel(933858887533232218).send(f"""```{output}```""")

    @task_one.error
    @task_two.error
    async def cog_error_handler(self, error) -> None:
        await self.bot.get_channel(self.bot._test_channelid).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))}```""")
        pass


def setup(bot):
    bot.add_cog(PeppernewsCog(bot))

