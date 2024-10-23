from disnake.ext import commands, tasks
import disnake
import requests
from asyncio import to_thread
from bs4 import BeautifulSoup
import json
from parsel import Selector

async def parse_productParams(script_with_data):
    """parse product HTML page for product data"""
    # extract data using a regex pattern:
    data = json.loads(script_with_data[0])
    r = await to_thread(requests.get,
                        url = data["descriptionModule"]["descriptionUrl"],
                        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36', "Accept-Language": "en"}
                        )
    soup = BeautifulSoup(r.text, features="html.parser")
    product = {
        "name": data["titleModule"]["subject"],
        "price": [data["priceModule"].get("formatedActivityPrice"), data["priceModule"].get("formatedPrice")],
        "variants": [],
        "images": data["imageModule"]["imagePathList"],
        "description": soup.get_text().strip(),
        "description_images": list(set([img.get("src") for img in soup.find_all("img")]))
                            }
    # every product variant has it's own price and ID number (sku):
    for sku in data["skuModule"]["productSKUPropertyList"]:
        product["variants"].append(
            {
                "name": sku["skuPropertyName"],
                "options": [skuprop["propertyValueDisplayName"] for skuprop in sku["skuPropertyValues"]]
            }
        )
    # data variable contains much more information - so feel free to explore it,
    # but to keep things brief we focus on essentials in this article
    return product


async def parse_productdida(script_with_data):
    """parse product HTML page for product data"""
    # extract data using a regex pattern:
    data = json.loads(f"""{{"data": {script_with_data[0]}""")
    r = await to_thread(requests.get,
                        url = data['data']['data']['description_2253']['fields']['detailDesc'],
                        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36', "Accept-Language": "en"}
                        )
    soup = BeautifulSoup(r.text, features="html.parser")
    product = {
        "name": data['data']['data']['titleBanner_2440']['fields']['subject'],
        "price": [ data['data']['data']['price_2256']['fields']['formatedActivityPrice'], data['data']['data']['price_2256']['fields']['formatedPrice'] ],
        "variants": [],
        "images": data['data']['data']['imageView_2247']['fields']['imageList'],
        "description": soup.get_text().strip(),
        "description_images": list(set([img.get("src") for img in soup.find_all("img")]))
                            }
    # every product variant has it's own price and ID number (sku):
    for sku in data['data']['data']['sku_2257']['fields']['propertyList']:
        product["variants"].append(
            {
                "name": sku['skuPropertyName'],
                "options": [skuprop['propertyValueName'] for skuprop in sku['skuPropertyValues']]
            }
        )
    # data variable contains much more information - so feel free to explore it,
    # but to keep things brief we focus on essentials in this article
    return product

class AliexpressCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        
        
    def cog_unload(self) -> None:
        pass


    @commands.slash_command(guild_ids=[self.bot._guildid])
    async def aliexpress(self, inter: disnake.ApplicationCommandInteraction, link: str) -> None:
        """
        Scrape Aliexpress

        Parameters
        ----------
        link: Aliexpress Link
        """
        await inter.response.defer()
        link  = f"""{link.split(".html")[0]}.html"""
        link = link.replace("m.ali", "www.ali").replace("nl.ali", "www.ali").replace("/i/", "/item/")
        r = await to_thread(requests.get, 
                    url = link,
                    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36', "Accept-Language": "en"}
                   # proxies = self.proxies,
                    )
        sel = Selector(text=r.text)
    # find the script tag containing our data:
        script_with_data = sel.xpath('//script[contains(text(),"window.runParams")]').re(r'data: ({.+?}),\n')
        if script_with_data != []:
            prodinfo = await parse_productParams(script_with_data)
        else:
            script_with_data2 = sel.xpath('//script[contains(text(),"window._dida_config_._init_data_")]').re(r'data: ({.*})')
            if script_with_data2 == []:
                return await inter.send("Could not retrieve information")
            prodinfo = await parse_productdida(script_with_data2)
        vari = [f"""**{prodinfo.get("name")}**\nActie prijs: ***{prodinfo.get("price")[0]}***\nGewone prijs: ***{prodinfo.get("price")[1]}***"""]
        for x in prodinfo.get("variants"):
            varianten = '\n'.join(x.get("options"))
            vari.append(f"""**{x.get("name")}**\nvarianten:\n***{varianten}***""")
        await inter.edit_original_message('\n\n'.join(vari))
        chunks3 = [prodinfo.get("description")[x:x+1950] for x in range(0, len(prodinfo.get("description")), 1950)]
        if chunks3 != []:
            for u in chunks3:
                await inter.send(u)
        await inter.send("***#####AFBEELDINGEN#####***")
        chunks = [prodinfo.get("images")[x:x+2] for x in range(0, len(prodinfo.get("images")), 2)]
        for z in chunks:
            await inter.send("\n".join(z))
        await inter.send("***#####AFBEELDINGEN IN DESCRIPTION#####***")
        chunks2 = [prodinfo.get("description_images")[x:x+2] for x in range(0, len(prodinfo.get("description_images")), 2)]
        for y in chunks2:
            await inter.send("\n".join(y))
        

def setup(bot):
    bot.add_cog(AliexpressCog(bot))
