from lxml import html
import requests
from disnake.ext import commands, tasks
import disnake
from asyncio import gather, to_thread, sleep
import datetime
from cryptography.fernet import Fernet
import traceback
import re
# from deluge_client import DelugeRPCClient
import random
from babelfish import Language
from subliminal import download_best_subtitles, region, save_subtitles, scan_video
from pathlib import Path
import json

VIDEO_EXTENSIONS = [
    ".avi", ".mp4", ".mkv", ".mpg",
    ".mpeg", ".mov", ".rm", ".vob",
    ".wmv", ".flv", ".3gp",".3g2", ".swf", ".mswmm"
]

def convert_to_int(string):
    if string[-1] == 'K':
        numeric_part = float(string[:-1])  # Remove 'K' and convert to float
        integer_value = int(numeric_part * 1000)  # Convert to integer by multiplying with 1000
        return integer_value
    if string[-1].isdigit():
        return int(string)  # If no 'K', directly convert to integer
    else:
        return 0


class GlobalVars(commands.Cog):
    def __init__(self, bot) -> None:
        self.url = "https://mymovies-41c3.restdb.io/rest/movies"
        self.decoder = Fernet(bot._enckey)
        self.api_key = self.decoder.decrypt(b'gAAAAABlIxJoppaR4gM008w5-s-mzxwgBIKhOR1-tVV4BoLq93w7jgCvP-TBNvUd-Pmojh1eSYYDIhukFVx0YkbGD4HXRkz-h0_C0aMl4t2MfxDP2RoKvMk=').decode()
        # self.host = self.decoder.decrypt(b'gAAAAABlpWObOSHPZsnwbjQWP9MwULDlDRuxFXKPYBFAZS_s6X_Lr620EKMtklKbFRvK1uFNdX6YYUWvrO2gXKLHEDkvERVE3w==').decode()
        # self.deluge_user =  self.decoder.decrypt(b'gAAAAABlIxN9JUKSkB2Ncjq1Na0huIM53UJGIGEb621_We33mUKHkN4uaifSZYp_pfexSEpq6NKI4Iy97KFjthaVbeUm5gPSkA==').decode()
        # self.deluge_passwd = self.decoder.decrypt(b'gAAAAABlIxOc7ZikmiK3gtZK5hvEDFZHAEp3dQurdZl4YoMzfHBZ3eveES_0WY-cqF10fIwPuIDVbawOiCsKFVHaiPs6GQ6s8g==').decode()
        self.host = self.decoder.decrypt(b'gAAAAABl_exEE4XNI2DIJk34tap0xf-2Vdt7rhsMQ5ZV8FB-7EZ_BpqGTqFoXq9AQ04rsxSXgVJ_8FcguE_eKS0ChNuVq-zApOALV0VlA0NO1pUO_SnXODU=').decode()
        self.deluge_passwd = self.decoder.decrypt(b'gAAAAABl_eyPYG0TxoImSD3TCeliHQ2hmMGnpMd22CcuPbtyCVzcCDjynwutv6zzWUaGRTCPNpfNDIUt3vX3KG43kymuMCdiKSHu2Km3wh8DjQUdY6bcYCg=').decode()


class Torrent:
    def __init__(self, me: object, database_entry: dict) -> None:
        self.bot = me.bot
        self.db_entry = database_entry
        self.global_var = me.bot.global_var


    async def update_show(self) -> None:
        url: str = self.db_entry.get('url')
        r = await to_thread(requests.get, url)
        dom = html.fromstring(r.text)
        season_episode = dom.cssselect('.episodes-item span')[0].text_content().split(" ")
        if season_episode[0] not in self.db_entry.get('newest_season') or season_episode[1] not in self.db_entry.get('newest_episode'):
            self.payload = { "newest_season": season_episode[0], "newest_episode": season_episode[1], "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z' }
            await self.update_db()


    async def media_scraper(self): #, qual
        n: int = 0
        while n <= 5:
            if n == 5:
                return []
            urls = ["https://bitsearch.to/search?q=", "https://solidtorrents.to/search?q="]
            r = await to_thread(requests.get,
                url = f"{urls[(n % len(urls))]}{self.search_term}+-hdrip+-camrip+-hdcam+-hdts+-720p+-480p+-2160p&sort=seeders",
                headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'}
            )
            if r.status_code != 200:
                await sleep(5)
                n += 1
                continue
            dom = html.fromstring(r.text)
            title_magnet = [{'title': title, 'magnet': magnet.get("href")} for title, magnet, seed in zip([elem.text_content() for elem in dom.cssselect('h5.title.w-100.truncate > a')], dom.cssselect('a.dl-magnet'), dom.cssselect('div.stats > div:nth-child(3) > font')) if ( "1080p" in title.lower() and title.lower().startswith(self.search_term.lower().split(' ')[0].replace('"', '')) and convert_to_int(seed.text) >= 2 )]
            return title_magnet if title_magnet else []


    async def delete_entry(self) -> None:
        await to_thread(requests.delete, f"{self.global_var.url}/{self.db_entry.get('_id')}", headers={'content-type': "application/json",'x-apikey': self.global_var.api_key,'cache-control': "no-cache"})
        self.bot._db3.remove(self.bot._query["_id"] == self.db_entry.get('_id'))
        return


    async def update_db(self, restdb = True) -> None:
        payload = self.payload
        self.bot._db3.update(payload, self.bot._query["_id"] == self.db_entry.get('_id'))
        if restdb:
            await to_thread(requests.put, f"{self.global_var.url}/{self.db_entry.get('_id')}", json=payload, headers={'content-type': "application/json",'x-apikey': self.global_var.api_key,'cache-control': "no-cache"})
        return


    async def get_trackers(self):
        trackers = await to_thread(requests.get, url="https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_all.txt")
        content_list = trackers.text.splitlines()
        trackers_list = [content for content in content_list if content]
        tracker_string = "&tr=".join(trackers_list)
        return tracker_string


    async def magnet2deluge(self, torrents, medium):
        magnet_uri = None
        for tor_info in torrents:
            tor_title = tor_info.get("title")
            if "265" in tor_title:
                if not magnet_uri:
                    magnet_uri = tor_info.get("magnet")
                if "10bit" in tor_title:
                    magnet_uri = tor_info.get("magnet")
                    break
        if not magnet_uri:
            magnet_uri = torrents[0].get("magnet")
        with requests.Session() as s:
            url = self.global_var.host
            headers = {'content-type': 'application/json'}
            for data in [{"method": "auth.login", "params": [self.global_var.deluge_passwd]}, {"method": "web.connect", "params": ["58de378ad2f643d78c3e1ea72cbbc719"]}, {"method": "web.connected", "params": []}, {"method": "core.add_torrent_magnet", "params": [f"{'&'.join([ part for part in magnet_uri.split('&') if not part.startswith('tr=') ])}&tr={await self.get_trackers()}", {"download_location": medium}]}]:
                payload = {
                    'method': data.get("method"),
                    'params': data.get("params"),
                    'id': 1
                }
                response = s.post(url, data=json.dumps(payload), headers=headers)
                if response.json().get("error"):
                    await self.bot.get_channel(self.bot._test_channelid).send(f"""```{response.json().get("error")}```""")
                    return
        # with DelugeRPCClient(self.global_var.host, 58846, self.global_var.deluge_user, self.global_var.deluge_passwd) as client:
        #     try:
        #         client.core.add_torrent_magnet(f"{'&'.join([ part for part in magnet_uri.split('&') if not part.startswith('tr=') ])}&tr={await self.get_trackers()}", options={"download_location": medium})
        #     except Exception as e:
        #         await self.bot.get_channel(self.bot._test_channelid).send(f"""```{e}```""")
        return
    

    async def download_torrent(self) -> None:
        if self.db_entry.get('ismovie'):
            self.search_term = f'''"{self.db_entry.get('title')} {self.db_entry.get('year')}"'''
            t_info = await self.media_scraper()
            if t_info == []:
                self.payload = {"_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}
                await self.update_db(restdb = False)
                return
            await self.magnet2deluge(t_info, "/movies/")
            ## update
            self.payload = {"found": True}
            await self.delete_entry()
            return

        if not self.db_entry.get('ismovie'):
            newest_season = int(self.db_entry.get('newest_season').replace('S', ''))
            newest_episode = int(self.db_entry.get('newest_episode').replace('E', ''))
            progress_season = int(self.db_entry.get('progress_season').replace('S', ''))
            progress_episode = int(self.db_entry.get('progress_episode').replace('E', ''))
            if progress_episode == 0:
                self.search_term = f"\"{self.db_entry.get('title')} S{progress_season:02}E{progress_episode+1:02}\"|\"{self.db_entry.get('title')} S{progress_season:02}\""
                t_info = await self.media_scraper()
                if t_info == []:
                    self.payload = {"_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}
                    await self.update_db(restdb = False)
                    return
                if (dl_list := [item for item in t_info if not f"s{progress_season:02}e{progress_episode+1:02}" in item.get('title').lower()]):
                    await self.magnet2deluge(dl_list, f"/tv/{self.db_entry.get('title').replace(' ', '_')}/")
                    self.payload = {"progress_episode": f"E{newest_episode}", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}
                    if newest_season > progress_season:
                        self.payload = {"progress_season": f"S{progress_season + 1}", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}
                    await self.update_db()
                    return
                if (dl_list := [item for item in t_info if f"s{progress_season:02}e{progress_episode+1:02}" in item.get('title').lower()]):
                    await self.magnet2deluge(dl_list, f"/tv/{self.db_entry.get('title').replace(' ', '_')}/")
                    self.payload = {"progress_episode": f"E{progress_episode+1}", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}
                    await self.update_db()
                    return
            self.search_term = f"\"{self.db_entry.get('title')} S{progress_season:02}E{progress_episode+1:02}\"|\"{self.db_entry.get('title')} S{progress_season+1:02}E01\"|\"{self.db_entry.get('title')} S{progress_season+1:02}\""
            t_info = await self.media_scraper()
            if t_info == []:
                self.payload = {"_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}
                await self.update_db(restdb = False)
                return
            if (dl_list := [item for item in t_info if (f"s{progress_season:02}e{progress_episode+1:02}" in item.get('title').lower())]):
                await self.magnet2deluge(dl_list, f"/tv/{self.db_entry.get('title').replace(' ', '_')}/")
                self.payload = {"progress_episode": f"E{progress_episode+1}", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}
                await self.update_db()
                return
            if (dl_list := [item for item in t_info if not (f"s{progress_season+1:02}e01" in item.get('title').lower())]):
                await self.magnet2deluge(dl_list, f"/tv/{self.db_entry.get('title').replace(' ', '_')}/")
                self.payload = {"progress_season": f"S{newest_season}","progress_episode": f"E{newest_episode}", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}
                if newest_season > progress_season+1:
                    self.payload = {"progress_season": f"S{progress_season+1}","progress_episode": f"E0", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}
                await self.update_db()
                return
            if (dl_list := [item for item in t_info if (f"s{progress_season+1:02}e01" in item.get('title').lower())]):
                await self.magnet2deluge(dl_list, f"/tv/{self.db_entry.get('title').replace(' ', '_')}/")
                self.payload = {"progress_season": f"S{progress_season+1}","progress_episode": "E1", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}
                await self.update_db()
                return
            return


class justwatchCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.searchmedia.start()
        self.update_newestmedia.start()
        self.bot.global_var = GlobalVars(self.bot)
        self.update_check_url = self.bot.global_var.decoder.decrypt(b'gAAAAABlsGsiqk91PE90JoM-n-bHly3uPL_RVwDdw1f2sZn3XoHkPy52dpXxLCn4Zf7z1LbNUA4YrFSoqnAEW30w0Jgr6kooef2BXP4-AkVa9tiuGBrA3kWtEs1V3DjCIx7f5JI21rTbGL1q9Sjf3aQP-0FgjRPU5A==').decode()


    def cog_unload(self) -> None:
        self.searchmedia.cancel()
        self.update_newestmedia.cancel()


    @commands.slash_command()
    async def delete_whole_db(self,
                        inter: disnake.ApplicationCommandInteraction) -> None:
        """
        delete db 

        Parameters
        ----------
        """
        await inter.response.defer(with_message=True, ephemeral=False)
        self.bot._db3.truncate()
        await inter.send("Deleted")
        return

    @commands.slash_command()
    async def delete_db3_entry(self, inter, title) -> None:
        """
        Remove entry from db

        Parameters
        ----------
        title: title of media entry
        """
        self.bot._db3.remove(self.bot._query.title == title)
        return await inter.send(f"{title} removed from databases")


    async def download_subs(self, file_path):
        await sleep(random.randint(2, 15))
        region.configure('dogpile.cache.dbm', arguments={'filename': '/home/Scripts/pythonvenvs/deluge/deluge_scripts/cachefile.dbm'}, replace_existing_backend=True)
        video = scan_video(file_path)
        subtitles = await to_thread(download_best_subtitles, [video], {Language('eng')})
        # save them to disk, next to the video
        save_subtitles(video, subtitles[video])
        return

    @commands.slash_command()
    async def download_subtitles(self,
                        inter: disnake.ApplicationCommandInteraction,
                        media_type: bool,
                        media_path: str) -> None:
        """
        Download subtitles

        Parameters
        ----------
        media_type: if movie set True, if tv show set False
        media_path: where media is located
        """
        await inter.response.defer(with_message=True, ephemeral=False)
        torrent = Path("/mnt/9C33-6BBD/Media/Shows/", media_path)
        if media_type:
            torrent = Path("/mnt/9C33-6BBD/Media/Movies/", media_path)
        if torrent.is_file():
            if any(torrent.suffix.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                await self.download_subs(str(torrent))
            return
        await gather(*[ self.download_subs(str(vid_file)) for vid_file in torrent.rglob('*') if vid_file.is_file() and any(vid_file.suffix.lower().endswith(ext) for ext in VIDEO_EXTENSIONS) ])
        return await inter.send(f"Downloaded subs for {torrent}")


    @commands.slash_command()
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
        r = await to_thread(requests.get, url=self.bot.global_var.url, headers={'content-type': "application/json",'x-apikey': self.bot.global_var.api_key,'cache-control': "no-cache"})
        main = r.json()
        main_entry = next(item for item in main if title.lower() in item["title"].lower())
        await self.bot.get_channel(self.bot._test_channelid).send(f"""```{main_entry}```""")
        await to_thread(requests.delete, f"{self.bot.global_var.url}/{main_entry.get('_id')}", headers={'content-type': "application/json",'x-apikey': self.bot.global_var.api_key,'cache-control': "no-cache"})
        self.bot._db3.remove(self.bot._query.title == title)
        return await inter.send(f"{title} removed from databases")


    @tasks.loop(seconds=60)
    async def searchmedia(self) -> None:
        headers_new_update = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        update_check_url = self.update_check_url
        new_update = await to_thread(requests.get, url=update_check_url, headers=headers_new_update)
        if new_update.json().get("update"):
            headers = {
                'content-type': "application/json",
                'x-apikey': self.bot.global_var.api_key,
                'cache-control': "no-cache"
            }
            response = await to_thread(requests.get, f"{self.bot.global_var.url}?metafields=_changed", headers=headers)
            data = response.json()
            [ self.bot._db3.insert(x) for x in data if not self.bot._db3.search(self.bot._query["_id"] == x.get("_id")) ]
            await to_thread(requests.put, url=update_check_url, headers=headers_new_update, json={"update": False})
        await gather(*[ Torrent(self, x).download_torrent() for x in self.bot._db3 if ( not (x.get('newest_season') == x.get('progress_season') and x.get('newest_episode') == x.get('progress_episode')) and (datetime.datetime.utcnow() - datetime.timedelta(minutes=15)) > datetime.datetime.strptime(x.get('_changed').split('.')[0], '%Y-%m-%dT%H:%M:%S') or x.get('_changed') == x.get('_created'))])
        return


    @tasks.loop(hours=12)
    async def update_newestmedia(self) -> None:
        [ await Torrent(self, x).update_show() for x in self.bot._db3 if x.get('ismovie') is False ]

    @delete_whole_db.error
    @delete_db3_entry.error
    @download_subtitles.error
    @delete_restdb.error
    @update_newestmedia.error
    @searchmedia.error
    async def cog_error_handler(self, error) -> None:
        await self.bot.get_channel(793878235066400809).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))[-1500:]}```""")
        pass
    
def setup(bot):
    bot.add_cog(justwatchCog(bot))
