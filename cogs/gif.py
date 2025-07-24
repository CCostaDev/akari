import discord
from discord.ext import commands
from services.tenor import fetch_gif

class Gif(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gif")
    async def gif(self, ctx, *, args: str = "funny"):
        """Sends a GIF to the mentioned channel (or current) based on the search term."""
        words = args.split()

        target_channel = ctx.channel
        search_term = args

        if words:
            first = words[0]

            #Check if the first word is a channel mention
            if first.startswith("<#") and first.endswith(">"):
                try:
                    channel_id = int(first[2:-1])
                    mentioned_channel = ctx.guild.get_channel(channel_id)
                    if mentioned_channel:
                        target_channel = mentioned_channel
                        search_term = " ".join(words[1:]) or "funny"
                except ValueError:
                    pass  # Invalid mention format

        gif_url = await fetch_gif(search_term)
        if not gif_url:
            await ctx.send("Couldn't find a GIF for that 😔")
            return
        
        try:
            await target_channel.send(gif_url)
            if target_channel != ctx.channel:
                await ctx.send(f"Sent your gif to {target_channel.mention}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to send messages in that channel.")
        except discord.HTTPException:
            await ctx.send("Something went wrong when trying to send the GIF.")
        
        
async def setup(bot):
    await bot.add_cog(Gif(bot))