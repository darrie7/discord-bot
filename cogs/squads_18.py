import disnake
from disnake.ext import commands, tasks
import asyncio
import sys
import random
import time
from datetime import datetime


def check(sqname):
    if "trio" in sqname.lower():
        return 3
    if "duo" in sqname.lower():
        return 2
    if any(x in sqname.lower() for x in ["in-house", "in house", "inhouse"]):
        return 10
    else:   
        return 5
    
    
async def everything(self, line, embed, inter, the_msg):
    max_players = check(line["name"])
    main = await asyncio.gather(*[ inter.guild.fetch_member(el) for el in line["participants"] ])
    # main = await ctx.guild.getch_members(line["participants"])
    main_names = [ l.display_name for l in main ]
    embed = embed
    embed.color=3732110
    embed.title = f'''⚔️ {main_names[0]} is hosting a game | {line["name"]}'''
    liste = [ f"🐵 {l}" for l in main_names ]
    embed.description = f"***Participants:***\n**{chr(10).join(liste)}**"
    if len(main_names) == max_players:
        embed.color = 15879244
    await inter.send(the_msg, embed = embed, components = [ disnake.ui.Button(label="Join", custom_id=f"join+{main[0].id}", style=disnake.ButtonStyle.green), disnake.ui.Button(label="Leave", custom_id=f"leave+{main[0].id}", style=disnake.ButtonStyle.red), disnake.ui.Button(label="Cancel", custom_id=f"cancel+{main[0].id}", style=disnake.ButtonStyle.grey)])
    new_msg = await inter.original_message()
    return new_msg

async def ctx_everything(self, line, embed, ctx, the_msg):
    max_players = check(line["name"])
    main = await asyncio.gather(*[ ctx.guild.fetch_member(el) for el in line["participants"] ])
    # main = await ctx.guild.getch_members(line["participants"])
    main_names = [ l.display_name for l in main ]
    embed = embed
    embed.color=3732110
    embed.title = f'''⚔️ {main_names[0]} is hosting a game | {line["name"]}'''
    liste = [ f"🐵 {l}" for l in main_names ]
    embed.description = f"***Participants:***\n**{chr(10).join(liste)}**"
    if len(main_names) == max_players:
        embed.color = 15879244
    new_msg = await ctx.send(the_msg, embed = embed, components = [ disnake.ui.Button(label="Join", custom_id=f"join+{main[0].id}", style=disnake.ButtonStyle.green), disnake.ui.Button(label="Leave", custom_id=f"leave+{main[0].id}", style=disnake.ButtonStyle.red), disnake.ui.Button(label="Cancel", custom_id=f"cancel+{main[0].id}", style=disnake.ButtonStyle.grey)])
    return new_msg
    

class MyCommandsCog2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(1, 2, commands.BucketType.user)
        self.all_cancel.start()
        
        
    @tasks.loop(minutes=15.0)
    async def all_cancel(self):
        current_time = int(time.time())
        for line in self.bot._db:
            if (current_time - line["time"]) > 3600:
                message = await self.bot.get_channel(line["channel_id"]).fetch_message(line["embed_id"])
                await message.delete()
                self.bot._db.remove(doc_ids = [line.doc_id])
            
        
    async def cog_check(self, ctx):
        bucket = self._cd.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            # You're rate limited, send message here
            await ctx.send(f"Please wait {round(retry_after, 2)} seconds to use this command.", delete_after=2)
            return False
        return True
        
        
    @commands.command(name='options', aliases=['o'])
    async def options(self, ctx):
        await ctx.send("""**Instructions:**
• To join a team type `-join @member` or `-j @member`
• To see which teams are hosted use `-teams` (red embed means team is full; green embed means team is not full)
• To create a new team use `-create <game mode>` or `-c <game mode>` (for example: Ranked Duo, Ranked Trio, ARAM or In-House custom. Team size changes according to mode)
• To leave a team type `-leave` or `-l` or `-x`
• A host can kick someone using `-kick @member`
• A host can cancel the team using `-cancel`
• To see your team use `-t` or `-team`
• To see a specific member's team use `-t @member` or `-team @member`""", delete_after=120)
        await ctx.message.delete()


    @commands.command(name='help', aliases=['h'])
    async def help(self, ctx):
        await ctx.send("""use **-o** or **-options**""", delete_after=120)
        await ctx.message.delete()
        
        
    @commands.command(name='kek', aliases=[])
    async def kek(self, ctx):
        await ctx.send(random.choice(['🐒','🐵','🙈','🙉','🙊','<:poopy:919681849306013726>','<:uhohstinky:919681849310187530>','<:ape:919681849150804018>','<:monkepog:919681849297600562>']), delete_after=120)
        await ctx.message.delete()
        

    @commands.command(name='create', aliases=['cr', 'c'])
    async def create_lobby(self, ctx, *, args: str=""):
        if self.bot._db.search(self.bot._query.participants.any([ctx.message.author.id])):
            await ctx.send('You are already in a team, please leave the team you are in first using **-leave** or use **-t** to view your current team', delete_after=10)
            await ctx.message.delete()
            return
        embed = disnake.Embed()
        embed.set_footer(text=f'Use -options or -o to see all options')
        embed.color=3732110
        embed.timestamp = datetime.now()
        embed.title = f"⚔️ {ctx.message.author.display_name} is hosting a game | {args}"
        embed.description= f"***Participants:***\n**🐵 {ctx.message.author.display_name}**"
        await ctx.send(f"<@{ctx.message.author.id}> is <@&903409059103907850> {args}")
        await ctx.message.delete()
        new_msg = await ctx.send(embed = embed, components = [ disnake.ui.Button(label="Join", custom_id=f"join+{ctx.message.author.id}", style=disnake.ButtonStyle.green), disnake.ui.Button(label="Leave", custom_id=f"leave+{ctx.message.author.id}", style=disnake.ButtonStyle.red), disnake.ui.Button(label="Cancel", custom_id=f"cancel+{ctx.message.author.id}", style=disnake.ButtonStyle.grey)])
        self.bot._db.insert({"name": args, "channel_id": ctx.channel.id, "embed_id": new_msg.id, "time": int(time.time()), "participants": [ctx.message.author.id]})

        
    @commands.command(name='leave', aliases=['l', 'x'])
    async def leave_lobby(self, ctx):
        await ctx.message.delete()
        if not self.bot._db.search(self.bot._query.participants.any([ctx.message.author.id])):
            await ctx.send('You are not in a team.', delete_after=10)
            return
        line = self.bot._db.search(self.bot._query.participants.any([ctx.message.author.id]))[0]
        line["participants"].remove(ctx.message.author.id)
        if len(line["participants"]) < 1:
            oldmess = await ctx.fetch_message(line["embed_id"])
            await oldmess.delete()
            await ctx.send(f"""RIP team | **{line["name"]}**""")
            self.bot._db.remove(doc_ids = [line.doc_id])
            return
        oldmess = await ctx.fetch_message(line["embed_id"])
        msg_con = f"""{ctx.message.author.display_name} has left **{line["name"]}**"""
        new_embed = await ctx_everything(self, line, oldmess.embeds[0], ctx, msg_con)
        await oldmess.delete()
        self.bot._db.update({"participants": line["participants"], "time": int(time.time()), "embed_id": new_embed.id, "channel_id": new_embed.channel.id}, doc_ids = [line.doc_id])
        return
            

    @commands.command(name='join', aliases=['j'])
    async def join_lobby(self, ctx, user: disnake.Member ):
        if self.bot._db.search(self.bot._query.participants.any([ctx.message.author.id])):
            await ctx.send('You are already in a team, please leave the team you are in first using **-leave** or use **-t** to view your current team', delete_after=10)
            return
        if not self.bot._db.search(self.bot._query.participants.any([user.id])):
            await ctx.send(f'**{user.display_name}** is not in a team', delete_after=10)
            return
        line = self.bot._db.search(self.bot._query.participants.any([user.id]))[0]
        max_players = check(line["name"])
        if len(line["participants"]) == max_players:
            await ctx.send(f'This team is full', delete_after=10)
            return
        line["participants"].append(ctx.message.author.id)
        oldmess = await ctx.fetch_message(line["embed_id"])
        msg_con = f"""{ctx.message.author.display_name} has joined **{line["name"]}** {' '.join([f"<@{part}>" for part in line["participants"][0:-1] ])}"""
        new_embed = await ctx_everything(self, line, oldmess.embeds[0], ctx, msg_con)
        await oldmess.delete()
        await ctx.message.delete()
        self.bot._db.update({"participants": line["participants"], "time": int(time.time()), "embed_id": new_embed.id, "channel_id": new_embed.channel.id}, doc_ids = [line.doc_id])
        return
            
            
    @commands.command(name='kick', aliases=['k'])
    async def kick_lobby(self, ctx, user: disnake.Member):
        await ctx.message.delete()
        if user.id == ctx.message.author.id:
            await ctx.send(f'You cannot kick yourself', delete_after=10)
            return
        if not self.bot._db.search(self.bot._query.participants.any([user.id])):
            await ctx.send(f'{user.display_name} is not in a team', delete_after=10)
            return
        if not self.bot._db.search(self.bot._query.participants.any([ctx.message.author.id])):
            await ctx.send(f'You are not in a team', delete_after=10)
            return
        for line in self.bot._db:
            if not all(x in line["participants"] for x in [ctx.message.author.id, user.id]):
                continue
            if ctx.message.author.id != line["participants"][0]:
                await ctx.send(f'You are not the team host', delete_after=10)
                return
            oldmess = await ctx.fetch_message(line["embed_id"])
            line["participants"].remove(user.id)
            msg_con = f"""{user.display_name} has been kicked from **{line["name"]}**"""
            new_embed = await ctx_everything(self, line, oldmess.embeds[0], ctx, msg_con)
            await oldmess.delete()
            self.bot._db.update({"participants": line["participants"], "time": int(time.time()), "embed_id": new_embed.id, "channel_id": new_embed.channel.id}, doc_ids = [line.doc_id])
            return
            
            
    @commands.command(name='cancel', aliases=[])
    async def cancel_lobby(self, ctx):
        await ctx.message.delete()
        if not self.bot._db.search(self.bot._query.participants.any([ctx.message.author.id])):
            await ctx.send(f'You are not in a team', delete_after=10)
            return
        line = self.bot._db.search(self.bot._query.participants.any([ctx.message.author.id]))[0]
        if ctx.message.author.id != line["participants"][0]:
            await ctx.send(f'You are not the team host', delete_after=10)
            return
        oldmess = await ctx.fetch_message(line["embed_id"])
        await oldmess.delete()
        await ctx.send(f"""RIP team | **{line["name"]}**""")
        self.bot._db.remove(doc_ids = [line.doc_id])
        return

               
    @commands.command(name='teams', aliases=[])
    async def lobbies(self, ctx, *, args: str=""):
        found = False
        for line in self.bot._db:
            if all(a.lower() in line["name"].lower() for a in args.split()):
                found = True
                oldmess = await ctx.fetch_message(line["embed_id"])
                embed = oldmess.embeds[0]
                new_msg = await ctx.send(embed=embed, components=[disnake.ui.Button(label=c.label, style=c.style, custom_id=c.custom_id, url=c.url) for c in oldmess.components[0].children])
                await oldmess.delete()
                self.bot._db.update({"embed_id": new_msg.id, "channel_id": new_msg.channel.id}, doc_ids = [line.doc_id])
        if not found:
            await ctx.send("No teams found", delete_after=10)
        await ctx.message.delete()
            
              
    @commands.command(name='team', aliases=['t'])
    async def my_lobby(self, ctx, user: disnake.Member=None):
        await ctx.message.delete()
        if user == None:
            user = ctx.message.author
        if not self.bot._db.search(self.bot._query.participants.any([user.id])):
            await ctx.send(f'**{user.display_name}** is not in a team.', delete_after=10)
            return
        line = self.bot._db.search(self.bot._query.participants.any([user.id]))[0]
        oldmess = await ctx.fetch_message(line["embed_id"])
        embed = oldmess.embeds[0]
        new_msg = await ctx.send(embed=embed, components=[disnake.ui.Button(label=c.label, style=c.style, custom_id=c.custom_id, url=c.url) for c in oldmess.components[0].children])
        await oldmess.delete()
        self.bot._db.update({"embed_id": new_msg.id, "channel_id": new_msg.channel.id}, doc_ids = [line.doc_id])
                               
                
    @commands.command(name='sticky', aliases=[])
    async def sticky(self, ctx, message_id: str, channel_id: disnake.TextChannel = None):
        if not (ctx.author.id == ctx.guild.owner_id or ctx.author.id == self.bot.owner_id):
            return
        if channel_id == None:
            channel_id = ctx.channel
        old_mess = await ctx.channel.fetch_message(int(message_id))
        new_mess = await self.bot.get_channel(channel_id.id).send(content=old_mess.content, embeds = old_mess.embeds)
        await old_mess.delete()
        await ctx.message.delete()
        self.bot._dbrandom.insert({"idd": new_mess.id, "channel_id": new_mess.channel.id, "title": str(new_mess.id), "sticky": "True"})
        
        
    @commands.command(name='unsticky', aliases=[])
    async def unsticky(self, ctx, message_id: str):
        if not (ctx.author.id == ctx.guild.owner_id or ctx.author.id == self.bot.owner_id):
            return
        for line in self.bot._dbrandom:
            if line["sticky"] == "False":
                continue
            if line["title"] == str(message_id):
                self.bot._dbrandom.remove(doc_ids = [line.doc_id])
                await ctx.message.delete()
                return

    @commands.Cog.listener("on_button_click")
    async def button_listener(self, inter: disnake.MessageInteraction) -> None:
        if "join" not in inter.component.custom_id and "leave" not in inter.component.custom_id and "cancel" not in inter.component.custom_id:
            return
        cancel = False
        if "cancel" in inter.component.custom_id:
            if not self.bot._db.contains(self.bot._query.participants.any([inter.author.id])):
                await inter.send('You are not in a team', ephemeral=True)
                return
            line = self.bot._db.get(self.bot._query.participants.any([inter.author.id]))
            if inter.author.id != line["participants"][0]:
                await inter.send('You are not the team host', ephemeral=True)
                return
            cancel = True
        if "join" in inter.component.custom_id:
            if self.bot._db.contains(self.bot._query.participants.any([inter.author.id])):
                await inter.send('You are already in a team, please leave the team you are in first using **-leave** or use **-t** to view your current team', ephemeral=True)
                return
            line = self.bot._db.get(self.bot._query.participants.any([int(inter.component.custom_id.split("+")[1])]))
            max_players = check(line["name"])
            if len(line["participants"]) == max_players:
                await inter.send(f'This team is full')
                return
            line["participants"].append(inter.author.id)
            msg_con = f"""**{inter.author.display_name}** has joined **{line["name"]}** {' '.join([f"<@{part}>" for part in line["participants"][0:-1] ])}"""
        if "leave" in inter.component.custom_id:
            if not self.bot._db.contains(self.bot._query.participants.any([inter.author.id])):
                await inter.send('You are not in a team.', ephemeral=True)
                return
            line = self.bot._db.get(self.bot._query.participants.any([inter.author.id]))
            line["participants"].remove(inter.author.id)
            if len(line["participants"]) < 1:
                cancel = True
            msg_con = f"""**{inter.author.display_name}** has left **{line["name"]}**"""
        oldmess = await inter.channel.fetch_message(line["embed_id"])
        emd = oldmess.embeds[0]
        await oldmess.delete()
        if cancel:
            await inter.send(f"""RIP team | **{line["name"]}**""")
            self.bot._db.remove(doc_ids = [line.doc_id])
        else:
            new_embed = await everything(self, line, emd, inter, msg_con)
            self.bot._db.update({"participants": line["participants"], "time": int(time.time()), "embed_id": new_embed.id, "channel_id": new_embed.channel.id}, doc_ids = [line.doc_id])
        return


                
    @create_lobby.error
    # @leave_lobby.error
    # @join_lobby.error
    # @lobbies.error
    # @kick_lobby.error
    # @cancel_lobby.error
    @my_lobby.error
    @options.error
    async def cog_error_handler(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            pass


def setup(bot):
    bot.add_cog(MyCommandsCog2(bot))
