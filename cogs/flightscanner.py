import requests
from datetime import datetime, timedelta
import time
import json
from asyncio import run, gather, to_thread, sleep
from disnake.ext import commands, tasks
import disnake
from cryptography.fernet import Fernet
from fake_useragent import UserAgent

baseurl = "https://flights.booking.com/flights/X/"

async def generate_date_range(vacation_range: tuple[datetime], vacation_length: tuple[int]):
    date_range = []
    current_date = vacation_range[0]

    while current_date + timedelta(days=vacation_length[0]) <= vacation_range[1]:
        date_range.append([f"{current_date + timedelta(days=xyz):%Y-%m-%d}" for xyz in [0, *range(*vacation_length)] if current_date + timedelta(days=xyz) <= vacation_range[1]])
        current_date += timedelta(days=1)

    return date_range

async def split_into_chunks_comp(data_list, chunk_size=3):
  """Splits a list into sublists of at most chunk_size."""
  if not isinstance(data_list, list):
      raise TypeError("Input must be a list.")
  if not isinstance(chunk_size, int) or chunk_size <= 0:
      raise ValueError("chunk_size must be a positive integer.")

  return [data_list[i : i + chunk_size] for i in range(0, len(data_list), chunk_size)]



class flightcog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.decoder = Fernet(self.bot._enckey)
        self.geoapi = self.decoder.decrypt(b'gAAAAABlvt_UBZV3G4oQoeIz74m3Y6oiTsRCOYgXGsvhYvL2AI0bGeGGuckDUY9A5esg-XUYQ0PzslUYqyIgRMFJlPL0wSTTZTATiSudSQOCL2FpLqJKC64=').decode()
        #self.flightscanner.start()
        

    def cog_unload(self) -> None:
        pass
        #self.flightscanner.cancel()


    @commands.slash_command()
    async def searchflights(self,
        inter: disnake.ApplicationCommandInteraction,
        roundtrip: bool,
        nradults: int,
        vaclength: str,
        startperiod: str,
        endperiod: str,
        savesearch: bool,
        agechildren: str = "",
        depcity: str = None,
        arrcity: str = None,
        depcountry: str = None,
        arrcountry: str = None
    ):
        """
        search for flights

        Parameters
        ----------
        roundtrip: Is the flight a roundtrip
        nradults: number of adults flying
        vaclength: length op vacation (5-10) days
        startperiod: search within this period start
        endperiod: search within this period end
        savesearch: repeatedly search for flights
        agechildren: age of children flying (2,4,7)
        depcity: departure cities (Amsterdam,Dusseldorf)
        arrcity: arrival cities (Amsterdam,Dusseldorf)
        depcountry: departure countries (Netherlands,Belgium)
        arrcountry: arrival countries (Netherlands,Belgium)
        """
        ua = UserAgent()
        headers = {
            "User-Agent": ua.random
        }
        url = "https://data.opendatasoft.com/api/explore/v2.1/catalog/datasets/airports-code@public/records?select=column_1%2Ccity_name%2Ccountry_name&order_by=country_name&limit=100&where="
        if depcountry:
            res = await to_thread(requests.get, f"{url}{'%20or%20'.join([f'country_name=%22{c.title()}%22' for c in depcountry.split(',')])}", headers = headers)
            self.depcity = [f"{x.get('column_1')}.AIRPORT" for x in res.json().get("results")]
        elif depcity:
            res = await to_thread(requests.get, f"{url}{'%20or%20'.join([f'city_name=%22{c.title()}%22%20or%20airport_name%20LIKE%20%22{c}%22' for c in depcity.split(',')])}", headers = headers)
            self.depcity = [f"{x.get('column_1')}.AIRPORT" for x in res.json().get("results")]
        if arrcountry:
            res = await to_thread(requests.get, f"{url}{'%20or%20'.join([f'country_name=%22{c.title()}%22' for c in arrcountry.split(',')])}", headers = headers)
            self.arrcity = [f"{x.get('column_1')}.AIRPORT" for x in res.json().get("results")]
        elif arrcity:
            res = await to_thread(requests.get, f"{url}{'%20or%20'.join([f'city_name=%22{c}%22%20or%20airport_name%20LIKE%20%22{c.title()}%22' for c in arrcity.split(',')])}", headers = headers)
            self.arrcity = [f"{x.get('column_1')}.AIRPORT" for x in res.json().get("results")]
        self.vacmin, self.vacmax = vaclength.split('-')
        self.depday, self.depmonth, self.depyear = startperiod.split('-')
        self.retday, self.retmonth, self.retyear = endperiod.split('-')
        self.roundtrip = roundtrip
        self.nradults = nradults
        self.agechildren = '%2C'.join(agechildren.split())
        await inter.send("we do be searching", ephemeral=True, delete_after=15)
        await self.flightscanner()


    @commands.slash_command()
    async def searchflightsfromhome(self,
        inter: disnake.ApplicationCommandInteraction,
        roundtrip: bool,
        nradults: int,
        vaclength: str,
        startperiod: str,
        endperiod: str,
        savesearch: bool,
        homecity: str,
        homemaxdistance: int,
        arrcity: str = None,
        arrmaxdistance: int = None,
        agechildren: str = "",
        arrcountry: str = None,
        arrairports: str = None,
    ):
        """
        search for flights with airports within x km

        Parameters
        ----------
        roundtrip: Is the flight a roundtrip
        nradults: number of adults flying
        vaclength: length op vacation (5-10) days
        startperiod: search within this period start
        endperiod: search within this period end
        savesearch: repeatedly search for flights
        agechildren: age of children flying (2 4 7)
        homecity: city you depart from
        homemaxdistance: look for airports within this range in km
        arrcity: city you want to go to
        arrmaxdistance: look for airports within this range in km
        """
        await inter.send("we do be searching", ephemeral=True, delete_after=15)

        ua = UserAgent()
        headers = {
            "User-Agent": ua.random
        }
        
        geohome = await to_thread(requests.get, f"https://geocode.maps.co/search?q={homecity}&api_key={self.geoapi}", headers = headers)
        lathome, lonhome = geohome.json()[0].get("lat"), geohome.json()[0].get("lon")
        geourlshome = f"https://data.opendatasoft.com/api/explore/v2.1/catalog/datasets/airports-code@public/records?select=column_1&order_by=country_name&limit=100&where=latitude%3C{float(lathome)+(1/111*homemaxdistance)}%20and%20latitude%3E{float(lathome)-(1/111*homemaxdistance)}%20and%20longitude%3C{float(lonhome)+(1/111*homemaxdistance)}%20and%20longitude%3E{float(lonhome)-(1/111*homemaxdistance)}"
        res = await to_thread(requests.get, geourlshome, headers = headers)
        self.depcity = [f"{x.get('column_1')}.AIRPORT" for x in res.json().get("results")]
        if arrcity:
            geoarr = await to_thread(requests.get, f"https://geocode.maps.co/search?q={arrcity}&api_key={self.geoapi}", headers = headers)
            latarr, lonarr = geoarr.json()[0].get("lat"), geoarr.json()[0].get("lon")
            geourlsarr = f"https://data.opendatasoft.com/api/explore/v2.1/catalog/datasets/airports-code@public/records?select=column_1&order_by=country_name&limit=100&where=latitude%3C{float(latarr)+(1/111*arrmaxdistance)}%20and%20latitude%3E{float(latarr)-(1/111*arrmaxdistance)}%20and%20longitude%3C{float(lonarr)+(1/111*arrmaxdistance)}%20and%20longitude%3E{float(lonarr)-(1/111*arrmaxdistance)}"
            res = await to_thread(requests.get, geourlsarr, headers = headers)
            self.arrcity = [f"{x.get('column_1')}.AIRPORT" for x in res.json().get("results")]
        elif arrcountry:
            res = await to_thread(requests.get, f"https://data.opendatasoft.com/api/explore/v2.1/catalog/datasets/airports-code@public/records?select=column_1%2Ccity_name%2Ccountry_name&order_by=country_name&limit=100&where={'%20or%20'.join([f'country_name=%22{c.title()}%22' for c in arrcountry.split(',')])}", headers = headers)
            self.arrcity = [f"{x.get('column_1')}.AIRPORT" for x in res.json().get("results")]
        elif arrairports:
            self.arrcity = [f"{x.upper()}.AIRPORT" for x in arrairports.split(',')]
        self.vacmin, self.vacmax = vaclength.split('-')
        self.depday, self.depmonth, self.depyear = startperiod.split('-')
        self.retday, self.retmonth, self.retyear = endperiod.split('-')
        self.roundtrip = roundtrip
        self.nradults = nradults
        self.agechildren = '%2C'.join(agechildren.split(','))
        await inter.send("we do be searching", ephemeral=True, delete_after=15)
        await self.flightscanner()

    async def look_for_flights(self, departureTerminals, arrivalTerminals, departdate, returndate) -> None:
        ua = UserAgent()
        headers = {
            "User-Agent": ua.random
        }
        self.roundtripconf = "ROUNDTRIP"
        if not self.roundtrip:
            self.roundtripconf = "ONEWAY"
            #    "https://flights.booking.com/api/flights/?type=ROUNDTRIP&adults=5&cabinClass=ECONOMY&children=1%2C3&from=AMS.AIRPORT%2CGNE.AIRPORT&to=LIS.AIRPORT%2CZYF.AIRPORT&depart=2025-05-20&return=2025-06-08&sort=CHEAPEST"
        url = f"https://flights.booking.com/api/flights/?type={self.roundtripconf}&adults={self.nradults}&cabinClass=ECONOMY&children={self.agechildren}&from={'%2C'.join(departureTerminals)}&to={'%2C'.join(arrivalTerminals)}&depart={departdate}&return={returndate}&sort=CHEAPEST"
        n = 1
        while n:
            if n == 10:
                return []
            r = await to_thread(requests.get, url, headers = headers)
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
        realret = [{"dates": [departdate, returndate], "price": int(x.get('priceBreakdown').get('total').get('units')) + int(x.get('extraProducts')[0].get('priceBreakdown').get('total').get('units')) if ( not x.get('segments')[0].get('travellerCheckedLuggage') and x.get('extraProducts') and x.get('extraProducts')[0].get('type') == 'checkedInBaggage' ) else int(x.get('priceBreakdown').get('total').get('units')), "flightTime": x.get('segments')[0].get('totalTime'), "flightTimeback": x.get('segments')[1].get('totalTime'), "depart": x.get('segments')[0].get('departureAirport').get('code'), "arriv": x.get('segments')[0].get('arrivalAirport').get('code'), "departTime": x.get('segments')[0].get('departureTime'), "arrivTime": x.get('segments')[0].get('arrivalTime'), "token": x.get('token')} for x in retdict if int(x.get('priceBreakdown').get('total').get('units')) < 10000 ]
        return realret
        
    async def url_shortener(self, data):
        ua = UserAgent()
        headers = {
            "User-Agent": ua.random
        }
        api_url = "https://is.gd/create.php"
        param = {'format': 'simple', 'url': f"{baseurl}{data.get('token')}"}
        n = 0
        while n <= 2:
            if n == 2:
                return f"https://flights.booking.com/flights/X/?type={self.roundtripconf}&adults={self.nradults}&children={self.agechildren}&cabinClass=ECONOMY&from={self.dep}.AIRPORT&to={self.arr}.AIRPORT&depart={data.get('dates')[0][:10]}&return={data.get('dates')[1][:10]}&sort=CHEAPEST"
            response = await to_thread(requests.get, url=api_url, params=param, headers = headers)
            if response.status_code != 200:
                await sleep(3)
                n += 1
                continue
            break
        return response.text.strip()
    

    async def embedfields(self, data):
        shortenedurl = await self.url_shortener(data)
        # shortenedurl = f"https://flights.booking.com/flights/X/?type={roundtrip}&adults={self.nradults}&cabinClass=ECONOMY&from={self.dep}.AIRPORT&to={self.arr}.AIRPORT&depart={data.get('dates')[0][:10]}&return={data.get('dates')[1][:10]}&sort=CHEAPEST"
        name = f"€{data.get('price')} || {data.get('dates')[0][5:]}({data.get('flightTime')//3600}h{data.get('flightTime')%3600//60}m) → {data.get('dates')[1][5:]}({data.get('flightTimeback')//3600}h{data.get('flightTimeback')%3600//60}m)" 
        value = f"[Dep: {data.get('departTime')[5:-3]}\nArr: {data.get('arrivTime')[5:-3]}]({shortenedurl})"
        return [name, value]
    

    async def flightscanner(self):
        dates = await generate_date_range(vacation_range=(datetime(int(self.depyear),int(self.depmonth), int(self.depday)), datetime(int(self.retyear), int(self.retmonth), int(self.retday))), vacation_length=(int(self.vacmin), int(self.vacmax)))
        my_dict = {"data": []}
        departcitiessplit = await split_into_chunks_comp(self.depcity, chunk_size=3)
        arrcitiessplit = await split_into_chunks_comp(self.arrcity, chunk_size=3)
        for dprt in departcitiessplit:
            for ari in arrcitiessplit:
                for d in dates:
                    allres = await gather(*[ self.look_for_flights(dprt, ari, d[0], x) for x in d[1:]])
                    for x in allres:
                        my_dict.get("data").extend(x)
                    await sleep(2)
        sorted_data = sorted(my_dict["data"], key=lambda x: x["price"])
        await self.sendflightstodiscord(sorted_data)


    async def sendflightstodiscord(self, sorteddata):
        sorted_data = sorteddata
        departures = sorted(list(set([data.get('depart') for data in sorted_data])), key=str.lower)
        for dep in departures:
            lowest_price_under_24 = next((x['price'] for x in sorted_data if 'AMS' in x['depart'] and x['flightTime'] <= 20 * 3600), 5000)
            lowest_price_above_24 = next((x['price'] for x in sorted_data if 'AMS' in x['depart'] and x['flightTime'] > 20 * 3600), 5000)
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
