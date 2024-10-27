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
from fake_useragent import UserAgent
import sqlite3


class PeppernewsCog(commands.Cog):
    def __init__(self, bot: object) -> None:
        self.bot = bot
        self.db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        self.restart_failed.start()
        self.task_one.start()
        self.task_two.start()
        self.marktplaatssync.start()
        
        
    def cog_unload(self) -> None:
        self.task_one.cancel()
        self.task_two.cancel()
        self.marktplaatssync.cancel()
        self.restart_failed.cancel()


    @commands.slash_command()
    async def pepper(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    @commands.slash_command()
    async def marktplaats(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    @marktplaats.sub_command()
    async def add(self,
                    inter: disnake.ApplicationCommandInteraction,
                    max_price: int, 
                    postcode: str,
                    distance: int, 
                    query: str = "",
                    category_id: str = "",
                    ) -> None:
        """
        Add category to database

        Parameters
        ----------
        postcode: postcode
        max_price: maximum price to filter for
        distance: maximum distance from postcode
        query: search term
        category_id: category id on marktplaats
        """
        db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        with sqlite3.connect(db_path) as conn:
            try:
                cur = conn.cursor()
            except Exception as ex:
                await inter.send(f"connection failed {db_path}", ephemeral=True)
            cur.execute('CREATE TABLE IF NOT EXISTS marktplaats (max_price TEXT, postcode TEXT, distance TEXT, query TEXT, category_id TEXT)')
            cur.execute('INSERT INTO marktplaats VALUES(?, ?, ?, ?, ?)', (str(max_price), postcode, str(distance), query, category_id))
            conn.commit()
        await inter.send(f"query/category has been added", ephemeral=True)

    @marktplaats.sub_command()
    async def database(self,
                       inter: disnake.ApplicationCommandInteraction
                        ) -> None:
        """
        Show all entries in database

        Parameters
        ----------
        """
        db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        with sqlite3.connect(db_path) as conn:
            try:
                cur = conn.cursor()
            except Exception as ex:
                await inter.send(f"connection failed {db_path}", ephemeral=True)
            data = cur.execute('SELECT max_price, postcode, distance, query, category_id FROM marktplaats')
        output = t2a(
                header=["max_price", "postcode", "distance", "query", "category_id"],
                body=[ [ x[0], x[1],x[2],x[3],x[4] ] for x in data ],
                style=PresetStyle.ascii_borderless
                )
        await inter.send(f"""```{output}```""", ephemeral=True)


    
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
        self.bot._db4.insert({"category": category.lower(), "max_price": max_price, "api_point": "pepper"})
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
    async def update(self,
                       inter: disnake.ApplicationCommandInteraction
                       ) -> None:
        """
        Remove an entry

        Parameters
        ----------
        """
        self.bot._db4.update({"api_point": "pepper"})                   
        await inter.response.send_message(f"db has been updated", ephemeral=True)


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
                body=[ [ x.get("category").title(), x.get("max_price") ] for x in self.bot._db4 if x.get("api_point") == "pepper" ],
                style=PresetStyle.ascii_borderless
                )
        await inter.response.send_message(f"""```{output}```""", ephemeral=True)


    async def pepperasync(self, url: str, pricelimit: int, timedelt: int) -> None:
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        r = await to_thread(requests.get, url=url, headers=headers)
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

    @tasks.loop(time=[time(hour=23, minute=1)])
    async def marktplaatssync(self) -> None:
        ua = UserAgent()
        db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        with sqlite3.connect(db_path) as conn:
            try:
                cur = conn.cursor()
            except Exception as ex:
                await self.bot.get_channel(679029900299993113).send(f"connection failed {db_path}", ephemeral=True)
            data = cur.execute('SELECT max_price, postcode, distance, query, category_id FROM marktplaats')
        url_params = [ {'minPrice': 'null', 'maxPrice': '0', 'distance': '13000', 'postcode': '7001KG', 'query': 'tafel'},
                        {'minPrice': 'null', 'maxPrice': '0', 'distance': '13000', 'postcode': '7001KG', 'query': 'bureau'},
                        {'minPrice': 'null', 'maxPrice': '1200', 'distance': '13000', 'postcode': '7001KG', 'query': 'boormachine'},
                        {'minPrice': 'null', 'maxPrice': '0', 'distance': '13000', 'postcode': '7001KG', 'category': '239' },
                        {'minPrice': 'null', 'maxPrice': '0', 'distance': '13000', 'postcode': '7001KG', 'category': '1099' },
                        {'minPrice': 'null', 'maxPrice': '0', 'distance': '13000', 'postcode': '7001KG', 'category': '784' },
                        {'minPrice': 'null', 'maxPrice': '0', 'distance': '13000', 'postcode': '7001KG', 'category': '504' }
                    ]
        for x in data: 
            comp_url = f"https://www.marktplaats.nl/lrp/api/search?attributeRanges[]=PriceCents%3Anull%3A{x[0]}&attributesByKey[]=offeredSince%3AGisteren&distanceMeters={x[2]}&limit=50&offset=0&postcode={x[1]}&l1CategoryId={x[4]}&query={x[3]}&searchInTitleAndDescription=true&sortBy=SORT_INDEX&sortOrder=DECREASING"
            retry = 0
            while retry < 3:
                headers = {'User-Agent': ua.random}
                r = await to_thread(requests.get, url=comp_url, headers=headers)
                if r.status_code == 200:
                    # Parse the JSON data directly from the response
                    data = r.json()
                    for x in data.get('listings'):
                        embedded = disnake.Embed(title = x.get("title"), description = f"""{x.get("categorySpecificDescription")}\n\nLocation:{x.get("location").get("cityName", "")}\nDistance: {x.get("location").get("distanceMeters")} meter""", url = f"""https://marktplaats.nl{x.get("vipUrl")}""")
                        if x.get("pictures", [{'data': None}])[0].get("extraExtraLargeUrl", ""):
                            embedded.set_image(url=x.get("pictures")[0].get("extraExtraLargeUrl"))
                        await self.bot.get_channel(679029900299993113).send(embed=embedded)
                    break
                retry += 1
            else:
                continue
        
   
        
    @tasks.loop(minutes=15.0)
    async def task_one(self) -> None:
        list_pepper = [ (x.get("category"), x.get("max_price")) for x in self.bot._db4 if x.get("api_point") == "pepper" ]
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

    @tasks.loop(minutes=5)
    async def restart_failed(self) -> None:
        errors = []
        if not self.task_one.next_iteration:
            self.task_one.cancel()
            self.task_one.start()
            errors.append("task 2")
        if errors:
            for _ in range(10):
                try:
                    await self.bot.get_channel(793878235066400809).send(f"{', '.join(errors)} errored, hopefully reloading")
                    return
                except Exception as e:
                    pass

    @restart_failed.error
    async def restart_failed_error_handler(self, error) -> None:
        await self.bot.get_channel(793878235066400809).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))[-1500:]}```""")
        self.restart_failed.cancel()
        self.restart_failed.start()
        pass

    @task_one.error
    async def task_one_error_handler(self, error) -> None:
        await self.bot.get_channel(self.bot._test_channelid).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))}```""")
        self.task_one.cancel()
        self.task_one.start()
        pass

    @task_two.error
    async def task_two_error_handler(self, error) -> None:
        await self.bot.get_channel(self.bot._test_channelid).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))}```""")
        self.task_two.cancel()
        self.task_two.start()
        pass

    @marktplaatssync.error
    async def marktplaatssync_error_handler(self, error) -> None:
        await self.bot.get_channel(self.bot._test_channelid).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))}```""")
        self.marktplaatssync.cancel()
        self.marktplaatssync.start()
        pass


def setup(bot):
    bot.add_cog(PeppernewsCog(bot))
