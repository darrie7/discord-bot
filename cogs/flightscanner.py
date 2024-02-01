import requests
from datetime import datetime, timedelta
import time
import json
from asyncio import run, gather, to_thread, sleep
from disnake.ext import commands, tasks
import disnake

baseurl = "https://flights.booking.com/flights/X/"

async def generate_date_range(vacation_range: tuple[datetime], vacation_length: tuple[int]):
    date_range = []
    current_date = vacation_range[0]

    while current_date + timedelta(days=vacation_length[0]) <= vacation_range[1]:
        date_range.append([f"{current_date + timedelta(days=xyz):%Y-%m-%d}" for xyz in [0, *range(*vacation_length)] if current_date + timedelta(days=xyz) <= vacation_range[1]])
        current_date += timedelta(days=1)

    return date_range


class flightcog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.flightscanner.start()
        

    def cog_unload(self) -> None:
        self.flightscanner.cancel()


    @commands.slash_command()
    async def lookupflight(self,
        inter: disnake.ApplicationCommandInteraction,
        dep_airp: str,
        arr_airp: str,
        vac_min: int,
        vac_max: int,
        dep_year: int = commands.Param(choices=[i for i in range(int(datetime.now().year), int(datetime.now().year)+5)]),
        dep_month: int = commands.Param(choices=[i for i in range(1, 13)]),
        dep_day: int = commands.Param(choices=[i for i in range(1, 32)]),
        ret_year: int = commands.Param(choices=[i for i in range(int(datetime.now().year), int(datetime.now().year)+5)]),
        ret_month: int = commands.Param(choices=[i for i in range(1, 13)]),
        ret_day: int = commands.Param(choices=[i for i in range(1, 32)])
    ):
        await inter.response.send_message(dep_airp, arr_airp, vac_min, vac_max, dep_year, dep_month, dep_day)

    async def look_for_flights(self, departureTerminals, arrivalTerminals, departdate, returndate) -> None:
        # self.arrivalTerminal = ["OSA.CITY"] if not self.arrivalTerminal == ["OSA.CITY"] else ["TYO.CITY"]
        url = f"https://flights.booking.com/api/flights/?type=ROUNDTRIP&adults=2&cabinClass=ECONOMY&children=&from={'%2C'.join(departureTerminals)}&to={'%2C'.join(arrivalTerminals)}&depart={departdate}&return={returndate}&sort=CHEAPEST&travelPurpose=leisure&duration=33"
        n = 1
        while n:
            if n == 101:
                return []
            r = await to_thread(requests.get, url)
            if r.status_code != 200:
                await sleep(5)
                n += 1
                continue
            break
        resp = r.json()
        if not resp.get('flightOffers'):
            return []
        flight = [fly for fly in resp.get('flightOffers')]
        retdict = [fl for fl in flight if (fl.get('segments')[0].get('travellerCheckedLuggage') or fl.get('extraProducts'))]
        realret = [{"dates": [departdate, returndate], "price": int(x.get('priceBreakdown').get('total').get('units')) + int(x.get('extraProducts')[0].get('priceBreakdown').get('total').get('units')) if ( not x.get('segments')[0].get('travellerCheckedLuggage') and x.get('extraProducts') and x.get('extraProducts')[0].get('type') == 'checkedInBaggage' ) else int(x.get('priceBreakdown').get('total').get('units')), "flightTime": x.get('segments')[0].get('totalTime'), "flightTimeback": x.get('segments')[1].get('totalTime'), "depart": x.get('segments')[0].get('departureAirport').get('code'), "arriv": x.get('segments')[0].get('arrivalAirport').get('code'), "departTime": x.get('segments')[0].get('departureTime'), "arrivTime": x.get('segments')[0].get('arrivalTime'), "token": x.get('token')} for x in retdict if int(x.get('priceBreakdown').get('total').get('units')) < 1700 ]
        return realret
        
    async def url_shortener(self, data):
        api_url = "https://is.gd/create.php"
        param = {'format': 'simple', 'url': f"{baseurl}{data.get('token')}"}
        n = 0
        while n <= 2:
            if n == 2:
                return f"https://flights.booking.com/flights/X/?type=ROUNDTRIP&adults=2&cabinClass=ECONOMY&from={self.dep}.AIRPORT&to={self.arr}.AIRPORT&depart={data.get('dates')[0][:10]}&return={data.get('dates')[1][:10]}&sort=CHEAPEST"
            response = await to_thread(requests.get, url=api_url, params=param)
            if response.status_code != 200:
                await sleep(3)
                n += 1
                continue
            break
        return response.text.strip()
    

    async def embedfields(self, data):
        shortenedurl = await self.url_shortener(data)
        # shortenedurl = f"https://flights.booking.com/flights/X/?type=ROUNDTRIP&adults=2&cabinClass=ECONOMY&from={self.dep}.AIRPORT&to={self.arr}.AIRPORT&depart={data.get('dates')[0][:10]}&return={data.get('dates')[1][:10]}&sort=CHEAPEST"
        name = f"€{data.get('price')} || {data.get('dates')[0][5:]}({data.get('flightTime')//3600}h{data.get('flightTime')%3600//60}m) → {data.get('dates')[1][5:]}({data.get('flightTimeback')//3600}h{data.get('flightTimeback')%3600//60}m)" 
        value = f"[Dep: {data.get('departTime')[5:-3]}\nArr: {data.get('arrivTime')[5:-3]}]({shortenedurl})"
        return [name, value]
    
    @tasks.loop(hours=500.0)
    async def flightscanner(self):
        dates = await generate_date_range(vacation_range=(datetime(2024,9, 1), datetime(2024, 9, 30)), vacation_length=(9, 10))
        my_dict = {"data": []}
        for d in dates:
            allres = await gather(*[ self.look_for_flights(["AMS.AIRPORT", "DUS.AIRPORT", "ANR.AIRPORT", "EIN.AIRPORT", "RTM.AIRPORT", "MST.AIRPORT", "GRQ.AIRPORT", "CGN.AIRPORT"], ["YVR.CITY"], d[0], x) for x in d[1:]])
            for x in allres:
                my_dict.get("data").extend(x)
            await sleep(2)
        sorted_data = sorted(my_dict["data"], key=lambda x: x["price"])
        await self.sendflightstodiscord(sorted_data)


    async def sendflightstodiscord(self, sorteddata):
        sorted_data = sorteddata
        departures = sorted(list(set([data.get('depart') for data in sorted_data])), key=str.lower)
        for dep in departures:
            lowest_price_under_24 = next((x['price'] for x in sorted_data if 'AMS' in x['depart'] and x['flightTime'] <= 20 * 3600), 1650)
            lowest_price_above_24 = next((x['price'] for x in sorted_data if 'AMS' in x['depart'] and x['flightTime'] > 20 * 3600), 1610)
            if "AMS" in dep:
                lowest_price_under_24 = 1650
                lowest_price_above_24 = 1610
            data = [ data for data in sorted_data if dep in data.get('depart') ]
            arrivals = sorted(list(set([ data.get('arriv') for data in data ])), key=str.lower)
            for arr in arrivals:
                self.dep = dep
                self.arr = arr
                # the_flights = list()
                shorter_than_24 = list()
                longer_than_24 = list()
                to_dest = [ x for x in sorted_data if (dep in x.get('depart') and arr in x.get('arriv')) ]
                dest_dep_dates = set([data.get('dates')[0] for data in to_dest])
                for dest_dep_day in dest_dep_dates:
                    dest_dep = [ data for data in to_dest if data.get('dates')[0] == dest_dep_day ]
                    dest_arr_dates = set([ data.get('dates')[1] for data in dest_dep ])
                    for dest_arr_day in dest_arr_dates:
                        extra = sorted([ data for data in dest_dep if data.get('dates')[1] == dest_arr_day ], key=lambda x: x["price"])
                        arr_times = set([ data.get('arrivTime') for data in extra ])
                        for arr_t in arr_times:
                            # the_flights.append([data for data in extra if data.get('arrivTime') == arr_t ][0])
                            shorter_than_24.append(next((data for data in extra if (data.get('arrivTime') == arr_t and data.get('price') < lowest_price_under_24 and data.get('flightTime') <= 20*3600 )), None))
                            longer_than_24.append(next((data for data in extra if (data.get('arrivTime') == arr_t and data.get('price') < lowest_price_above_24 and data.get('flightTime') > 20*3600 )), None))
                # if (shorter_than_24:=sorted([ x for x in the_flights if (x.get('flightTime') <= 20*3600 and x.get('price') < lowest_price_under_24)], key=lambda x: x.get('price'))):
                if [ x for x in shorter_than_24 if x ]:
                    embed2 = disnake.Embed(title=f"{dep}→{arr} <20h")
                    embedvals = await gather(*[self.embedfields(date) for date in sorted([ x for x in shorter_than_24 if x ], key=lambda x: x["price"])[0:20]])
                    for emb in embedvals:
                        embed2.add_field(name=emb[0], value=emb[1])
                    await self.bot.get_channel(679029900299993113).send(embed=embed2)
                # if (longer_than_24:=sorted([ x for x in the_flights if (x.get('flightTime') > 20*3600 and x.get('price') < lowest_price_above_24)], key=lambda x: x.get('price'))):
                if [x for x in longer_than_24 if x ]:
                    embed2 = disnake.Embed(title=f"{dep}→{arr} >20h")
                    embedvals = await gather(*[self.embedfields(date) for date in sorted([ x for x in longer_than_24 if x ], key=lambda x: x["price"])[0:20]])
                    for emb in embedvals:
                        embed2.add_field(name=emb[0], value=emb[1])
                    await self.bot.get_channel(679029900299993113).send(embed=embed2)

    
def setup(bot):
    bot.add_cog(flightcog(bot))
