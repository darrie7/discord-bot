import requests
from datetime import datetime, timedelta
import time
import json
from asyncio import run, gather, to_thread, sleep
from disnake.ext import commands, tasks
import disnake

class skiplaggedcog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.main.start()
        

    def cog_unload(self) -> None:
        self.main.cancel()

    async def generate_date_range(self, start_date, end_date):
        date_range = []
        current_date = start_date

        while current_date <= end_date:
            date_range.append(current_date)
            current_date += timedelta(days=1)

        return date_range
    
    async def url_shortener(self, data):
        api_url = "https://is.gd/create.php"
        param = {'format': 'simple', 'url': f"https://skiplagged.com/flights/{data.get('depAirport')}/{data.get('arrAirport')}/{data.get('dates')[0]}/{data.get('dates')[1]}?adults=2#trip={data.get('ports')}"}
        n = 0
        while n <= 2:
            if n == 2:
                return f"https://skiplagged.com/flights/{data.get('depAirport')}/{data.get('arrAirport')}/{data.get('dates')[0]}/{data.get('dates')[1]}?adults=2#trip={data.get('ports')}"
            response = await to_thread(requests.get, url=api_url, params=param)
            if response.status_code != 200:
                await sleep(3)
                n += 1
                continue
            break
        return response.text.strip()


    async def searchflights(self, url, dates):
        n = 0
        while n <= 3:
            if n == 3:
                return [[], []]
            r = await to_thread(requests.get, url=url, headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'})
            if r.status_code != 200:
                await sleep(5)
                n += 1
                continue
            break
        resp = r.json()
        shorter_than_20 = [flight for flight in resp.get('itineraries').get('outbound') if resp.get('flights').get(flight.get('flight')).get('duration')/3600 <= 20 and resp.get('flights').get(flight.get('flight')).get('segments')[0].get('departure').get('airport') in ["AMS", "DUS", "ANR", "EIN", "RTM", "MST", "GRQ", "CGN", "FMO", "BRU"] and "SK" not in resp.get('flights').get(flight.get('flight')).get('segments')[0].get('airline') ][:2]
        dataless20 = {"data":[]}
        for flight in shorter_than_20:
            dataless20.get("data").append({"price": flight.get('min_round_trip_price')/100, "flightTime": resp.get('flights').get(flight.get('flight')).get('duration'), "dates":dates, "departTime": resp.get('flights').get(flight.get('flight')).get('segments')[0].get('departure').get('time'), "arrivTime": resp.get('flights').get(flight.get('flight')).get('segments')[-1].get('arrival').get('time'), "depAirport": resp.get('flights').get(flight.get('flight')).get('segments')[0].get('departure').get('airport'), "arrAirport": resp.get('flights').get(flight.get('flight')).get('segments')[-1].get('arrival').get('airport'), "ports": "-".join([ f"{x.get('airline')}{x.get('flight_number')}" for x in resp.get('flights').get(flight.get('flight')).get('segments')])})
        longer_than_20 = [flight for flight in resp.get('itineraries').get('outbound') if resp.get('flights').get(flight.get('flight')).get('duration')/3600 > 20 and resp.get('flights').get(flight.get('flight')).get('segments')[0].get('departure').get('airport') in ["AMS", "DUS", "ANR", "EIN", "RTM", "MST", "GRQ", "CGN", "FMO", "BRU"] and "SK" not in resp.get('flights').get(flight.get('flight')).get('segments')[0].get('airline') ][:2]
        datamore20 = {"data": []}
        for flight in longer_than_20:
            datamore20.get("data").append({"price": flight.get('min_round_trip_price')/100, "flightTime": resp.get('flights').get(flight.get('flight')).get('duration'), "dates":dates, "departTime": resp.get('flights').get(flight.get('flight')).get('segments')[0].get('departure').get('time'), "arrivTime": resp.get('flights').get(flight.get('flight')).get('segments')[-1].get('arrival').get('time'), "depAirport": resp.get('flights').get(flight.get('flight')).get('segments')[0].get('departure').get('airport'), "arrAirport": resp.get('flights').get(flight.get('flight')).get('segments')[-1].get('arrival').get('airport'), "ports": "-".join([ f"{x.get('airline')}{x.get('flight_number')}" for x in resp.get('flights').get(flight.get('flight')).get('segments')])})
        return [dataless20, datamore20]
        ## , "HAJ", "BRE", "BRU", "FRA"


    async def get_conv(self):
        n = 0
        while n <= 3:
            if n == 3:
                return []
            z = await to_thread(requests.get, url="https://wise.com/rates/live?source=USD&target=EUR&", headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'})
            if z.status_code != 200:
                await sleep(5)
                n += 1
                continue
            break
        zet  = z.json()
        return zet.get("value")

    async def update_show(self, departdate, returndate) -> None:
        dates = [departdate, returndate]
        url_de = f"""https://skiplagged.com/api/search.php?from=germany&to=japan&depart={departdate}&return={returndate}&format=v3&counts%5Badults%5D=2&counts%5Bchildren%5D=0&filters=%7B"types"%3A%7B"standard"%3Afalse%2C"hiddenCity"%3Atrue%7D%7D"""
        url_nl = f"""https://skiplagged.com/api/search.php?from=netherlands&to=japan&depart={departdate}&return={returndate}&format=v3&counts%5Badults%5D=2&counts%5Bchildren%5D=0&filters=%7B"types"%3A%7B"standard"%3Afalse%2C"hiddenCity"%3Atrue%7D%7D"""
        url_be = f"""https://skiplagged.com/api/search.php?from=belgium&to=japan&depart={departdate}&return={returndate}&poll=true&format=v3&counts%5Badults%5D=2&counts%5Bchildren%5D=0&filters=%7B"types"%3A%7B"standard"%3Afalse%2C"hiddenCity"%3Atrue%7D%7D"""
        results = await gather(*[self.searchflights(url, dates) for url in [url_de, url_nl, url_be] ])
        # print(results)
        less20 =  []
        more20 = []
        for res in results:
            less20.extend(res[0].get("data"))
            more20.extend(res[1].get("data"))
        return [less20, more20]

    async def gendates(self, date):
        dates = [date]
        dates.extend([date+timedelta(days=xyz) for xyz in range(18, 27)])
        return [ f"{day:%Y-%m-%d}" for day in dates ]

    async def embedfields(self, data):
            shortenedurl = await self.url_shortener(data)
            name = f"€{data.get('price')*self.currconv:.2f} || {data.get('dates')[0][5:]}({data.get('flightTime')//3600}h{data.get('flightTime')%3600//60}m) → {data.get('dates')[1][5:]}" 
            value = f"[Dep: {data.get('departTime')[5:-3]}\nArr: {data.get('arrivTime')[5:-3]}]({shortenedurl})"
            return [name, value]


    @tasks.loop(hours=6.0)
    async def main(self):
        self.currconv = await self.get_conv()
        dates = await self.generate_date_range(datetime(2023, 9, 1), datetime(2023, 11, 1))
        departandreturndates = await gather(*[self.gendates(date) for date in dates])
        all_data = {"data": []}
        for d in departandreturndates:
            allres = await gather(*[ self.update_show(d[0], x) for x in d[1:]])
            for res in allres:
                all_data.get("data").extend(res[0])
                all_data.get("data").extend(res[1])
        sorted_all_data = sorted(all_data.get("data"), key=lambda x: x["price"])
        # departures = sorted(list(set([data.get('depAirport') for data in sorted_all_data])), key=str.lower)
        for dep in sorted(list(set([data.get('depAirport') for data in sorted_all_data])), key=str.lower):
            lowest_price_under_24 = next((x['price'] for x in sorted_all_data if 'AMS' in x['depAirport'] and x['flightTime'] <= 20 * 3600), 1810)
            lowest_price_above_24 = next((x['price'] for x in sorted_all_data if 'AMS' in x['depAirport'] and x['flightTime'] > 20 * 3600), 1760)
            if "AMS" in dep:
                lowest_price_under_24 = 1810
                lowest_price_above_24 = 1760
            data = [ data for data in sorted_all_data if dep in data.get('depAirport') ]
            arrivals = sorted(list(set([data.get('arrAirport') for data in data])), key=str.lower)
            for arr in arrivals:
                arrdata = [ data for data in data if arr in data.get('arrAirport') ]
                if (emb1list:=[data for data in arrdata if data.get('price') < lowest_price_under_24 and data.get('flightTime') <= 20*3600 ]):
                    embed1 = disnake.Embed(title=f"{dep}→{arr} <20h (Skiplagged)")
                    embedvals = await gather(*[self.embedfields(date) for date in emb1list[:10]])
                    for emb in embedvals:
                        embed1.add_field(name=emb[0], value=emb[1])
                    await self.bot.get_channel(679029900299993113).send(embed=embed1)
                if (emb2list:=[data for data in arrdata if data.get('price') < lowest_price_above_24 and data.get('flightTime') > 20*3600]):
                    embed2 = disnake.Embed(title=f"{dep}→{arr} >20h (Skiplagged)")
                    embedvals = await gather(*[self.embedfields(date) for date in emb2list[:10]])
                    for emb in embedvals:
                        embed2.add_field(name=emb[0], value=emb[1])
                    await self.bot.get_channel(679029900299993113).send(embed=embed2)



    
def setup(bot):
    bot.add_cog(skiplaggedcog(bot))