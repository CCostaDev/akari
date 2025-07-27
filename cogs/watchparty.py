import discord
import aiohttp
from PIL import Image
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from dotenv import load_dotenv
import dateparser
import pytz
import json
import os
import io

load_dotenv()
WATCHLIST_FILE = "data/watchlist.json"
VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID"))
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

class WatchParty(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.watchlist = self.load_watchlist()

    def load_watchlist(self):
        if not os.path.exists(WATCHLIST_FILE):
            return {}
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
        
    def save_watchlist(self):
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(self.watchlist, f, indent=4)

    # Autocomplete function
    async def watchlist_autocomplete(self, interaction: discord.Interaction, current: str):
        return[
            app_commands.Choice(name=title, value=title)
            for title in self.watchlist
            if current.lower() in title.lower()
        ][:25]  # Discord limits to 25 choices

    # TMDB functions
    async def tmdb_search_show(self, title):
        url = f"https://api.themoviedb.org/3/search/tv"
        params = {"api_key": TMDB_API_KEY, "query": title}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                if data["results"]:
                    return data["results"][0] #returns top match
                return None
            
    async def tmdb_get_episode_info(self, show_id, season, episode):
        url = f"https://api.themoviedb.org/3/tv/{show_id}/season/{season}/episode/{episode}"
        params = {"api_key": TMDB_API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    
    async def get_image_bytes(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    image_data = await response.read()

                    # Use Pillow to verify image and get format
                    image = Image.open(io.BytesIO(image_data))
                    format = image.format.lower()  # e.g. 'png', 'jpeg'

                    # Optional: reject unsupported formats
                    if format not in ["jpeg", "jpg", "png"]:
                        raise ValueError(f"Unsupported image format: {format}")

                    return image_data
                else:
                    raise ValueError(f"Failed to fetch image: {url}")
            
    # /addshow
    @app_commands.command(name="addshow", description="Add a new show to the server's watchlist.")
    async def add_show(self, interaction: discord.Interaction, title: str):
        title = title.strip().title()
        if title in self.watchlist:
            await interaction.response.send_message(f"❌ '{title}' is already in the watchlist.", ephemeral=True)
            return
        self.watchlist[title] = {
            "current_season": 1,
            "current_episode": 1,
            "next_session": None
        }
        self.save_watchlist()
        await interaction.response.send_message(f"✅ '{title}' has been added to the watchlist!")

    # /removeshow
    @app_commands.command(name="removeshow", description="Remove a show from the watchlist.")
    async def remove_show(self, interaction: discord.Interaction, title: str):
        title = title.strip().title()
        if title not in self.watchlist:
            await interaction.response.send_message(f"❌ '{title}' is not in the watchlist.", ephemeral=True)
            return
        del self.watchlist[title]
        self.save_watchlist()
        await interaction.response.send_message(f"🗑️ '{title}' has been removed from the watchlist.")
    
    # /setep
    @app_commands.command(name="setep",description="Update the current episode number for a show.")
    @app_commands.describe(title="Select a show")
    async def set_episode(self, interaction: discord.Interaction, title: str, season: int, episode: int):
        title = title.strip().title()
        if title not in self.watchlist:
            await interaction.response.send_message(f"❌ '{title}' is not in the watchlist.", ephemeral=True)
            return
        self.watchlist[title]["current_season"] = season
        self.watchlist[title]["current_episode"] = episode
        self.save_watchlist()
        await interaction.response.send_message(f"📺 '{title}' is now set to Season {season}, Episode {episode}.")
    
    @set_episode.autocomplete("title")
    async def set_episode_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.watchlist_autocomplete(interaction, current)

    # /watched
    @app_commands.command(name="watched", description="Mark the next episode as watched.")
    async def watched(self, interaction: discord.Interaction, title: str):
        title = title.strip().title()
        if title not in self.watchlist:
            await interaction.response.send_message(f"❌ '{title}' is not in the watchlist.", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ Marked episode {self.watchlist[title]['current_episode']} of **{title}** as watched.")
        self.watchlist[title]["current_episode"] += 1
        self.watchlist[title]["next_session"] = None  # clears schedule session if any exist
        self.save_watchlist()

    # /watchlist
    @app_commands.command(name="watchlist", description="View the current server watchlist.")
    async def show_watchlist(self, interaction: discord.Interaction):
        if not self.watchlist:
            await interaction.response.send_message("📭 The watchlist is currently empty.")
            return
        message = "🎬 **Watchlist:**\n"
        for title, data in self.watchlist.items():
            ep = data.get("current_episode", "?")
            message += f"- **{title}** (Ep {ep})\n"
        await interaction.response.send_message(message)

    # /status
    @app_commands.command(name="status", description="Show the current status of a show.")
    @app_commands.describe(title="Select a show")
    async def show_status(self, interaction: discord.Interaction, title: str):
        title = title.strip().title()
        if title not in self.watchlist:
            await interaction.response.send_message(f"❌ '{title}' is not in the watchlist.", ephemeral=True)
            return
        show = self.watchlist[title]
        ep = show.get("current_episode", 1)
        season = show.get("current_season", 1)
        session = show.get("next_session")
        if session:
            session_time = datetime.fromisoformat(session)
            formatted = session_time.strftime('%A, %d %B %Y at %I:%M %p')
        else:
            formatted = "Not scheduled"
        await interaction.response.send_message(f"📺 **{title}**\nNext Episode: S{season} E{ep}\nNext Watch Session: {formatted}")

    @show_status.autocomplete("title")
    async def show_status_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.watchlist_autocomplete(interaction, current)
        
    

    # /schedule
    @app_commands.choices(timezone=[app_commands.Choice(name="UK", value="UK"), app_commands.Choice(name="NL", value="NL")])
    @app_commands.command(name="schedule", description="Schedule the next watch session for a show.")
    @app_commands.describe(title="Select a show", time="Time for the session (e.g. 'Sunday 8pm')", timezone="Timezone (UK or NL)")
    async def schedule_session(self, interaction: discord.Interaction, title: str, time: str, timezone: str):
        title = title.strip().title()
        if title not in self.watchlist:
            await interaction.response.send_message(f"❌ '{title}' is not in the watchlist.", ephemeral=True)
            return
        
        # Timezone mapping
        timezone_map = {
            "UK": "Europe/London",
            "NL": "Europe/Amsterdam"
        }
        tz_name = timezone_map.get(timezone.upper())
        if not tz_name:
            await interaction.response.send_message("❌ Invalid timezone. Choose either 'UK' or 'NL'.", ephemeral=True)
            return
        
        # Parse and localise the time
        parsed_time = dateparser.parse(time)
        if not parsed_time:
            await interaction.response.send_message("❌ I couldn't understand that time. Try something like 'Sunday 8pm'.", ephemeral=True)
            return
        
        local_tz = pytz.timezone(tz_name)
        localized_time = local_tz.localize(parsed_time)
        parsed_time_utc = localized_time.astimezone(pytz.UTC)
        
        # Save session time
        self.watchlist[title]["next_session"] = parsed_time.isoformat()
        self.save_watchlist()

        # Get voice channel
        voice_channel = interaction.guild.get_channel(VOICE_CHANNEL_ID)
        if not voice_channel:
            await interaction.response.send_message("❌ Could not find the voice channel.", ephemeral=True)
            return

        # Get current episode and season
        season = self.watchlist[title].get("current_season", 1)
        ep = self.watchlist[title].get("current_episode", 1)
        runtime = 25  # default fallback
        poster_url = None
        image_bytes = None

        # fetch TMDB info
        tmdb_data = await self.tmdb_search_show(title)
        if tmdb_data:
            show_id = tmdb_data["id"]

            if tmdb_data.get("poster_path"):
                poster_url = f"https://image.tmdb.org/t/p/w780{tmdb_data['poster_path']}"
                try:
                    image_bytes = await self.get_image_bytes(poster_url)
                except Exception as e:
                    print(f"[Warning] Failed to fetch/verify poster image: {e}")
            episode_info = await self.tmdb_get_episode_info(show_id, season, ep)

            if episode_info:
                runtime = episode_info.get("runtime", runtime)
                overview = episode_info.get("overview", "No description available.")
            else:
                overview = "Episode info not found."
        else:
            overview = "TMDB info not found."

        # Create scheduled event
        try:
            await interaction.guild.create_scheduled_event(
                name=f"🎬 {title} - Season {season} Ep {ep}",
                description=f"{overview}",
                start_time=parsed_time_utc,
                end_time=parsed_time_utc + timedelta(minutes=runtime),
                channel=voice_channel,
                entity_type=discord.EntityType.voice,
                privacy_level=discord.PrivacyLevel.guild_only,
                image=image_bytes
            )
        except Exception as e:
            print("Failed to create scheduled event", e)
            await interaction.response.send_message("❌ Failed to create the scheduled event.", ephemeral=True)
            return

        formatted_time = localized_time.strftime('%A, %d %B %Y at %I:%M %p')
        await interaction.response.send_message(f"📅 Next session for **{title}** scheduled on `{formatted_time}` ({timezone}) and a Discord event has been created!")
    @schedule_session.autocomplete("title")
    async def schedule_title_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.watchlist_autocomplete(interaction, current)

async def setup(bot):
    await bot.add_cog(WatchParty(bot))