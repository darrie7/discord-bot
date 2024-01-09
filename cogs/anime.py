from lib2to3.pgen2.token import OP
from nis import cat
import disnake
from disnake.ext import commands, tasks
from asyncio import gather, to_thread, sleep
from bs4 import BeautifulSoup
import pytz
from feedparser import parse
import json
from datetime import datetime, timedelta, time
from table2ascii import table2ascii as t2a, PresetStyle
import traceback
import os
from os.path import join, dirname
from dotenv import load_dotenv
from typing import Optional
import requests
from cryptography.fernet import Fernet
import re


class Dropdown(disnake.ui.Select):
    def __init__(self, opt: list[object], min_val: int = 1, max_val: int = 1, placehold: Optional[str] = None) -> None:

        # Set the options that will be presented inside the dropdown


        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder=placehold,
            min_values=min_val,
            max_values=max_val,
            options=opt
        )

    async def callback(self, interaction: disnake.MessageInteraction) -> None:
        await interaction.response.send_message(components = [disnake.ui.Button(label="Your Torrent", url=self.values[0])], ephemeral=True)
        #await interaction.response.send_message(self.vals[int(self.values[0])][0], ephemeral=True)
        #await interaction.send(self.vals[int(self.values[0])][1], ephemeral=True)


class ViewButton(disnake.ui.Button):
    def __init__(self, link: Optional[str] = None, my_label: Optional[str] = None, my_custom_id: Optional[str] = None, button_style: Optional[object] = disnake.ButtonStyle.primary) -> None:
        super().__init__(
            style=button_style,
            label=my_label,
            url=link,
            custom_id=my_custom_id
        )


class TheView(disnake.ui.View):
    def __init__(self, viewcomponents: list[object]) -> None:
        super().__init__()

        # Adds the dropdown to our view object.
        for comp in viewcomponents:
            self.add_item(comp)


class AnimeStuff:
    def __init__(self, bot: object, anime: dict) -> None:
        self.bot = bot
        self.anime = anime
        self.token = bot.token


    async def url_shortener(self, url: str) -> Optional[str]:
        api_url = "http://tinyurl.com/api-create.php"
        response = await to_thread(requests.get, url=api_url, params=dict(url=url))
        if response.ok:
            return response.text.strip()
        return Exception

    async def filterlist(self) -> Optional[dict]:
        if self.anime.get("notes") is None:
            self.anime["notes"] = f"""{{'lastdl': {self.anime.get("progress")}, 'syn': [], 'epoffset': 0, 'synoffset': [] }}"""
            query = f"""query {{ Media (id:{self.anime.get('media').get('id')}, type: ANIME) {{mediaListEntry {{notes}}, relations {{edges {{relationType, node {{title {{romaji}}, relations {{edges {{relationType, node {{seasonInt, format, episodes }} }} }} }} }} }} }} }}"""
            i = 0
            while i < 5:
                spanime = await send2graphql(query, self.token, True)
                if not spanime and not spanime.get("data", {}) and not spanime.get("data", {}).get("Media", {}) and not spanime.get("data", {}).get("Media", {}).get("relations", {}) and not spanime.get("data", {}).get("Media", {}).get("relations", {}).get("edges", []):
                    i += 1
                    await sleep(2)
                    if i == 3:
                        break
                else:     
                    data = spanime.get("data", {}).get("Media", {}).get("relations", {}).get("edges", [])
                    for relation in data:
                        if relation.get("relationType") == "ADAPTATION":
                            title = relation.get("node").get("title").get("romaji")
                            related_data = relation.get("node", {}).get("relations", {}).get("edges", [])
                            episodes = 0
                            for related in related_data:
                                node = related.get("node", {})
                                if related.get("relationType") == "ADAPTATION" and node.get("format") == "TV" and node.get("seasonInt") < self.anime.get('media').get('seasonInt'):
                                    episodes += related.get("node", {}).get("episodes")
                            self.anime["notes"] = f"""{{'lastdl': {self.anime.get("progress")}, 'syn': [], 'epoffset': {episodes}, 'synoffset': ['{re.sub(r"[^a-zA-Z0-9-_ ]", "", title)}'] }}"""
                            break
                    break
        if ( "ignore" in self.anime.get("notes").lower()) or (json.loads(self.anime.get("notes").replace("\'", "\"")).get("lastdl") > self.anime.get("progress") ):
            return None
        if self.anime.get("media").get("nextAiringEpisode") is None:
            return self.anime
        if ( self.anime.get("media").get("nextAiringEpisode").get("episode") - self.anime.get("progress") ) < 2:
            return None
        return self.anime

    async def search_gen(self) -> dict:
        self.anime["notes"] = json.loads(self.anime.get("notes").replace("\'", "\""))
        '''title search'''
        search = [ self.anime.get("media").get("title").get("romaji"), self.anime.get("media").get("title").get("english") ]
        if self.anime.get("notes").get("syn"):
            search.extend(self.anime.get("notes").get("syn"))
        search.extend(self.anime.get("media").get("synonyms"))
        search = [ s for s in search if s and s.isascii() ]
        '''for z in [("season ", "s"), (": ", " - "), (": ", " "), ("-"," ")]:'''
        for z in [(": ", " - "), (": ", " "), ("-"," ")]:
            search.extend([" - ".join([a.lower().replace(z[0], z[1]) for a in title.split(" - ")]) for title in search if z[0] in title.lower()])
        self.anime["search"] = list(dict.fromkeys(search))
        '''episode search'''
        # Regular expression patterns to match season indicators
        season_patterns = [
            re.compile(r'season (\d+)', re.IGNORECASE),
            re.compile(r's(\d+)', re.IGNORECASE),
            re.compile(r'(\d+)(?:st|nd|rd|th) season', re.IGNORECASE),
            re.compile(r'(second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth) season', re.IGNORECASE),
            re.compile(r' (II|III|IV|V|VI|VII|VIII|IX|X)$', re.IGNORECASE),  # Roman numerals
        ]
        # Dictionary to map words to numeric values
        word_roman_to_number = {
            'first': 1,
            'second': 2,
            'third': 3,
            'fourth': 4,
            'fifth': 5,
            'sixth': 6,
            'seventh': 7,
            'eighth': 8,
            'ninth': 9,
            'tenth': 10,
            'ii': 2,
            'iii': 3,
            'iv': 4,
            'v': 5,
            'vi': 6,
            'vii': 7,
            'viii': 8,
            'ix': 9,
            'x': 10,
            '1': 1,
            '2': 2,
            '3': 3,
            '4': 4,
            '5': 5,
            '6': 6,
            '7': 7,
            '8': 8,
            '9': 9,
            '10': 10,
        }
        # Iterate through patterns and check for matches
        season_number = 1
        add_search = []
        for pattern in season_patterns:
            for s in self.anime.get("search"):
                match = pattern.search(s)
                if not match:
                    continue
                matched_substring = match.group(0)
                ani_title = s.replace(matched_substring, "").strip()
                season_text = match.group(1)
                season_text_lower = season_text.lower()
                if season_text_lower in word_roman_to_number:
                    season_number = word_roman_to_number[season_text_lower]
                    add_search.append(f"{ani_title} season {season_number}")
                    add_search.append(f"{ani_title} s{season_number}")
                    if season_number == 2:
                         add_search.append(f"{ani_title} {season_number}nd season")
                         add_search.append(f"{ani_title} second season")
                    elif season_number == 3:
                         add_search.append(f"{ani_title} {season_number}rd season")
                         add_search.append(f"{ani_title} third season")
                    else:
                         add_search.append(f"{ani_title} {season_number}th season")
                         add_search.append(f"{ani_title} {season_text_lower} season")

        self.anime.get("search").extend(add_search)
        self.anime["search"] = list(dict.fromkeys(self.anime.get("search")))
        season_number = int(season_number)
        self.anime["episodesearch"] = [f"""- {self.anime.get("progress")+1:02} """, f"""- {self.anime.get("progress")+1:02}v""", f"""S{season_number:02}E{self.anime.get("progress")+1:02}"""]
        return self.anime

    async def fetch(self, url: str, searchlist: list[str], episodesearch: list[str]) -> str:
        r = await to_thread(requests.get, url=url)
        for x in sorted(parse(r.text).get("entries"), key = lambda v: int(v.get("nyaa_seeders")), reverse=True):
            x = dict(x)
            if any(title.lower() in x.get("title").lower() for title in searchlist) and any(ep.lower() in x.get("title").lower() for ep in episodesearch):
                embed = disnake.Embed(title = x.get("title"))
                embed.set_thumbnail(url=self.anime.get("media").get("coverImage").get("extraLarge"))
                await self.bot.get_channel(679029957728665628).send(await self.url_shortener(f"magnet:?xt=urn:btih:{x['nyaa_infohash']}"))
                await self.bot.get_channel(679029957728665628).send(embed=embed, components = [ disnake.ui.Button(label="Magnet", url=await self.url_shortener(f"magnet:?xt=urn:btih:{x.get('nyaa_infohash')}")),
                                                                                                disnake.ui.Button(label="Torrent", url=x.get("link")), 
                                                                                                disnake.ui.Button(label="Nyaa", url=await self.url_shortener(url.replace(" ","+").replace("page=rss&",""))),  
                                                                                                disnake.ui.Button(label="MyAnimeList", url=f"""https://myanimelist.net/anime/{self.anime.get("media").get("idMal")}"""),
                                                                                                disnake.ui.Button(label="More Torrents", custom_id=await self.url_shortener(url.replace(" ","+")), style=disnake.ButtonStyle.blurple) ])
                self.anime.get("notes")["lastdl"] = self.anime.get("progress")+1
                return f"""ani{self.anime.get("mediaId")}: SaveMediaListEntry (mediaId: {self.anime.get("mediaId")}, notes: \"{self.anime.get("notes")}\") {{id}}\n"""

    async def torrentsearch(self) -> list[str]:
        base_url = "https://nyaa.si/?page=rss&s=seeders&o=desc&c=1_2&f=0&q=-Raze+-60fps+-120fps+-144fps+-480p+-720p+-540p+"
        if self.anime.get("notes").get("epoffset") > 0 and self.anime.get("notes").get("synoffset"):
            responses = await gather(*[ self.fetch(f"""{base_url}({"|".join(f'"{word}"' for word in self.anime.get("episodesearch"))})+{"|".join(f'"{word.replace("&", "%26")}"' for word in self.anime.get("search"))}""", self.anime.get("search"), self.anime.get("episodesearch")),
                                        self.fetch(f"""{base_url}(- {self.anime.get("progress")+self.anime.get("notes").get("epoffset")+1:02})+{"|".join(f'"{word.replace("&", "%26")}"' for word in self.anime.get("notes").get("synoffset"))}""" , self.anime.get("notes").get("synoffset"), [f"""- {self.anime.get("progress")+self.anime.get("notes").get("epoffset")+1:02}"""])
            ] )
        else:
            responses = await gather(*[ self.fetch(f"""{base_url}({"|".join(f'"{word}"' for word in self.anime.get("episodesearch"))})+{"|".join(f'"{word.replace("&", "%26")}"' for word in self.anime.get("search"))}""", self.anime.get("search"), self.anime.get("episodesearch"))])
        return [ resp for resp in responses if resp ]

    async def subfunc(self) -> Optional[list[str]]:
        self.anime = await self.filterlist()
        if not self.anime: 
            return
        self.anime = await self.search_gen()
        return await self.torrentsearch()


async def send2graphql(query: str, token: str, ret: bool = False) -> Optional[str]:
    url = "https://graphql.anilist.co"
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    r = await to_thread(requests.post, url = url, json = {"query": query}, headers = headers)
    if ret is True:
        return r.json()
    else:
        pass


class MyCommandsCog(commands.Cog):
    def __init__(self, bot: object) -> None:
        self.bot = bot
        self.task_one.start()
        self.task_two.start()
        self.task_three.start()
        self.task_four.start()
        self.task_five.start()
        
        
    def cog_unload(self) -> None:
        self.task_one.cancel()
        self.task_two.cancel()
        self.task_three.cancel()
        self.task_four.cancel()
        self.task_five.cancel()

    
    @commands.slash_command(guild_ids=[631502700244107315])
    async def pepper(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    @commands.slash_command(guild_ids=[631502700244107315])
    async def addatabase5(self,
                        inter: disnake.ApplicationCommandInteraction,
                        key: str,
                        value: str) -> None:
        """
        Add key and value to database

        Parameters
        ----------
        key: the key
        value: the value
        """
        self.bot._db5.upsert({"key": key, "value": value}, self.bot._query.key == key)
        await inter.response.send_message(f"{key} has been added or updated", ephemeral=True)



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
            await self.bot.get_channel(679029900299993113).send(embed=disnake.Embed(title = title_pep, description = f"""{BeautifulSoup(f.get("description"), features="html.parser").get_text()[:1500]}...""", url = f.get("link")))
   
        
    @tasks.loop(minutes=15.0)
    async def task_one(self) -> None:
        list_pepper = [ (x.get("category"), x.get("max_price")) for x in self.bot._db4 ]
        # list_pepper = [ ("gratis", 250), ("televisie", 2000), ("nas", 200), ("sim-only", 2000), ("telefoonabonnementen", 2000), ("zonbescherming", 2000), ("externe-opslag", 100) ]
        await gather(*[self.pepperasync(f"""https://nl.pepper.com/rss/groep/{x[0]}""", x[1], 915) for x in list_pepper])


    @tasks.loop(minutes=3)
    async def task_two(self) -> None:
        enctoken = (await to_thread(requests.get, url="https://raw.githubusercontent.com/darrie7/STUFFFF/main/apilist")).text.strip()
        self.bot.token = Fernet(self.bot._enckey).decrypt(enctoken).decode()
        anilist = []
        n = 0
        while n < 5:
            anilist = await send2graphql(f"""query {{ MediaListCollection (userId:178944, type: ANIME, status: CURRENT) {{lists {{entries {{media {{id, seasonInt, idMal, episodes, synonyms, title {{romaji, english}}, nextAiringEpisode {{episode}}, coverImage {{extraLarge}} }}, progress, notes, mediaId }} }} }} }}""", self.bot.token, True)
            if not anilist and not anilist.get("data").get("MediaListCollection") and not anilist.get("data").get("MediaListCollection").get("lists") and not anilist.get("data").get("MediaListCollection").get("lists")[0]:
                n += 1
                await sleep(2)
                if n == 3:
                    return
            else:
                break
        anilist = anilist.get("data").get("MediaListCollection").get("lists")[0].get("entries")
        anilist = list(filter(None, await gather(*[ AnimeStuff(self.bot, anime).subfunc() for anime in anilist ])))
        r = [x for x in anilist if x]
        if not len(r) > 0:
            return
        await send2graphql(f"""mutation {{ {"".join(res[0] for res in r)} }}""", self.bot.token)


    @tasks.loop(minutes=15)
    async def task_three(self) -> None:
        maltoken = self.bot._db5.get(self.bot._query.key == "mal_access").get("value")
        statuses = [('watching', 'CURRENT'), ('completed', 'COMPLETED'), ('plan_to_watch', 'PLANNING'), ('on_hold', 'PAUSED'), ('dropped', 'DROPPED')]
        enctoken = (await to_thread(requests.get, url="https://raw.githubusercontent.com/darrie7/STUFFFF/main/apilist")).text.strip()
        self.token2 = Fernet(self.bot._enckey).decrypt(enctoken).decode()
        anilist = []
        n = 0
        while n < 5:
            anilist = await send2graphql(f"""query {{ MediaListCollection (userId:178944, type: ANIME, sort: UPDATED_TIME_DESC) {{lists {{entries {{media {{idMal, title {{romaji}} }}, progress, status, mediaId, updatedAt }} }} }} }}""", self.token2, True)
            if not anilist and not anilist.get("data").get("MediaListCollection") and not anilist.get("data").get("MediaListCollection").get("lists") and not anilist.get("data").get("MediaListCollection").get("lists")[0]:
                n += 1
                await sleep(2)
                if n == 3:
                    return
            else: 
                break
        anilist = anilist.get("data").get("MediaListCollection").get("lists")[0].get("entries")
        now = datetime.now()
        for x in anilist:
            if ((now - timedelta(minutes=15)) < datetime.fromtimestamp(x.get("updatedAt"))):
                if any(x.get("status") in (stat:=s) for s in statuses):
                    data = {
        'status': {stat[0]},
        'num_watched_episodes': {x.get("progress")} }
                print(data)
                header = {'Authorization': f'Bearer {maltoken}'}
                req = await to_thread(requests.put, url=f"""https://api.myanimelist.net/v2/anime/{x.get("media").get("idMal")}/my_list_status""", headers = header, data = data)
                await self.bot.get_channel(793878235066400809).send(f"task 3: {req.json()}")

    
    @tasks.loop(hours=72)
    async def task_five(self) -> None:
        params = {"client_id": Fernet(self.bot._enckey).decrypt(b'gAAAAABlIw3eLcJmAFdqjAhCHJjq-2sWlw1NxnZKeR5_DDr9wsHnkPXq31CyWwsPItLxB_507xK6DgyzPomh8KvC9zH6OhbEdP5corItvLq7z00HOfZeQmqdFZWz-1cIZFegXXC-0k7N').decode(),
    "client_secret": Fernet(self.bot._enckey).decrypt(b'gAAAAABlIw5m_REDMeXuwvQVPHmCeHPV3MOfSjsFKYFpXlQIBmmBE9kWQTGqM8wlsw-UQq8X-E9fMpLFAiJmbwMQScaz2-Q9syj5RlnRUCL9jP7Rpn1TufI1JADvq4obcGF99UpPPvyTFPLe9kS8IjAeZIY0mEu4fj2NUHqJnKRAOZCLaAGO73I=').decode(),
    "grant_type": "refresh_token",
    "refresh_token": self.bot._db5.get(self.bot._query.key == "mal_refresh").get("value")}
        myreq = await to_thread(requests.post, url="https://myanimelist.net/v1/oauth2/token", data = params)
        await self.bot.get_channel(793878235066400809).send(f"task 5:{myreq.json()}")
        self.bot._db5.upsert({"value": myreq.json().get("access_token")}, self.bot._query.key == "mal_access")
        self.bot._db5.upsert({"value": myreq.json().get("refresh_token")}, self.bot._query.key == "mal_refresh")
            
            
    @tasks.loop(time=[time(hour=11)])
    async def task_four(self) -> None:
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
        
        
    @task_four.error
    @task_one.error
    @task_two.error
    @task_three.error
    @task_five.error
    async def cog_error_handler(self, error) -> None:
        await self.bot.get_channel(793878235066400809).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))}```""")
        pass


    @commands.Cog.listener("on_button_click")
    async def button_listener(self, inter: disnake.MessageInteraction) -> None:
        if "tinyurl" not in inter.component.custom_id:
            return

        # And thus, we end up with only buttons sent by command `send_button`.
        # At this point, this listener is practically identical to the callback of a view button.

        await inter.response.defer(with_message=True, ephemeral=True)
        r = await to_thread(requests.get, url = inter.component.custom_id)
        embed = disnake.Embed()
        comps = list()
        for idx, x in enumerate(sorted(parse(r.text).get("entries"), key = lambda v: int(v.get("nyaa_seeders")), reverse=True)[:min(len(parse(r.text).get("entries")), 5)], start=1):
            embed.add_field(name=f"""{idx}: {x.get("title")}""", value=f"""Seeders: {x.get("nyaa_seeders")} - Size: {x.get("nyaa_size")}""", inline=False)
            comps.append(disnake.ui.Button(label=f"""{idx}""", url=await AnimeStuff(self.bot, {}).url_shortener(f"magnet:?xt=urn:btih:{x['nyaa_infohash']}")))
        await inter.send(components=comps, embed=embed)
        return


def setup(bot):
    bot.add_cog(MyCommandsCog(bot))
