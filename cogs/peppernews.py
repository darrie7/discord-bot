import disnake
from disnake.ext import commands, tasks
from asyncio import gather, to_thread
import pytz
from feedparser import parse
import json
from datetime import datetime, timedelta, time, timezone
from table2ascii import table2ascii as t2a, PresetStyle
import traceback
import requests
from lxml import html
from fake_useragent import UserAgent
import sqlite3
from io import StringIO

def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

MARKTPLAATS_CATEGORIES = { "categories": [  {"name": "antiek-en-kunst", "id": 1},
                                          {"name": "audio-tv-en-foto", "id": 31}, {"name": "auto-kopen", "id": 91},
                                          {"name": "auto-onderdelen", "id": 2600}, {"name": "auto-diversen", "id": 48},
                                          {"name": "boeken", "id": 201}, {"name": "caravans-en-kamperen", "id": 289},
                                          {"name": "cd-s-en-dvd-s", "id": 1744}, {"name": "computers-en-software", "id": 322},
                                          {"name": "contacten-en-berichten", "id": 378}, {"name": "diensten-en-vakmensen", "id": 1098},
                                          {"name": "dieren-en-toebehoren", "id": 395}, {"name": "fietsen-en-brommers", "id": 445},
                                          {"name": "doe-het-zelf-en-verbouw", "id": 239}, {"name": "hobby-en-vrije-tijd", "id": 1099},
                                          {"name": "huis-en-inrichting", "id": 504}, {"name": "huizen-en-kamers", "id": 1032},
                                          {"name": "kinderen-en-baby-s", "id": 565}, {"name": "kleding-dames", "id": 621},
                                          {"name": "kleding-heren", "id": 1776}, {"name": "motoren", "id": 678}, 
                                          {"name": "muziek-en-instrumenten", "id": 728}, {"name": "postzegels-en-munten", "id": 1784},
                                          {"name": "sieraden-tassen-en-uiterlijk", "id": 1826}, {"name": "spelcomputers-en-games", "id": 356},
                                          {"name": "sport-en-fitness", "id": 784}, {"name": "telecommunicatie", "id": 820},
                                          {"name": "tickets-en-kaartjes", "id": 1984}, {"name": "tuin-en-terras", "id": 1847},
                                          {"name": "vacatures", "id": 167}, {"name": "vakantie", "id": 856},
                                          {"name": "verzamelen", "id": 895}, {"name": "watersport-en-boten", "id": 976},
                                          {"name": "witgoed-en-apparatuur", "id": 537}, {"name": "zakelijke-goederen", "id": 1085},
                                          {"name": "diversen", "id": 428}                                      
] }

DB_PATH = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'

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
                    categories_1: str = commands.Param(choices=[z.get("name") for z in MARKTPLAATS_CATEGORIES.get("categories")[:20]], default="" ),
                    categories_2: str = commands.Param(choices=[z.get("name") for z in MARKTPLAATS_CATEGORIES.get("categories")[20:]], default="" ),
                    subcategory_id: str = ""
                    ) -> None:
        """
        Add category to database

        Parameters
        ----------
        postcode: postcode
        max_price: maximum price to filter for
        distance: maximum distance from postcode
        query: search term
        categories_1: category on marktplaats
        categories_2: category on marktplaats
        subcategory_id: subcategory id on marktplaats
        """
        category_id = next((z.get("id") for z in MARKTPLAATS_CATEGORIES.get("categories") if z.get('name') in categories_1 or z.get('name') in categories_2), "")
        db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        with sqlite3.connect(db_path) as conn:
            try:
                cur = conn.cursor()
            except Exception as ex:
                await inter.send(f"connection failed {db_path}", ephemeral=True)
            cur.execute('CREATE TABLE IF NOT EXISTS marktplaats (id INTEGER PRIMARY KEY AUTOINCREMENT, max_price TEXT, postcode TEXT, distance TEXT, query TEXT, category_id TEXT, subcategory_id TEXT)')
            cur.execute('INSERT INTO marktplaats (max_price, postcode, distance, query, category_id, subcategory_id) VALUES (?, ?, ?, ?, ?, ?)', (str(max_price), postcode, str(distance), query, category_id, subcategory_id))
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
        await inter.response.defer()
        db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = dict_factory
            try:
                cur = conn.cursor()
            except Exception as ex:
                await inter.send(f"connection failed {db_path}", ephemeral=True)
            data = cur.execute('SELECT id, max_price, postcode, distance, query, category_id, subcategory_id FROM marktplaats')
        output = t2a(
                header=["id", "max_price", "postcode", "distance", "query", "category_id", "category_name", "subcategory_id"],
                body=[ [ x.get("id"), x.get("max_price"), x.get("postcode"), x.get("distance"), x.get("query"), x.get("category_id"), next((z.get("name") for z in MARKTPLAATS_CATEGORIES.get("categories") if x.get("category_id") is not None and x.get("category_id").isdigit() and int(x.get("category_id")) == z.get("id")), None), x.get("subcategory_id") ] for x in data ],
                style=PresetStyle.ascii_borderless
                )
        mystring = StringIO(output)
        my_file = disnake.File(mystring, filename="db.txt")
        await inter.send(file=my_file, ephemeral=True)

    @marktplaats.sub_command()
    async def remove_db(self,
                       inter: disnake.ApplicationCommandInteraction
                        ) -> None:
        """
        Show all entries in database

        Parameters
        ----------
        """
        db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = dict_factory
            try:
                cur = conn.cursor()
            except Exception as ex:
                await inter.send(f"connection failed {db_path}", ephemeral=True)
                return
            cur.execute('DROP TABLE IF EXISTS marktplaats')
            conn.commit() 
        await inter.send(f"""```db removed```""", ephemeral=True)

    @marktplaats.sub_command()
    async def delete(self,
                       inter: disnake.ApplicationCommandInteraction,
                        id: int
                        ) -> None:
        """
        Show all entries in database

        Parameters
        ----------
        id: id of the database entry (not category id)
        """
        db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = dict_factory
            try:
                cur = conn.cursor()
            except Exception as ex:
                await inter.send(f"connection failed {DB_PATH}", ephemeral=True)
                return
            cur.execute('DELETE FROM marktplaats WHERE id = ?', (id,))
            conn.commit() 
        await inter.send(f"""```entry with id = {id} deleted```""", ephemeral=True)


    
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

        db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        with sqlite3.connect(db_path) as conn:
            try:
                cur = conn.cursor()
            except Exception as ex:
                await inter.send(f"connection failed {db_path}", ephemeral=True)
            cur.execute('CREATE TABLE IF NOT EXISTS pepper (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, max_price TEXT)')
            cur.execute('INSERT INTO pepper (category, max_price) VALUES (?, ?)', (category, str(max_price)))
            conn.commit()
        await inter.send(f"query/category has been added", ephemeral=True)
                        
        # if self.bot._db4.get(self.bot._query.category == category.lower()):
        #     await inter.response.send_message("This category is already added", ephemeral=True)
        #     return
        # self.bot._db4.insert({"category": category.lower(), "max_price": max_price, "api_point": "pepper"})
        # await inter.response.send_message(f"{category.title()} has been added", ephemeral=True)

    
    @pepper.sub_command()
    async def delete(self,
                       inter: disnake.ApplicationCommandInteraction,
                        id: int
                        ) -> None:
        """
        Show all entries in database

        Parameters
        ----------
        id: id of the database entry (not category id)
        """
        db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = dict_factory
            try:
                cur = conn.cursor()
            except Exception as ex:
                await inter.send(f"connection failed {DB_PATH}", ephemeral=True)
                return
            cur.execute('DELETE FROM pepper WHERE id = ?', (id,))
            conn.commit() 
        await inter.send(f"""```entry with id = {id} deleted```""", ephemeral=True)
                            
    # async def remove(self,
    #                    inter: disnake.ApplicationCommandInteraction,
    #                    category: str
    #                    ) -> None:
    #     """
    #     Remove an entry

    #     Parameters
    #     ----------
    #     category: category name on pepper
    #     """
    #     if  not self.bot._db4.get(self.bot._query.category == category.lower()):
    #         await inter.response.send_message("This category is not in the database", ephemeral=True)
    #         return
    #     media = self.bot._db4.get(self.bot._query.category == category.lower())
    #     self.bot._db4.remove(doc_ids=[media.doc_id])
    #     await inter.response.send_message(f"{category.title()} has been removed", ephemeral=True)

    # @pepper.sub_command()
    # async def update(self,
    #                    inter: disnake.ApplicationCommandInteraction
    #                    ) -> None:
    #     """
    #     Remove an entry

    #     Parameters
    #     ----------
    #     """
    #     self.bot._db4.update({"api_point": "pepper"})                   
    #     await inter.response.send_message(f"db has been updated", ephemeral=True)


    @pepper.sub_command()
    async def database(self,
                       inter: disnake.ApplicationCommandInteraction
                        ) -> None:
        """
        Show all entries in database

        Parameters
        ----------
        """

        await inter.response.defer()
        db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = dict_factory
            try:
                cur = conn.cursor()
            except Exception as ex:
                await inter.send(f"connection failed {db_path}", ephemeral=True)
            data = cur.execute('SELECT id, category, max_price FROM pepper')
        output = t2a(
                header=["id", "category", "max_price"],
                body=[ [ x.get("id"), x.get("category").title(), x.get("max_price")] for x in data ],
                style=PresetStyle.ascii_borderless
                )
        mystring = StringIO(output)
        my_file = disnake.File(mystring, filename="db.txt")
        await inter.send(file=my_file, ephemeral=True)
                            
        # output = t2a(
        #         header=["category", "max_price"],
        #         body=[ [ x.get("category").title(), x.get("max_price") ] for x in self.bot._db4 if x.get("api_point") == "pepper" ],
        #         style=PresetStyle.ascii_borderless
        #         )
        # await inter.response.send_message(f"""```{output}```""", ephemeral=True)


    async def pepperasync(self, url: str, pricelimit: int, timedelt: int) -> list[dict]:
        entries = []
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        r = await to_thread(requests.get, url=url, headers=headers)
        for f in parse(r.text).get("entries"):
            if not (datetime.strptime(f.get("published"), "%a, %d %b %Y %H:%M:%S %z") > (datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Europe/Amsterdam")) - timedelta(seconds = timedelt))):
                break
            if float(f.get("pepper_merchant", {"price": "€0"}).get("price", "€0").replace("€", "").replace(".","").replace(",", ".")) < float(pricelimit):
                entries.append(f)
        return entries
            # if "pepper_merchant" in f and "price" in f.get("pepper_merchant"):
            #     if (float(f.get("pepper_merchant").get("price").replace("€", "").replace(".","").replace(",", ".")) < float(pricelimit)):
            #         title_pep = f"""{f.get("title")}, PRICE: {f.get("pepper_merchant").get("price")}"""
            #     else:
            #         continue
            # else:
            #     title_pep = f.get("title")
            # await self.bot.get_channel(679029900299993113).send(embed=disnake.Embed(title = title_pep, description = f"""{html.fromstring(f.get("description")).text_content()[:1500]}...""", url = f.get("link")))

    @tasks.loop(time=[time(hour=1, minute=1, tzinfo=timezone(datetime.now(pytz.timezone("Europe/Amsterdam")).utcoffset()))])
    async def marktplaatssync(self) -> None:
        ua = UserAgent()
        db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = dict_factory
                cur = conn.cursor()
                data = cur.execute('SELECT max_price, postcode, distance, query, category_id, subcategory_id FROM marktplaats')
        except Exception as ex:
            await self.bot.get_channel(679029900299993113).send(f"connection failed {db_path}")
            return

        listings = []
        for x in data: 
            comp_url = f"https://www.marktplaats.nl/lrp/api/search?attributeRanges[]=PriceCents%3Anull%3A{x.get('max_price','')}&attributesByKey[]=offeredSince%3AGisteren&distanceMeters={x.get('distance','')}&limit=50&offset=0&postcode={x.get('postcode','')}&l1CategoryId={x.get('category_id','')}&l2CategoryId={x.get('subcategory_id','')}&query={x.get('query','')}&searchInTitleAndDescription=true&sortBy=SORT_INDEX&sortOrder=DECREASING"
            for _ in range(3):
                headers = {'User-Agent': ua.random}
                r = await to_thread(requests.get, url=comp_url, headers=headers)
                if r.status_code == 200:
                    # Parse the JSON data directly from the response
                    data_response = r.json()
                    listings.extend(data_response.get('listings', []))
                    break
        unique_listings_id = set()
        unique_listings = [x for x in listings if not (x['itemId'] in unique_listings_id or unique_listings_id.add(x['itemId']))]
        for listing in unique_listings:
            embedded = disnake.Embed(title = f"""{listing.get("title")} - PRICE: €{listing.get("priceInfo", {"priceCents": 0}).get("priceCents", 0)/100}""", description = f"""{listing.get("categorySpecificDescription")}\n\nLocation:{listing.get("location").get("cityName", "")}\nDistance: {listing.get("location").get("distanceMeters")} meter""", url = f"""https://marktplaats.nl{listing.get("vipUrl")}""")
            if listing.get("pictures", [{'data': None}])[0].get("extraExtraLargeUrl", ""):
                embedded.set_image(url=listing.get("pictures")[0].get("extraExtraLargeUrl"))
            await self.bot.get_channel(679029900299993113).send(embed=embedded)
            
        
    @tasks.loop(minutes=15.0)
    async def task_one(self) -> None:
        ua = UserAgent()
        db_path = '/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/sqlite3.db'
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = dict_factory
                cur = conn.cursor()
                data = cur.execute('SELECT category, max_price FROM pepper')
        except Exception as ex:
            await self.bot.get_channel(679029900299993113).send(f"connection failed {db_path}")
            return
        listings = []
        list_of_list_of_entries = await gather(*[self.pepperasync(f"""https://nl.pepper.com/rss/groep/{x.get("category")}""", x.get("max_price"), 915) for x in data], return_exceptions=True)
        filtered_list_of_list_of_entries = list(filter(lambda x: not isinstance(x, Exception), list_of_list_of_entries))
        for list_of_entries in filtered_list_of_list_of_entries:
            listings.extend(list_of_entries)
        unique_listings_id = set()
        unique_listings = [x for x in listings if not (x['guid'] in unique_listings_id or unique_listings_id.add(x['guid']))]
        for listing in unique_listings:
            title_pep = f"""{listing.get("title")} - PRICE: {listing.get("pepper_merchant", {"price": "???"}).get("price", "???")}"""
            await self.bot.get_channel(679029900299993113).send(embed=disnake.Embed(title = title_pep, description = f"""{html.fromstring(listing.get("description")).text_content()[:1500]}...""", url = listing.get("link")))
            

        # listings = []
        # list_pepper = [ (x.get("category"), x.get("max_price")) for x in self.bot._db4 if x.get("api_point") == "pepper" ]
        # list_of_list_of_entries = await gather(*[self.pepperasync(f"""https://nl.pepper.com/rss/groep/{x[0]}""", x[1], 915) for x in list_pepper], return_exceptions=True)
        # filtered_list_of_list_of_entries = list(filter(lambda x: not isinstance(x, Exception), list_of_list_of_entries))
        # for list_of_entries in filtered_list_of_list_of_entries:
        #     listings.extend(list_of_entries)
        # unique_listings_id = set()
        # unique_listings = [x for x in listings if not (x['guid'] in unique_listings_id or unique_listings_id.add(x['guid']))]
        # for listing in unique_listings:
        #     title_pep = f"""{listing.get("title")} - PRICE: {listing.get("pepper_merchant", {"price": "???"}).get("price", "???")}"""
        #     await self.bot.get_channel(679029900299993113).send(embed=disnake.Embed(title = title_pep, description = f"""{html.fromstring(listing.get("description")).text_content()[:1500]}...""", url = listing.get("link")))
            

    @tasks.loop(time=[time(hour=12, tzinfo=timezone(datetime.now(pytz.timezone("Europe/Amsterdam")).utcoffset()))])
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
