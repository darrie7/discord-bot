import disnake
from disnake.ext import commands, tasks
import pytchat
import asyncio
import datetime as dt
import pytz
from google_trans_new import google_translator


class MyCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.english = ["en", "eng", "trans", "日本/en"]
        self.spanish = ["es", "esp"]
        self.tags = [("[", "]"), ("(", ")"), ("", "-"), ("【", "】"), ("", ":"), ("", "~"), ("", " "), ("{", "}"), ("<", ">"), ("|", "|"), ("「", "」"), ("『", "』"), ("〚", "〛"), ("〈", "〉")]
        

    @commands.command(name='translations', aliases=['tl'])
    async def translations(self, ctx, *, args: str):
        try:
            lang = args.split(" ")[1].lower()
            if any(l in lang for l in ["english","eng","en"]):
                language = self.english
                await ctx.message.add_reaction("🇬🇧")
            elif any(l in lang for l in ["spanish","esp","es"]):
                language = self.spanish
                await ctx.message.add_reaction("🇪🇸")
            elif "custom" in lang:
                language = args.split(" ")[2].split(",")
                await ctx.message.add_reaction("🏳️")
        except:
            language = self.english
            await ctx.message.add_reaction("🇬🇧")
        all = []
        for lng in language:
            for tag in self.tags:
                all.append(f"{tag[0]}{lng}{tag[1]}")
                all.append(f"{lng}{tag[1]}")
        self.all = list(dict.fromkeys(all))
        self.id=args.split(" ")[0]
        self.ctx = ctx
        self.translator = google_translator()
        self.maintrans.start()


    @tasks.loop()
    async def maintrans(self):
        self.livechat = pytchat.LiveChatAsync(self.id, callback = self.func)
        while self.livechat.is_alive():
            await asyncio.sleep(1)
            #other background operation.
        else:
            await self.ctx.send(content=f"*[{dt.datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%H:%M:%S')}]* LiveChat has ended")
            self.maintrans.cancel()


        #callback function is automatically called periodically.
    async def func(self, chatdata):
        for c in chatdata.items:
            if any(c.message.lower().startswith((tagsave := tag)) for tag in self.all):
                await self.ctx.send(content=f"_[{dt.datetime.fromtimestamp(int(c.timestamp)/1000).astimezone(pytz.timezone('Asia/Tokyo')).strftime('%H:%M:%S')}|{c.author.name}]_ 💬: {c.message[c.message.lower().find(tagsave)+len(tagsave):].strip().lstrip('💬').lstrip(':')}")
            elif c.author.isChatOwner or c.author.isChatModerator:
                await self.ctx.send(content=f"_[{dt.datetime.fromtimestamp(int(c.timestamp)/1000).astimezone(pytz.timezone('Asia/Tokyo')).strftime('%H:%M:%S')}|{c.author.name}]_ 💬TL: {self.translator.translate(c.message,lang_tgt='en')}")
            await chatdata.tick_async()


    @commands.command(name='terminate', aliases=['tm'])
    async def terminate(self, ctx):
        try:
            if self.livechat.is_alive():
                self.livechat.terminate()
                self.maintrans.cancel()
                await ctx.send(content="Terminated")
            else:
                await ctx.send(content="Nothing to terminate")
        except Exception as e:
            print(type(e), str(e))
            await ctx.send(content="Nothing to terminate")
            
            
    @commands.command(name='copy', aliases=['cp'])
    async def copy(self, ctx, *, args: str):
        await ctx.send(content=args)


def setup(bot):
    bot.add_cog(MyCommandsCog(bot))
