import os
from lxml import etree
import requests
from disnake.ext import commands, tasks
import disnake
import os
# from bs4 import BeautifulSoup
# from typing import Optional
from asyncio import gather, to_thread, sleep
import datetime
from pexpect import pxssh
from cryptography.fernet import Fernet
import traceback
from random import randrange
import re

def convert_to_int(string):
    if string[-1] == 'K':
        numeric_part = float(string[:-1])  # Remove 'K' and convert to float
        integer_value = int(numeric_part * 1000)  # Convert to integer by multiplying with 1000
        return integer_value
    else:
        return int(string)  # If no 'K', directly convert to integer


class Torrent:
    def __init__(
        self, 
        me: object,
        database_entry: dict,
        ) -> None:

        self.bot = me.bot
        self.s = me.s
        self.db_entry = database_entry
        self.nterm = me.noddeven  % len(me.urls)
        self.urlsT = me.urls
        self.apikeysT = me.apikeys
        self.enckey = me.bot._enckey


    async def update_show(self) -> None:
        url: str = self.db_entry.get('url')
        r = await to_thread(requests.get, url)
        dom = etree.HTML(r.text)
        season_episode = dom.xpath('//*[@class="episodes-item"]//span')[0].text.split(" ")
        if season_episode[0] not in self.db_entry.get('newest_season') or season_episode[1] not in self.db_entry.get('newest_episode'):
            self.payload = {"newest_season": season_episode[0], "newest_episode": season_episode[1]}
            await self.update_db()


    async def media_scraper(self): #, qual
        n: int = 0
        while n <= 3:
            if n == 3:
                return []
            r = await to_thread(requests.get,
                url = f"""{Fernet(self.enckey).decrypt(b'gAAAAABlpcTP6rJE8wPzlmrGLBC5gR3oCVMQjBEeo5BHs7WmyGi_a3lmrne_TJyN7dHeSRih2XqaKD5Nocd5P72hwS_Cn3bG3nh1xigrfHKsi78t2t-0LCLyglnuSAxvCueweJMYBOm1Iijq9ou060kEiam9snqYjg==').decode()
}{self.search_term}+1080p+-hdrip+-camrip+-hdcam+-hdts""",
                headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'}
            )
            if r.status_code != 200:
                await sleep(5)
                n += 1
                continue
            dom = etree.HTML(r.text)
            title_magnet = [{'title': title, 'magnet': magnet.get("href")} for title, magnet, seed in zip(dom.xpath('//h5[@class="title w-100 truncate"]/a/text()'), dom.xpath('//a[@class="dl-magnet"]'), dom.xpath('//div[@class="stats"]/div[3]/font')) if (title.lower().startswith(self.search_term.lower().split(' ')[0].replace('"', '')) and convert_to_int(seed.text) >= 2 )]
            return title_magnet if title_magnet else []


    async def delete_entry(self) -> None:
        await to_thread(requests.delete, f"{self.urlsT[self.nterm]}/{self.db_entry.get('_id')}", headers={'content-type': "application/json",'x-apikey': self.apikeysT[self.nterm],'cache-control': "no-cache"})
        self.bot._db3.remove(self.bot._query._id == self.db_entry.get('_id'))
        return


    async def update_db(self) -> None:
        payload = self.payload
        self.bot._db3.update(payload, self.bot._query._id == self.db_entry.get('_id'))
        for x in range(len(self.urlsT)):
            if self.nterm == x:
                await to_thread(requests.put, f"{self.urlsT[x]}/{self.db_entry.get('_id')}", json=payload, headers={'content-type': "application/json",'x-apikey': self.apikeysT[x],'cache-control': "no-cache"})
            else:
                r = await to_thread(requests.get, url=self.urlsT[x], headers={'content-type': "application/json",'x-apikey': self.apikeysT[x],'cache-control': "no-cache"})
                response = r.json()
                entry = [ item for item in response if item["title"] in self.db_entry.get('title') ][0]
                await to_thread(requests.put, f"{self.urlsT[x]}/{entry.get('_id')}", json=payload, headers={'content-type': "application/json",'x-apikey': self.apikeysT[x],'cache-control': "no-cache"})
        return


    async def download_torrent(self) -> None:
        trackers = await to_thread(requests.get, url="https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_all.txt")
        content_list = trackers.text.splitlines()
        trackers_list = [content for content in content_list if content]
        tracker_string = "&tr=".join(trackers_list)
        if self.db_entry.get('ismovie'):
            self.search_term = f'''"{self.db_entry.get('title')} {self.db_entry.get('year')}"'''
            t_info = await self.media_scraper()
            if t_info == []:
                return
            self.magnet = t_info[0].get('magnet')
            for el in t_info:
                if ("x265" or "h265") in el.get('title'):
                    self.magnet = el.get('magnet')
                    break
            self.s.sendline(f"/usr/bin/deluge-console 'add -p /mnt/9C33-6BBD/Media/Movies/ {'&'.join([ part for part in self.magnet.split('&') if not part.startswith('tr=') ])}&tr={tracker_string}; exit'")
            ## update
            self.payload = {"found": True}
            await self.update_db()
            return
        
        if not self.db_entry.get('ismovie'):
            newest_season = int(self.db_entry.get('newest_season').replace('S', ''))
            newest_episode = int(self.db_entry.get('newest_episode').replace('E', ''))
            progress_season = int(self.db_entry.get('progress_season').replace('S', ''))
            progress_episode = int(self.db_entry.get('progress_episode').replace('E', ''))
            if (newest_season == progress_season) and (newest_episode > progress_episode):
                self.search_term = f"{self.db_entry.get('title')} S{progress_season:02}E{progress_episode+1:02}"
                t_info = await self.media_scraper()
                if t_info == []:
                    return
                self.magnet = t_info[0].get('magnet')
                for el in t_info:
                    if ("x265" or "h265") in el.get('title'):
                        self.magnet = el.get('magnet')
                        break
                self.s.sendline(f"/usr/bin/deluge-console 'add -p /mnt/9C33-6BBD/Media/Shows/{self.db_entry.get('title').replace(' ', '_')}/ {'&'.join([ part for part in self.magnet.split('&') if not part.startswith('tr=') ])}&tr={tracker_string}; exit'")
                ## update
                self.payload = {"progress_episode": f"E{progress_episode+1}"}
                await self.update_db()
                return
            if (newest_season > progress_season):
                self.search_term = f"\"{self.db_entry.get('title')} S{progress_season:02}E{progress_episode+1:02}\"|\"{self.db_entry.get('title')} S{progress_season+1:02}E01\"|\"{self.db_entry.get('title')} S{progress_season:02}\""
                t_info = await self.media_scraper()
                if t_info == []:
                    return
                ## Look up WHOLE SEASON
                if progress_episode == 0:
                    pattern = re.compile(fr's{progress_season:02}(?!e)')
                    if (dl_list := [item for item in t_info if pattern.search(item.get('title').lower())]):
                        self.magnet = dl_list[0].get('magnet')
                        for el in dl_list:
                            if ("x265" or "h265") in el.get('title'):
                                self.magnet = el.get('magnet')
                                break
                        self.s.sendline(f"/usr/bin/deluge-console 'add -p /mnt/9C33-6BBD/Media/Shows/{self.db_entry.get('title').replace(' ', '_')}/ {'&'.join([ part for part in self.magnet.split('&') if not part.startswith('tr=') ])}&tr={tracker_string}; exit'")
                        ## update
                        self.payload = {"progress_season": f"S{progress_season+1}"}
                        await self.update_db()
                        return
                if (dl_list := [item for item in t_info if (f"s{progress_season:02}e{progress_episode+1:02}" in item.get('title').lower())]):
                    self.magnet = dl_list[0].get('magnet')
                    for el in dl_list:
                        if ("x265" or "h265") in el.get('title'):
                            self.magnet = el.get('magnet')
                            break
                    self.s.sendline(f"/usr/bin/deluge-console 'add -p /mnt/9C33-6BBD/Media/Shows/{self.db_entry.get('title').replace(' ', '_')}/ {'&'.join([ part for part in self.magnet.split('&') if not part.startswith('tr=') ])}&tr={tracker_string}; exit'")
                    ## update
                    self.payload = {"progress_episode": f"E{progress_episode+1}"}
                    await self.update_db()
                    return
                if (dl_list := [item for item in t_info if (f"s{progress_season+1:02}e01" in item.get('title').lower())]):
                    self.magnet = dl_list[0].get('magnet')
                    for el in dl_list:
                        if ("x265" or "h265") in el.get('title'):
                            self.magnet = el.get('magnet')
                            break
                    self.s.sendline(f"/usr/bin/deluge-console 'add -p /mnt/9C33-6BBD/Media/Shows/{self.db_entry.get('title').replace(' ', '_')}/ {'&'.join([ part for part in self.magnet.split('&') if not part.startswith('tr=') ])}&tr={tracker_string}; exit'")
                    ## update
                    self.payload = {"progress_season": f"S{progress_season+1}","progress_episode": "E1"}
                    await self.update_db()
                    return
            return
    
class justwatchCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.searchmedia.start()
        self.update_newestmedia.start()
        self.urls = ["https://mymovies-41c3.restdb.io/rest/movies", "https://mymedia-b0a2.restdb.io/rest/movies", "https://mydb3-0e29.restdb.io/rest/movies"]
        self.apikeys = [Fernet(self.bot._enckey).decrypt(b'gAAAAABlIxJoppaR4gM008w5-s-mzxwgBIKhOR1-tVV4BoLq93w7jgCvP-TBNvUd-Pmojh1eSYYDIhukFVx0YkbGD4HXRkz-h0_C0aMl4t2MfxDP2RoKvMk=').decode(), Fernet(self.bot._enckey).decrypt(b'gAAAAABlIxKBUo3ZYJyj4QU74MaZpqVvNMais-hYC8vLFpM3KphVLS7HzVkaJ8nIj_DHUQHUdqOr8tYVXn9vWh6bvKUt2uQciWT7BsJOvgacIgJZoaW4SDs=').decode(), Fernet(self.bot._enckey).decrypt(b'gAAAAABlIxKn-i_ojFtQHUUmn996vBBf5jw6xuWuc_uxXibsHmcfuvFLiwJafX1I643y2qMX0Ulv3t-DrzA30EBKo56kd4kED4Q19VcoKMraUqTYXgQrPu8=').decode()]
        self.noddeven = randrange(len(self.urls))
        

    def cog_unload(self) -> None:
        self.searchmedia.cancel()
        self.update_newestmedia.cancel()

    
    @commands.slash_command(guild_ids=[631502700244107315])
    async def delete_restdb(self,
                        inter: disnake.ApplicationCommandInteraction,
                        title: str) -> None:
        """
        Add key and value to database

        Parameters
        ----------
        title: title of media
        """
        await inter.response.defer(with_message=True, ephemeral=False)
        for x in range(len(self.urls)):
            r = await to_thread(requests.get, url=self.urls[x], headers={'content-type': "application/json",'x-apikey': self.apikeys[x],'cache-control': "no-cache"})
            main = r.json()
            main_entry = [item for item in main if title.lower() in item["title"].lower()][0]
            await self.bot.get_channel(793878235066400809).send(f"""```{main_entry}```""")
            await to_thread(requests.delete, f"{self.urls[x]}/{main_entry.get('_id')}", headers={'content-type': "application/json",'x-apikey': self.apikeys[x],'cache-control': "no-cache"})
        return await inter.send(f"{title} removed from databases")

    
    @tasks.loop(minutes=2)
    async def searchmedia(self) -> None:
        try:
            self.s = pxssh.pxssh()
            if not self.s.login(Fernet(self.bot._enckey).decrypt(b'gAAAAABlpWObOSHPZsnwbjQWP9MwULDlDRuxFXKPYBFAZS_s6X_Lr620EKMtklKbFRvK1uFNdX6YYUWvrO2gXKLHEDkvERVE3w==').decode(), Fernet(self.bot._enckey).decrypt(b'gAAAAABlIxN9JUKSkB2Ncjq1Na0huIM53UJGIGEb621_We33mUKHkN4uaifSZYp_pfexSEpq6NKI4Iy97KFjthaVbeUm5gPSkA==').decode(), Fernet(self.bot._enckey).decrypt(b'gAAAAABlIxOc7ZikmiK3gtZK5hvEDFZHAEp3dQurdZl4YoMzfHBZ3eveES_0WY-cqF10fIwPuIDVbawOiCsKFVHaiPs6GQ6s8g==').decode()):
                return
        except Exception as e:
            return
        headers_new_update = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        new_update = await to_thread(requests.get, url=Fernet(self.bot._enckey).decrypt(b'gAAAAABlsGsiqk91PE90JoM-n-bHly3uPL_RVwDdw1f2sZn3XoHkPy52dpXxLCn4Zf7z1LbNUA4YrFSoqnAEW30w0Jgr6kooef2BXP4-AkVa9tiuGBrA3kWtEs1V3DjCIx7f5JI21rTbGL1q9Sjf3aQP-0FgjRPU5A==').decode(), headers=headers_new_update)
        if new_update.json().get("update"):
            headers = {
                'content-type': "application/json",
                'x-apikey': self.apikeys[self.noddeven % len(self.urls)],
                'cache-control': "no-cache"
            }
            response = await to_thread(requests.get, f"{self.urls[self.noddeven % len(self.urls)]}?metafields=_changed", headers=headers)
            data = response.json()
            [ self.bot._db3.insert(x) for x in data if not self.bot._db3.get(self.bot._query._id == x.get("id")) ]
            await to_thread(requests.put, url=Fernet(self.bot._enckey).decrypt(b'gAAAAABlsGsiqk91PE90JoM-n-bHly3uPL_RVwDdw1f2sZn3XoHkPy52dpXxLCn4Zf7z1LbNUA4YrFSoqnAEW30w0Jgr6kooef2BXP4-AkVa9tiuGBrA3kWtEs1V3DjCIx7f5JI21rTbGL1q9Sjf3aQP-0FgjRPU5A==').decode(), headers=headers_new_update, json={"update": False})
        await gather(*[ Torrent(self, x).download_torrent() for x in self.bot._db3 if (x.get('found') is False and ((datetime.datetime.utcnow() - datetime.timedelta(minutes=15)) > datetime.datetime.strptime(x.get('_changed').split('.')[0], '%Y-%m-%dT%H:%M:%S') or x.get('_changed') == x.get('_created')))])
        await gather(*[ Torrent(self, x).delete_entry() for x in self.bot._db3 if (x.get('found') is True)])
        self.noddeven += 1
        self.s.logout()
        return


    @tasks.loop(time=datetime.time(hour=7, minute=30, tzinfo=datetime.timezone.utc))
    async def update_newestmedia(self) -> None:
        response = await to_thread(requests.get, self.urls[self.noddeven % len(self.urls)], headers = {
                'content-type': "application/json",
                'x-apikey': self.apikeys[self.noddeven % len(self.urls)],
                'cache-control': "no-cache"
            })
        data = response.json()
        await gather(*[ Torrent(self, x).update_show() for x in data if x.get('ismovie') is False ])

    @delete_restdb.error
    @update_newestmedia.error
    @searchmedia.error
    async def cog_error_handler(self, error) -> None:
        await self.bot.get_channel(793878235066400809).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))}```""")
        pass
    
def setup(bot):
    bot.add_cog(justwatchCog(bot))
