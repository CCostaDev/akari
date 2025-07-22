import discord
from discord.ext import commands
from config import TOKEN
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} is online!")

async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
             print(f"Loading cog: {filename}")
             await bot.load_extension(f"cogs.{filename[:-3]}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

asyncio.run(main())