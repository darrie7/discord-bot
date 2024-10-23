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
import xml.etree.ElementTree as ET
from guessit import guessit
from fake_useragent import UserAgent

VIDEO_EXTENSIONS = [
    ".avi", ".mp4", ".mkv", ".mpg",
    ".mpeg", ".mov", ".rm", ".vob",
    ".wmv", ".flv", ".3gp",".3g2", ".swf", ".mswmm"
]

# def convert_to_int(string):
#     if string[-1] == 'K':
#         numeric_part = float(string[:-1])  # Remove 'K' and convert to float
#         integer_value = int(numeric_part * 1000)  # Convert to integer by multiplying with 1000
#         return integer_value
#     if string[-1].isdigit():
#         return int(string)  # If no 'K', directly convert to integer
#     else:
#         return 0


class GlobalVars(commands.Cog):
    def __init__(self, bot) -> None:
        self.url = "https://mymovies-41c3.restdb.io/rest/movies"
        self.decoder = Fernet(bot._enckey)
        self.api_key = self.decoder.decrypt(b'gAAAAABlIxJoppaR4gM008w5-s-mzxwgBIKhOR1-tVV4BoLq93w7jgCvP-TBNvUd-Pmojh1eSYYDIhukFVx0YkbGD4HXRkz-h0_C0aMl4t2MfxDP2RoKvMk=').decode()
        self.host = self.decoder.decrypt(b'gAAAAABmBvixHfgpAN-TBLb04DXf2E1J53zdxQsHevpacEShlPR7oLvwa4-EOAA11alY6Us3w0ZRYOpqt_psAZwepCekQ__WkWJExYHBG4OEebO4TP3Ah70=').decode()
        self.deluge_passwd = self.decoder.decrypt(b'gAAAAABmEvel4VRvjFbNkKvvqWrb3c5Jrngy6JOQZ83JjyDHPXuioI0-xwROYDG7EdQ8Gjpmy-JuCZLdjsIKrZ1V0YF0cBxkiQm10mMU0ScTWBW1EZVJrft5WTe4ZsHf9v6W4C57Kk_luG4BB4wy98mOe9ZxY1bKFDlMYAAy-IH77YUO4MBr2_QtWk7JwOhpF7-Bwctfp00s-3T2Q4QDE5fA-aaOp-dqqKAQUZw44rcMA_3-KdKWjdfkobof8QQoKBQ5cEdrA5JO').decode()
        self.jkt = self.decoder.decrypt(b'gAAAAABmRUBmnARecJEV7e02UAXCZhv9uIsuMtvcHw5KCeEl0-caj94VYCaueaQv7LeB_iFASbkA3abMasRRAbxj_5YOHCjQK_hy8Av7GPfgYFuEAaMWlwcP4prBuVMg7p7EL2oGvKJ-HBCfnS4ICwc7RTVjCsuYxR2cjtv9rlbP2upMnpj-wVACNzK7wZ4jWpgUh9zt-rjWE7fTzEIOTXoCbHsb1_MIwTtGdIuPuvyzgAGXojuEl1E=').decode()


class Torrent:
    def __init__(self, me: object, database_entry: dict) -> None:
        self.bot = me.bot
        self.db_entry = database_entry
        self.global_var = me.bot.global_var


    async def update_show(self) -> None:
        url: str = self.db_entry.get('url')
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        r = await to_thread(requests.get, url=url, headers=headers)
        dom = html.fromstring(r.text)
        season_episode = dom.cssselect('.episodes-item span')[0].text_content().split(" ") if dom.cssselect('.episodes-item span') else None
        if not season_episode:
            return
        if season_episode[0] not in self.db_entry.get('newest_season') or season_episode[1] not in self.db_entry.get('newest_episode'):
            await self.update_db({ "newest_season": season_episode[0], "newest_episode": season_episode[1], "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z' })

    def guess_title(self, item):
        title = guessit(item.find('title').text).get('title')
        return title.lower() if title else ''
        

    async def media_scraper(self):
        n: int = 0
        uri = f"{self.global_var.jkt}{self.search_term}+1080p"
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        while n < 2:
            data = await to_thread(requests.get, url=uri, headers=headers)
            if not data.ok:
                await sleep(random.randint(2, 15))
                n += 1
                continue
            root = ET.fromstring(data.text)
            #title_magnet = [{'title': item.find('title').text, 'magnet': item.find(".//{http://torznab.com/schemas/2015/feed}attr[@name='magneturl']").attrib['value']} for item in root.findall('.//item') if (item.find(".//{http://torznab.com/schemas/2015/feed}attr[@name='magneturl']") and item.find(".//{http://torznab.com/schemas/2015/feed}attr[@name='seeders']") and not any(word in item.find('title').text.lower() for word in ['hdrip', 'camrip', 'hdcam', 'hdts']) and int(item.find(".//{http://torznab.com/schemas/2015/feed}attr[@name='seeders']").attrib['value']) > 2 and guessit(item.find('title').text).get('title').strip().lower() in self.db_entry.get('title').lower() )]
            title_magnet = [{'title': item.find('title').text, 'magnet': item.find('link').text} for item in root.findall('.//item') if ( item.find('title').text and item.find('link').text and not any(word in item.find('title').text.lower() for word in ['hdrip', 'camrip', 'hdcam', 'hdts']) and int(item.find(".//{http://torznab.com/schemas/2015/feed}attr[@name='seeders']").attrib['value']) > 2 and self.guess_title(item) in self.db_entry.get('title').lower() )]
            # await self.bot.get_channel(793878235066400809).send(f"""```{title_magnet}```""")
            return title_magnet if title_magnet else []
        return []


    async def delete_entry(self) -> None:
        await to_thread(requests.delete, f"{self.global_var.url}/{self.db_entry.get('_id')}", headers={'content-type': "application/json",'x-apikey': self.global_var.api_key,'cache-control': "no-cache"})
        self.bot._db3.remove(self.bot._query["_id"] == self.db_entry.get('_id'))
        return


    async def update_db(self, payload, restdb = True) -> None:
        self.bot._db3.update(payload, self.bot._query["_id"] == self.db_entry.get('_id'))
        if restdb:
            await to_thread(requests.put, f"{self.global_var.url}/{self.db_entry.get('_id')}", json=payload, headers={'content-type': "application/json",'x-apikey': self.global_var.api_key,'cache-control': "no-cache"})
        return


    async def get_trackers(self):
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        trackers = await to_thread(requests.get, url="https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_all.txt", headers=headers)
        content_list = trackers.text.splitlines()
        trackers_list = [content for content in content_list if content]
        tracker_string = "&tr=".join(trackers_list)
        return tracker_string


    async def magnet2deluge(self, torrents, medium):
        found_torrent = None
        for tor_info in torrents:
            if "265" in tor_info.get("title"):
                if not found_torrent:
                    found_torrent = tor_info
                if "10bit" in tor_info.get("title"):
                    found_torrent = tor_info
                    break
        if not found_torrent:
            found_torrent = torrents[0]
        if "10bit" not in found_torrent.get("title") and self.db_entry.get('h26510_cycle') < 4:
            await self.update_db({"_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z', "h26510_cycle": self.db_entry.get('h26510_cycle')+1}, restdb = False)
            return True
        with requests.Session() as s:
            para  = None
            if "magnet" in found_torrent.get('magnet'):
                para = f"{'&'.join([ part for part in found_torrent.get('magnet').split('&') if not part.startswith('tr=') ])}&tr={await self.get_trackers()}"
            else:
                try: 
                    magneturi = await to_thread(s.get, url=found_torrent.get('magnet'))
                except requests.exceptions.RequestException as e:# This is the correct syntax
                    matches = re.findall(r"'(.*?)'", str(e))
                    if not matches or not "magnet" in matches[0]:
                        await self.bot.get_channel(self.bot._test_channelid).send(f"""```{e}```""")
                        return True
                    para = f"{'&'.join([ part for part in matches[0].split('&') if not part.startswith('tr=') ])}&tr={await self.get_trackers()}"
            if not para:
                return True
            url = self.global_var.host
            headers = {'content-type': 'application/json'}
            for data in [{"method": "auth.login", "params": [self.global_var.deluge_passwd]}, {"method": "web.connect", "params": ["58de378ad2f643d78c3e1ea72cbbc719"]}, {"method": "web.connected", "params": []}, {"method": "core.add_torrent_magnet", "params": [ para, {"download_location": medium}]}]:
                payload = {
                    'method': data.get("method"),
                    'params': data.get("params"),
                    'id': 1
                }
                response = await to_thread(s.post, url=url, data=json.dumps(payload), headers=headers)
                if response.json().get("error"):
                    await self.bot.get_channel(self.bot._test_channelid).send(f"""```{response.json().get("error")}```""")
                    return True
        return
    

    async def download_torrent(self) -> None:
        if self.db_entry.get('ismovie'):
            self.search_term = f'''"{self.db_entry.get('title')} {self.db_entry.get('year')}"'''
            t_info = await self.media_scraper()
            if t_info == []:
                await self.update_db({"_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}, restdb = False)
                return
            mag2del = await self.magnet2deluge(t_info, f"/movies/{self.db_entry.get('title').replace(' ', '_')}_{self.db_entry.get('year')}/")
            if mag2del:
                return
            ## update
            #self.payload = 
            await self.update_db({"found": True, "h26510_cycle": 0})
            #await self.delete_entry()
            return

        if not self.db_entry.get('ismovie'):
            newest_season = int(self.db_entry.get('newest_season').replace('S', ''))
            newest_episode = int(self.db_entry.get('newest_episode').replace('E', ''))
            progress_season = int(self.db_entry.get('progress_season').replace('S', ''))
            progress_episode = int(self.db_entry.get('progress_episode').replace('E', ''))
            dl_path = f"/tv/{self.db_entry.get('title').replace(' ', '_')}/"
            if progress_episode == 0:
                self.search_term = f"{self.db_entry.get('title')} S{progress_season:02}"
                t_info = await self.media_scraper()
                if not t_info == []:
                    mag2del = await self.magnet2deluge(t_info, dl_path)
                    if mag2del:
                        return
                    await self.update_db({"progress_season": f"S{progress_season + 1}", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z', "h26510_cycle": 0} if (newest_season > progress_season) else {"progress_episode": f"E{newest_episode}", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z', "h26510_cycle": 0})
                    return
                self.search_term = f"{self.db_entry.get('title')} S{progress_season:02}E{progress_episode+1:02}"
                t_info = await self.media_scraper()
                if not t_info == []:
                    mag2del = await self.magnet2deluge(t_info, dl_path)
                    if mag2del:
                        return
                    await self.update_db({"progress_episode": f"E{progress_episode+1}", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z', "h26510_cycle": 0})
                    return
                await self.update_db({"_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}, restdb = False)
                return
            self.search_term = f"{self.db_entry.get('title')} S{progress_season:02}E{progress_episode+1:02}"
            t_info = await self.media_scraper()
            if not t_info == []:
                mag2del = await self.magnet2deluge(t_info, dl_path)
                if mag2del:
                    return
                await self.update_db({"progress_episode": f"E{progress_episode+1}", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z', "h26510_cycle": 0})
                return
            self.search_term = f"{self.db_entry.get('title')} S{progress_season+1:02}"
            t_info = await self.media_scraper()
            if not t_info == []:
                mag2del = await self.magnet2deluge(t_info, dl_path)
                if mag2del:
                    return
                await self.update_db({"progress_season": f"S{progress_season+1}","progress_episode": f"E0", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z', "h26510_cycle": 0} if (newest_season > progress_season+1) else {"progress_season": f"S{newest_season}","progress_episode": f"E{newest_episode}", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z', "h26510_cycle": 0})
                return
            self.search_term = f"{self.db_entry.get('title')} S{progress_season+1:02}E01"
            t_info = await self.media_scraper()
            if not t_info == []:
                mag2del = await self.magnet2deluge(t_info, dl_path)
                if mag2del:
                    return
                await self.update_db({"progress_season": f"S{progress_season+1}","progress_episode": "E1", "_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z', "h26510_cycle": 0})
                return
            await self.update_db({"_changed": f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'}, restdb = False)
            return


class justwatchCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.restart_failed.start()
        self.searchmedia.start()
        self.update_newestmedia.start()
        self.bot.global_var = GlobalVars(self.bot)
        self.update_check_url = self.bot.global_var.decoder.decrypt(b'gAAAAABlsGsiqk91PE90JoM-n-bHly3uPL_RVwDdw1f2sZn3XoHkPy52dpXxLCn4Zf7z1LbNUA4YrFSoqnAEW30w0Jgr6kooef2BXP4-AkVa9tiuGBrA3kWtEs1V3DjCIx7f5JI21rTbGL1q9Sjf3aQP-0FgjRPU5A==').decode()


    def cog_unload(self) -> None:
        self.restart_failed.cancel()
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
        await inter.send("```Deleted```")
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
        return await inter.send(f"```{title} removed from databases```")


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
        return await inter.send(f"```Downloaded subs for {torrent}```")


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
        return await inter.send(f"```{title} removed from databases```")


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
        data = [ x for x in self.bot._db3 if not x.get('found') ]
        await gather(*[ Torrent(self, x).download_torrent() for x in data if ( not (x.get('newest_season') == x.get('progress_season') and x.get('newest_episode') == x.get('progress_episode')) and ((datetime.datetime.utcnow() - datetime.timedelta(minutes=15)) > datetime.datetime.strptime(x.get('_changed').split('.')[0], '%Y-%m-%dT%H:%M:%S') or x.get('_changed') == x.get('_created')))])
        return


    @tasks.loop(hours=12)
    async def update_newestmedia(self) -> None:
        [ await Torrent(self, x).update_show() for x in self.bot._db3 if x.get('ismovie') is False ]


    @tasks.loop(minutes=5)
    async def restart_failed(self) -> None:
        if self.searchmedia.failed() or not self.searchmedia.is_running():
            self.searchmedia.restart()
        if self.update_newestmedia.failed() or not self.update_newestmedia.is_running():
            self.update_newestmedia.restart()

    @restart_failed.error
    async def restart_failed_error_handler(self, error) -> None:
        await self.bot.get_channel(793878235066400809).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))[-1500:]}```""")
        self.restart_failed.restart()
        pass

    
    @searchmedia.error
    async def searchmedia_error_handler(self, error) -> None:
        await self.bot.get_channel(793878235066400809).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))[-1500:]}```""")
        self.searchmedia.restart()
        pass

    @update_newestmedia.error
    async def update_newestmedia_error_handler(self, error) -> None:
        await self.bot.get_channel(793878235066400809).send(f"""```{"".join(traceback.format_exception(type(error), error, error.__traceback__))[-1500:]}```""")
        self.update_newestmedia.restart()
        pass
    
def setup(bot):
    bot.add_cog(justwatchCog(bot))
