import discord
import os
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID"))
SUPPORT_CHANNEL_ID = int(os.getenv("SUPPORT_CHANNEL_ID"))
ROLE_ID = int(os.getenv("ROLE_ID"))

# TEMPORARY in-memory storage
welcome_messages = {}

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        support_channel = member.guild.get_channel(SUPPORT_CHANNEL_ID)
        role = member.guild.get_role(ROLE_ID)


        panda_emoji = "<a:PandaKissesLove:1269770132129841155>"
        lyzz_emoji = "<:ACozyBlanketLyzz:1237365594219610224>"
        myra_emoji = "<:MyraKissHeart:1241845943943299153>"

        if role:
            await member.add_roles(role)
            print(f"Gave {member.name} the role {role.name}")

        if channel and support_channel:
            msg = await channel.send(
                f"Welcome {member.mention} to **{member.guild.name}**! {panda_emoji}\n\n"
                f"Our aisles are stocked with fun, and the shelves are full of great company. Feel free to browse, chat, and make yourself at home! {lyzz_emoji}\n\n"
                f"Need help? Visit {support_channel.mention} to open a ticket. Otherwise, enjoy your stay and happy shopping—I mean, chatting! {myra_emoji}"
                )
            welcome_messages[member.id] = msg.id
            print(f"Sent welcome for {member.name}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel and member.id in welcome_messages:
            try:
                msg = await channel.fetch_message(welcome_messages[member.id])
                await msg.delete()
                print(f"Deleted welcome message for {member.name}")
            except discord.NotFound:
                print(f"Welcome message for {member.name} not found.")
            del welcome_messages[member.id]

async def setup(bot):
    await bot.add_cog(Welcome(bot))