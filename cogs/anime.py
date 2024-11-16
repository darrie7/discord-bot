import disnake
from disnake.ext import commands, tasks
from asyncio import gather, to_thread, sleep
from feedparser import parse
import json
from datetime import datetime, timedelta
import traceback
from typing import Optional
import requests
from cryptography.fernet import Fernet
import re
import string
import random
# from deluge_client import DelugeRPCClient


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
        self.host = bot.host
        # self.deluge_user = bot.deluge_user
        self.deluge_passwd = bot.deluge_passwd


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
                if not spanime.get("data", {"Media": {}}).get("Media", {"relations": {}}).get("relations", {"edges": []}).get("edges", []):
                    i += 1
                    await sleep(2)
                    if i == 3:
                        break
                else:     
                    syn = []
                    data = spanime.get("data", {"Media": {}}).get("Media", {"relations": {}}).get("relations", {"edges": []}).get("edges", [])
                    if data == []:
                        # syn.append(re.sub(r'[^a-zA-Z0-9-_ ]', '', self.my_func(self.anime.get("media").get("title").get("romaji"))))
                        self.anime["notes"] = f"""{{'lastdl': {self.anime.get("progress")}, 'syn': {syn}, 'epoffset': 0, 'synoffset': [] }}"""
                        break
                    for relation in data:
                        if relation.get("relationType") == "ADAPTATION":
                            title = re.sub(r'[^a-zA-Z0-9-_ ]', '', self.my_func(r'(?<=[a-zA-Z])[^a-zA-Z0-9 ](?=[a-zA-Z])', relation.get("node").get("title").get("romaji")))
                            # title = relation.get("node").get("title").get("romaji").replace("\'", "").replace("\"", "").replace(",", "")
                            related_data = relation.get("node", {"relations": {}}).get("relations", {"edges": []}).get("edges", [])
                            episodes = 0
                            for related in related_data:
                                node = related.get("node", {})
                                if related.get("relationType") == "ADAPTATION" and node.get("format") == "TV" and node.get("seasonInt") < self.anime.get('media').get('seasonInt'):
                                    episodes += related.get("node", {}).get("episodes")
                            if episodes == 0:
                                syn.append(title)
                            self.anime["notes"] = f"""{{'lastdl': {self.anime.get("progress")}, 'syn': {syn}, 'epoffset': {episodes}, 'synoffset': ["{title}"] }}"""
                            break
                    break
        if ( "ignore" in self.anime.get("notes").lower()) or (json.loads(self.anime.get("notes").replace("\'", "\"")).get("lastdl") > self.anime.get("progress") ):
            return None
        if self.anime.get("media").get("nextAiringEpisode") is None:
            return self.anime
        if ( self.anime.get("media").get("nextAiringEpisode").get("episode") - self.anime.get("progress") ) < 2:
            return None
        return self.anime

    def my_func(self, regex, s):
        pattern = re.compile(regex)
        match = pattern.search(s)
        if match:
            start, end = match.span()
            new_s = f"{s[:start]} {s[end:]}"
            return self.my_func(regex, new_s)
        if not match:
            return s.strip()

    async def search_gen(self) -> dict:
        self.anime["notes"] = json.loads(self.anime.get("notes", "").replace("\'", "\""))
        '''title search'''
        # search = [ self.anime.get("media").get("title").get("romaji"), self.anime.get("media").get("title").get("english") ]
        search = [ x.replace("'", "").replace('"', "") for x in [self.anime.get("media", {}).get("title", {}).get("romaji", ""), self.anime.get("media", {}).get("title", {}).get("english", "") ] if x ]
        if self.anime.get("notes", {}).get("syn"):
            search.extend(self.anime.get("notes").get("syn"))
        search.extend([ syn.replace("\'", "").replace("\"", "") for syn in self.anime.get("media").get("synonyms") if syn.replace("\'", "").replace("\"", "")[0].isascii()])
        # Iterate through each string in the original search list
        search.extend([ self.my_func(r'(?<=[a-zA-Z])[^a-zA-Z0-9 ](?=[a-zA-Z])', s) for s in search if s.strip() ])
        search.extend( [ re.sub(r'[^a-zA-Z0-9-_ ]', '', self.my_func(r'  ', self.my_func(r'-', s))).strip() for s in search if s and len(s.strip()) > 2 and not s.strip().isdigit() ] )# and s.isascii() 
        '''for z in [("season ", "s"), (": ", " - "), (": ", " "), ("-"," ")]:'''
        # for z in [(": ", " - "), (": ", " "), ("-"," ")]:
        #     search.extend([" - ".join([a.replace(z[0], z[1]) for a in title.split(" - ")]) for title in search if z[0] in title])
        self.anime["search"] = list(dict.fromkeys(search))
        '''episode search'''
        # Regular expression patterns to match season indicators
        season_patterns = [
            re.compile(r' season (\d+)', re.IGNORECASE),
            re.compile(r' s(\d+)', re.IGNORECASE),
            re.compile(r' (\d+)$', re.IGNORECASE),
            re.compile(r' (\d+)(?:st|nd|rd|th) season', re.IGNORECASE),
            re.compile(r' (second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth) season', re.IGNORECASE),
            re.compile(r' (II|III|IV|V|VI|VII|VIII|IX|X)$'),  # Roman numerals
        ]
        # Dictionary to map words to numeric values
        word_roman_to_number = {
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
            'x': 10
        }
        # Iterate through patterns and check for matches
        season_number = 1
        add_search = []
        season_search = []
        for s in self.anime.get("search"):
            match = next((x.search(s) for x in season_patterns if x.search(s)), None)
            if match:
                start, end = match.span()
                ani_title = s[:start].strip() + s[end:].strip()
                season_text = match.group(1).lower()
                season_number = word_roman_to_number.get(season_text, '') if word_roman_to_number.get(season_text, '') else int(season_text)
                add_search.append(ani_title)
                season_search.extend([f" season {season_number}", f" s{season_number}", f" s{season_number:02}", f" - s{season_number:02}", f" {season_number} "])
                if season_number == 2:
                    season_search.extend([f" {season_number}nd season", f" second season"])
                elif season_number == 3:
                    season_search.extend([f" {season_number}rd season", f" third season"])
                else:
                    season_search.extend([f" {season_number}th season", f" {season_text} season"])
                continue
            add_search.append(s)
            # for pattern in season_patterns:
            #     match = pattern.search(s)
            #     if not match:
            #         add_search.append(s)
            #     if match:
            #         start, end = match.span()
            #         ani_title = s[:start].strip() + s[end:].strip()
            #         season_text = match.group(1).lower()
            #         season_number = word_roman_to_number.get(season_text, int(season_text))
            #         add_search.append(ani_title)
            #         season_search.extend([f" season {season_number}", f" s{season_number}", f" s{season_number:02}", f" - s{season_number:02}", f" {season_number} "])
            #         # add_search.append(f"{ani_title} season {season_number}")
            #         # add_search.append(f"{ani_title} s{season_number}")
            #         # add_search.append(f"{ani_title} s{season_number:02}")
            #         # add_search.append(f"{ani_title} - s{season_number:02}")
            #         if season_number == 2:
            #             season_search.extend([f" {season_number}nd season", f" second season"])
            #             # add_search.append(f"{ani_title} {season_number}nd season")
            #             # add_search.append(f"{ani_title} second season")
            #         elif season_number == 3:
            #             season_search.extend([f" {season_number}rd season", f" third season"])
            #             # add_search.append(f"{ani_title} {season_number}rd season")
            #             # add_search.append(f"{ani_title} third season")
            #         else:
            #             season_search.extend([f" {season_number}th season", f" {season_text} season"])
            #             # add_search.append(f"{ani_title} {season_number}th season")
            #             # add_search.append(f"{ani_title} {season_text} season")

        # self.anime.get("search").extend(add_search)
        searches = list(dict.fromkeys(add_search))
        self.anime["search"] = [ s for s in searches if s and s.strip() and len(s.strip()) > 2 and not s.strip().isdigit() ] # and s.isascii() 
        season_number = int(season_number)
        self.anime["seasonsearch"] = list(dict.fromkeys(season_search))
        self.anime["episodesearch"] = [f""" - {self.anime.get("progress")+1:03} """, f""" - {self.anime.get("progress")+1:02} """, f""" - {self.anime.get("progress")+1:03}v""", f""" - {self.anime.get("progress")+1:02}v""", f"""S{season_number:02}E{self.anime.get("progress")+1:03}""", f"""S{season_number:02}E{self.anime.get("progress")+1:02}"""]
        return self.anime

    async def fetch(self, url: str, searchlist: list[str], episodesearch: list[str]) -> str:
        r = await to_thread(requests.get, url=url)
        for x in sorted(parse(r.text).get("entries"), key = lambda v: int(v.get("nyaa_seeders")), reverse=True):
            x = dict(x)
            if any(title.lower() in re.sub(r'[^a-zA-Z0-9-_ ]', '', self.my_func(r'(?<=[a-zA-Z])[^a-zA-Z0-9 ](?=[a-zA-Z])', x.get("title").lower())) for title in searchlist) and any(ep.lower() in re.sub(r'[^a-zA-Z0-9-_ ]', '', self.my_func(r'(?<=[a-zA-Z])[^a-zA-Z0-9 ](?=[a-zA-Z])', x.get("title").lower())) for ep in episodesearch):
                with requests.Session() as s:
                    uri = self.host
                    headers = {'content-type': 'application/json'}
                    for data in [{"method": "auth.login", "params": [self.deluge_passwd]}, {"method": "web.connect", "params": ["58de378ad2f643d78c3e1ea72cbbc719"]}, {"method": "web.connected", "params": []}, {"method": "core.add_torrent_magnet", "params": [f"magnet:?xt=urn:btih:{x.get('nyaa_infohash')}", {"download_location": '/downloads/'}]}]:
                        payload = {
                            'method': data.get("method"),
                            'params': data.get("params"),
                            'id': 1
                        }
                        response = s.post(uri, data=json.dumps(payload), headers=headers)
                        if response.json().get("error"):
                            await self.bot.get_channel(self.bot._test_channelid).send(f"""```{response.json().get("error")}```""")
                            return

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
            responses = await gather(*[ self.fetch(f"""{base_url}{"|".join(f'"{word.replace("&", "%26")}"' for word in self.anime.get("search"))}+{"|".join(f'"{word}"' for word in self.anime.get("seasonsearch"))}+{"|".join(f'"{word}"' for word in self.anime.get("episodesearch"))}""", self.anime.get("search"), self.anime.get("episodesearch")),
                                        self.fetch(f"""{base_url}(- {self.anime.get("progress")+self.anime.get("notes").get("epoffset")+1:02})+{"|".join(f'"{word.replace("&", "%26")}"' for word in self.anime.get("notes").get("synoffset"))}""" , self.anime.get("notes").get("synoffset"), [f"""- {self.anime.get("progress")+self.anime.get("notes").get("epoffset")+1:02}"""])
            ] )
        else:
            responses = await gather(*[ self.fetch(f"""{base_url}{"|".join(f'"{word.replace("&", "%26")}"' for word in self.anime.get("search"))}+{"|".join(f'"{word}"' for word in self.anime.get("seasonsearch"))}+{"|".join(f'"{word}"' for word in self.anime.get("episodesearch"))}""", self.anime.get("search"), self.anime.get("episodesearch"))])
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
        self.task_two.start()
        self.task_three.start()
        self.task_four.start()
        self.task_five.start()
        self.restart_failed.start()
        self.decoder = Fernet(self.bot._enckey)
        self.bot.token = self.decoder.decrypt(b'gAAAAABmBvXouylSxaCLf73YU23aES0icnrji2pYrhlpNsKVAUgj30oV8Ey0h5VeXcl1qLgE1gU6tg6k3IPKSRU46Ijz7VfZjL1U1HZfLHn_SPhBIyJ26qMjTBoYUhMOXtrhRCN9yRHMVbnruYaR4gkNNaHTRBFwN2WveSEiu9SrtYsdxp_48wdoBJxOUoIK_1mpgILKN6a1yPGHsuiWbDkYk9gfp6GRu3Bh7E94dMIj2u_XpE1dwnyBCuDp2OucSH9gqvKG4A5Ewdp70g7WGs1s9rJcjxheKqS7RpYkXUQMRmS9FsVz7INhI0um3BXMqlokYhtEc9anTON341jrs2IXL4x2jpRRhTzimtMcx24lDv981X1m1ykVfkSeZUfD5qa9tIXBpgjVhg2mq2axQiBUhJr2D3cQk1iH-6OSzC-0-ZkswPC69YvfRFSVBU0cE7h6gPuD_1CJWBQXAogJAMVyl78jCPAtjUw8IKKMzvTDy73KAHGbi84DrTs4l04hjIlv44rj-2WYDdEF8BEWk-C8iiq5qL5a3zzHg_xEK_caARlqWByXNPmpds4EZIRLYfjrqAcAKSh8AMAcF0vMQbGw_seeoTDZM0T5MsZzkOrXHScqtkdt6J1FSO6CNUmPKCgCDFJZ2T7FOBBT4RGZ_Tm3lHBuoamI-ts1v5nXoEe2Fmn52I5pl4VIszWinGlZ0g0MHaCpee1hdT-rBLlfuJoP9QErQ2aSQfXN1RP5-oc3CN_TFYv0q3yvQWj_6Ma8Bb3Kd-nK6jhmC1s3Z4bhb0qk3MaBlKkYUH-M76tNHnx2AZQBjRpqf6Gx74ftBg3uz__SQ5qHDXf_FtCKYR1POSWLdTiHmwq0uad69vc2EfKApOXqk-S9aD7P2CtSF_3I43ia3aRid1eJbiSkzHulEElW9oh6p-P7myEZVvSY2BdxDfClcRsRlSLupQGW0Kku9hZnRqptsuY8LPRWRTseGoXiiGYHOl_p0iSjWFYowdKAxRqAhgBfYsNvM0RP_XCTXEdxaititPtEqCikzsePoV6QuU21hdRzwlQj5beZz_aoIHjyE8SyHVZLnXgtvZMOUrSETI9ABTgX4gBIg2L3M3BLoMGSTWZLeZkDa7ZeBkDg3LTtSRMezamoVqzT0LgJxJuKqEfU8KAN67aVYtBs1ymQgOZqKriJkEhtl_Ts7GPYlhw8M9pQt3NnImdMONEQ-C1fh5WWEsJFj5NwJZEVkp1C44LG8o6OZcHmUsWfLZnYrm-PUVnvvCc4_WzQj4B8P8oVZpEkjugttfjy8Ks_7NuZQU_z6Kx9HSJkdsQ94NtRB2ckBqSZ3IlIhPP1ISiXbaggtjNEydhL8pIgwDSKxpMuF6BXdnCRLXX2e405XNkb_LSFZAx4xdVE7yPa-5ZKTqI5JUSmvjX0L7zh4EIE7CtZVYSODt-ReZnJ8DqiYXjeGeuwkfR2ci-n-7F6Smu8_BLwq_rH4enchgOh8Sq-HTx_HheZr0wZ385FKgN4CV_LKortMBc4i1k=').decode()
        self.client_id = self.decoder.decrypt(b'gAAAAABlIw3eLcJmAFdqjAhCHJjq-2sWlw1NxnZKeR5_DDr9wsHnkPXq31CyWwsPItLxB_507xK6DgyzPomh8KvC9zH6OhbEdP5corItvLq7z00HOfZeQmqdFZWz-1cIZFegXXC-0k7N').decode()
        self.client_secret = self.decoder.decrypt(b'gAAAAABlIw5m_REDMeXuwvQVPHmCeHPV3MOfSjsFKYFpXlQIBmmBE9kWQTGqM8wlsw-UQq8X-E9fMpLFAiJmbwMQScaz2-Q9syj5RlnRUCL9jP7Rpn1TufI1JADvq4obcGF99UpPPvyTFPLe9kS8IjAeZIY0mEu4fj2NUHqJnKRAOZCLaAGO73I=').decode()
        # self.bot.host = self.decoder.decrypt(b'gAAAAABlpWObOSHPZsnwbjQWP9MwULDlDRuxFXKPYBFAZS_s6X_Lr620EKMtklKbFRvK1uFNdX6YYUWvrO2gXKLHEDkvERVE3w==').decode()
        # self.bot.deluge_user =  self.decoder.decrypt(b'gAAAAABlIxN9JUKSkB2Ncjq1Na0huIM53UJGIGEb621_We33mUKHkN4uaifSZYp_pfexSEpq6NKI4Iy97KFjthaVbeUm5gPSkA==').decode()
        # self.bot.deluge_passwd = self.decoder.decrypt(b'gAAAAABlIxOc7ZikmiK3gtZK5hvEDFZHAEp3dQurdZl4YoMzfHBZ3eveES_0WY-cqF10fIwPuIDVbawOiCsKFVHaiPs6GQ6s8g==').decode()
        self.bot.host = self.decoder.decrypt(b'gAAAAABmBvixHfgpAN-TBLb04DXf2E1J53zdxQsHevpacEShlPR7oLvwa4-EOAA11alY6Us3w0ZRYOpqt_psAZwepCekQ__WkWJExYHBG4OEebO4TP3Ah70=').decode()
        self.bot.deluge_passwd = self.decoder.decrypt(b'gAAAAABmEvel4VRvjFbNkKvvqWrb3c5Jrngy6JOQZ83JjyDHPXuioI0-xwROYDG7EdQ8Gjpmy-JuCZLdjsIKrZ1V0YF0cBxkiQm10mMU0ScTWBW1EZVJrft5WTe4ZsHf9v6W4C57Kk_luG4BB4wy98mOe9ZxY1bKFDlMYAAy-IH77YUO4MBr2_QtWk7JwOhpF7-Bwctfp00s-3T2Q4QDE5fA-aaOp-dqqKAQUZw44rcMA_3-KdKWjdfkobof8QQoKBQ5cEdrA5JO').decode()
        
        
        
    def cog_unload(self) -> None:
        self.task_two.cancel()
        self.task_three.cancel()
        self.task_five.cancel()
        self.task_four.cancel()
        self.restart_failed.cancel()


    @commands.slash_command()
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
        await inter.response.send_message(f"```{key} has been added or updated```", ephemeral=True)


    @tasks.loop(minutes=5)
    async def task_two(self) -> None:
        anilist = []
        n = 0
        while n < 5:
            anilist = await send2graphql(f"""query {{ MediaListCollection (userId:178944, type: ANIME, status: CURRENT) {{lists {{entries {{media {{id, seasonInt, idMal, episodes, synonyms, title {{romaji, english}}, nextAiringEpisode {{episode}}, coverImage {{extraLarge}} }}, progress, notes, mediaId }} }} }} }}""", self.bot.token, True)
            if not anilist or not anilist.get("data") or not anilist.get("data").get("MediaListCollection") or not anilist.get("data").get("MediaListCollection").get("lists") or not anilist.get("data").get("MediaListCollection").get("lists")[0] or not anilist.get("data").get("MediaListCollection").get("lists")[0].get("entries"):
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


    @tasks.loop(hours=2)
    async def task_four(self) -> None:
        self.bot._db5.update({'value': ''.join(random.choice(string.ascii_letters) for i in range(50))}, self.bot._query.key == "cookies")

    @tasks.loop(minutes=15)
    async def task_three(self) -> None:
        maltoken = self.bot._db5.get(self.bot._query.key == "mal_access").get("value")
        statuses = [('watching', 'CURRENT'), ('completed', 'COMPLETED'), ('plan_to_watch', 'PLANNING'), ('on_hold', 'PAUSED'), ('dropped', 'DROPPED')]
        anilist = []
        n = 0
        while n < 5:
            anilist = await send2graphql(f"""query {{ MediaListCollection (userId:178944, type: ANIME, sort: UPDATED_TIME_DESC) {{lists {{entries {{media {{idMal, title {{romaji}} }}, progress, status, mediaId, updatedAt }} }} }} }}""", self.bot.token, True)
            if not anilist or not anilist.get("data") or not anilist.get("data").get("MediaListCollection") or not anilist.get("data").get("MediaListCollection").get("lists") or not anilist.get("data").get("MediaListCollection").get("lists")[0] or not anilist.get("data").get("MediaListCollection").get("lists")[0].get("entries"):
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
                await self.bot.get_channel(self.bot._test_channelid).send(f"```task 3: {req.json()}```")

    
    @tasks.loop(hours=168)
    async def task_five(self) -> None:
        params = {"client_id": self.client_id,
    "client_secret": self.client_secret,
    "grant_type": "refresh_token",
    "refresh_token": self.bot._db5.get(self.bot._query.key == "mal_refresh").get("value")}
        myreq = await to_thread(requests.post, url="https://myanimelist.net/v1/oauth2/token", data = params)
        await self.bot.get_channel(self.bot._test_channelid).send(f"```task 5:{myreq.json()}```")
        self.bot._db5.upsert({"value": myreq.json().get("access_token")}, self.bot._query.key == "mal_access")
        self.bot._db5.upsert({"value": myreq.json().get("refresh_token")}, self.bot._query.key == "mal_refresh")


    @tasks.loop(minutes=5)
    async def restart_failed(self) -> None:
        errors = []
        if not self.task_five.next_iteration:
            self.task_five.cancel()
            self.task_five.start()
            errors.append("task 5")
        if not self.task_four.next_iteration:
            self.task_four.cancel()
            self.task_four.start()
            errors.append("task 4")
        if not self.task_three.next_iteration:
            self.task_three.cancel()
            self.task_three.start()
            errors.append("task 3")
        if not self.task_two.next_iteration:
            self.task_two.cancel()
            self.task_two.start()
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
    
    @task_two.error
    async def task_two_error_handler(self, error) -> None:
        await self.bot.get_channel(self.bot._test_channelid).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))}```""")
        self.task_two.cancel()
        self.task_two.start()
        pass

    @task_three.error
    async def task_three_error_handler(self, error) -> None:
        await self.bot.get_channel(self.bot._test_channelid).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))}```""")
        self.task_three.cancel()
        self.task_three.start()
        pass

    @task_four.error
    async def task_four_error_handler(self, error) -> None:
        await self.bot.get_channel(self.bot._test_channelid).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))}```""")
        self.task_four.cancel()
        self.task_four.start()
        pass

    @task_five.error
    async def task_five_error_handler(self, error) -> None:
        await self.bot.get_channel(self.bot._test_channelid).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))}```""")
        self.task_five.cancel()
        self.task_five.start()
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
