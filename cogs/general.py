import discord
from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(name="ping")
    async def ping(self, ctx):
        """Responds with Pong! and bot latency."""
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! 🏓 '{latency}ms'")

async def setup(bot):
    await bot.add_cog(General(bot))