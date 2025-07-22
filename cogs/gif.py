import discord
from discord.ext import commands
from services.tenor import fetch_gif

class Gif(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gif")
    async def gif(self, ctx, *, search_term: str = "funny"):
        """Sends a GIF based on the search term."""
        gif_url = await fetch_gif(search_term)
        if gif_url:
            await ctx.send(gif_url)
        else:
            await ctx.send("Couldn't find a GIF for that 😔")

async def setup(bot):
    await bot.add_cog(Gif(bot))