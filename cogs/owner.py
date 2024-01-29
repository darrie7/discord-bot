from disnake.ext import commands, tasks
import disnake
import glob
from typing import Optional
from asyncio import to_thread
import requests

class Dropdown(disnake.ui.Select):
    def __init__(
        self, 
        opt: list,
        min_val: int = 1, 
        max_val: int = 1, 
        placehold: Optional[str] = None,
        my_custom_id: Optional[str] = None
        ) -> None:

        self.opt = opt

        # Set the options that will be presented inside the dropdown


        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder=placehold,
            min_values=min_val,
            max_values=max_val,
            options=self.opt,
            custom_id=my_custom_id
        )

    # async def callback(self, interaction: disnake.MessageInteraction) -> None:
    #     await interaction.response.send_message(self.vals[int(self.values[0])][0], ephemeral=True)
    #     await interaction.send(self.vals[int(self.values[0])][1], ephemeral=True)


class ViewButton(disnake.ui.Button):
    def __init__(
      self, 
      link: Optional[str] = None, 
      my_label: Optional[str] = None, 
      my_custom_id: Optional[str] = None, 
      button_style: Optional[object] = disnake.ButtonStyle.primary
      ) -> None:
        super().__init__(
            style=button_style,
            label=my_label,
            url=link,
            custom_id=my_custom_id
        )


class TheView(disnake.ui.View):
    def __init__(
      self, 
      viewcomponents: list
      ) -> None:
        super().__init__()

        # Adds the dropdown to our view object.
        for comp in viewcomponents:
            self.add_item(comp)

class OwnerCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.slash_command()
    @commands.is_owner()
    async def refresh_cogs(self, inter):
        """
        Updates the cogs from Github

        Parameters
        ----------
        """
        await inter.response.defer()
        n = 0
        while n <= 3:
            if n == 3:
                return
            my_cogs = await to_thread(requests.get, url="https://api.github.com/repos/darrie7/discord-bot/contents/cogs")
            if my_cogs.status_code != 200:
                continue
            my_cogs = my_cogs.json()
            for cog in my_cogs:
                with open(f"/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/cogs/{cog.get('name')}", 'wb') as cog_file:
                    cog_content = await to_thread(requests.get, url=cog.get('download_url'))
                    if cog_content.status_code == 200:
                        cog_file.write(cog_content.content)
            break
        await inter.send("Cogs updated", ephemeral=True)

    # Hidden means it won't show up on the default help.
  #################################################OWNER COMMANDS######################################          
    @commands.slash_command()
    @commands.is_owner()
    async def reload(self, inter):
        """        
        Reload cog

        Parameters
        ----------
        """
        options = [ disnake.SelectOption(label=f"cogs.{f.replace('/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/cogs/', '').replace('.py', '')}") for f in glob.glob("/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/cogs/*.py") ]
        await inter.response.send_message(view=TheView([Dropdown(options, my_custom_id="reload")]), ephemeral=True)

            
    @commands.slash_command()
    @commands.is_owner()
    async def load(self, inter):
        """        
        Load cog

        Parameters
        ----------
        """
        options = [ disnake.SelectOption(label=f"cogs.{f.replace('/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/cogs/', '').replace('.py', '')}") for f in glob.glob("/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/cogs/*.py") ]
        await inter.response.send_message(view=TheView([Dropdown(options, my_custom_id="just_load")]), ephemeral=True)
            
            
    @commands.slash_command()
    @commands.is_owner()
    async def unload(self, inter):
        """        
        Unoad cog

        Parameters
        ----------
        """
        options = [ disnake.SelectOption(label=f"cogs.{f.replace('/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/cogs/', '').replace('.py', '')}") for f in glob.glob("/home/darrie7/Scripts/pythonvenvs/discordbot/discordbot_scripts/cogs/*.py") ]
        await inter.response.send_message(view=TheView([Dropdown(options, my_custom_id="unload")]), ephemeral=True)


    @commands.Cog.listener('on_dropdown')
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if "load" not in inter.component.custom_id:
            return
        if "reload" in inter.component.custom_id:
            try:
                self.bot.unload_extension(inter.values[0])
                self.bot.load_extension(inter.values[0])
            except Exception as e:
                await inter.send(f'**`ERROR:`** {type(e).__name__} - {e}', ephemeral=True)
            else:
                await inter.send('**`SUCCESS`**', ephemeral=True)
        if "just_load" in inter.component.custom_id:
            try:
                self.bot.load_extension(inter.values[0])
            except Exception as e:
                await inter.send(f'**`ERROR:`** {type(e).__name__} - {e}', ephemeral=True)
            else:
                await inter.send('**`SUCCESS`**', ephemeral=True)
        if "unload" in inter.component.custom_id:
            try:
                self.bot.unload_extension(inter.values[0])
            except Exception as e:
                await inter.send(f'**`ERROR:`** {type(e).__name__} - {e}', ephemeral=True)
            else:
                await inter.send('**`SUCCESS`**', ephemeral=True)





def setup(bot):
    bot.add_cog(OwnerCog(bot))
