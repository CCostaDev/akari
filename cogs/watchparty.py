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
    @app_commands.command(name="addshow", description="Add a new show or movie to the server's watchlist.")
    @app_commands.describe(title="Title of the show or movie", is_movie="Check if it's a movie instead of a TV show")
    async def add_show(self, interaction: discord.Interaction, title: str, is_movie: bool = False):
        title = title.strip().title()
        if title in self.watchlist:
            await interaction.response.send_message(f"❌ '{title}' is already in the watchlist.", ephemeral=True)
            return
        self.watchlist[title] = {
            "type": "movie" if is_movie else "tv",
            "current_season": 1,
            "current_episode": 1,
            "next_session": None
        }
        self.save_watchlist()
        await interaction.response.send_message(f"✅ '{title}' has been added to the watchlist as a {'movie' if is_movie else 'TV show'}!")

    # /removeshow
    @app_commands.command(name="removeshow", description="Remove a show from the watchlist.")
    @app_commands.describe(title="Select a show")
    async def remove_show(self, interaction: discord.Interaction, title: str):
        title = title.strip().title()
        if title not in self.watchlist:
            await interaction.response.send_message(f"❌ '{title}' is not in the watchlist.", ephemeral=True)
            return
        del self.watchlist[title]
        self.save_watchlist()
        await interaction.response.send_message(f"🗑️ '{title}' has been removed from the watchlist.")

    @remove_show.autocomplete("title")
    async def remove_show_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.watchlist_autocomplete(interaction, current)
    
    # /setep
    @app_commands.command(name="setep",description="Update the current episode number for a show.")
    @app_commands.describe(title="Select a show")
    async def set_episode(self, interaction: discord.Interaction, title: str, season: int, episode: int):
        title = title.strip().title()
        if title not in self.watchlist:
            await interaction.response.send_message(f"❌ '{title}' is not in the watchlist.", ephemeral=True)
            return
        
        show = self.watchlist[title]
        if show.get("type", "tv") != "tv":
            await interaction.response.send_message(f"🎬 '{title}' is a movie and does not have episodes.", ephemeral=True)
            return
        
        show["current_season"] = season
        show["current_episode"] = episode
        self.save_watchlist()
        await interaction.response.send_message(f"📺 '{title}' is now set to Season {season}, Episode {episode}.")
        
    @set_episode.autocomplete("title")
    async def set_episode_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=title, value=title)
            for title, data in self.watchlist.items()
            if (data.get("type", "tv") == "tv") and current.lower() in title.lower()
        ][:25]

    # /watched
    @app_commands.command(name="watched", description="Mark the next episode as watched.")
    async def watched(self, interaction: discord.Interaction, title: str):
        title = title.strip().title()
        if title not in self.watchlist:
            await interaction.response.send_message(f"❌ '{title}' is not in the watchlist.", ephemeral=True)
            return
        
        entry = self.watchlist[title]
        content_type = entry.get("type", "tv")


        if content_type == "movie":
            # Just clear the session and optionally mark it somehow
            entry["next_session"] = None
            entry["watched"] = True
            await interaction.response.send_message(f"🎬 You've marked **{title}** as watched.")
        else:
            current_episode = entry.get("current_episode", 1)
            entry["current_episode"] = current_episode + 1
            entry["next_session"] = None
            await interaction.response.send_message(
                f"✅ Marked episode {current_episode} of **{title}** as watched. Now set to episode {entry['current_episode']}."
            )
        self.save_watchlist()

    @watched.autocomplete("title")
    async def watched_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.watchlist_autocomplete(interaction, current)

    # /watchlist
    @app_commands.command(name="watchlist", description="View the current server watchlist.")
    async def show_watchlist(self, interaction: discord.Interaction):
        if not self.watchlist:
            await interaction.response.send_message("📭 The watchlist is currently empty.")
            return
        message = "🎬 **Watchlist:**\n"
        for title, data in self.watchlist.items():
            if data.get("type") == "movie":
                message += f"- 🎬 **{title}** (Movie)\n"
            else:
                ep = data.get("current_episode", "?")
                season = data.get("current_season", "?")
                message += f"- 📺 **{title}** (S{season} E{ep})\n"
        await interaction.response.send_message(message)

    # /status
    @app_commands.command(name="status", description="Show the current status of a show or movie.")
    @app_commands.describe(title="Select a show or movie")
    async def show_status(self, interaction: discord.Interaction, title: str):
        title = title.strip().title()
        if title not in self.watchlist:
            await interaction.response.send_message(f"❌ '{title}' is not in the watchlist.", ephemeral=True)
            return
        
        show = self.watchlist[title]
        content_type = show.get("type", "tv")  #Default to "tv" for backward compatibility
        session = show.get("next_session")

        if session:
            session_time = datetime.fromisoformat(session)
            formatted = session_time.strftime('%A, %d %B %Y at %I:%M %p')
        else:
            formatted = "Not scheduled"

        if content_type == "movie":
            status_message = f"🎬 **{title}**\nType: Movie\nNext Watch Session: {formatted}"
        else:
            ep = show.get("current_episode", 1)
            season = show.get("current_season", 1)
            status_message = f"📺 **{title}**\nNext Episode: S{season} E{ep}\nNext Watch Session: {formatted}"
        await interaction.response.send_message(status_message)

    @show_status.autocomplete("title")
    async def show_status_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.watchlist_autocomplete(interaction, current)
        
    

    # /schedule
    @app_commands.choices(timezone=[app_commands.Choice(name="UK", value="UK"), app_commands.Choice(name="NL", value="NL")])
    @app_commands.command(name="schedule", description="Schedule the next watch session for a show or movie.")
    @app_commands.describe(title="Select a show or movie", time="Time for the session (e.g. 'Sunday 8pm')", timezone="Timezone (UK or NL)")
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

        # Get information for show or movie
        content_type = self.watchlist[title].get("type", "tv")
        season = self.watchlist[title].get("current_season", 1)
        ep = self.watchlist[title].get("current_episode", 1)
        runtime = 25  # default fallback
        poster_url = None
        image_bytes = None

        # fetch TMDB info (TV or movie)
        if content_type == "movie":
            tmdb_url = f"https://api.themoviedb.org/3/search/movie"
        else:
            tmdb_url = f"https://api.themoviedb.org/3/search/tv"

        params = {"api_key": TMDB_API_KEY, "query": title}
        async with aiohttp.ClientSession() as session:
            async with session.get(tmdb_url, params=params) as resp:
                tmdb_data = await resp.json()
                if tmdb_data["results"]:
                    result = tmdb_data["results"][0]
                    if result.get("poster_path"):
                        poster_url = f"https://image.tmdb.org/t/p/w780{result['poster_path']}"
                        try:
                            image_bytes = await self.get_image_bytes(poster_url)
                        except Exception as e:
                            print(f"[Warning] Failed to fetch/verify poster image: {e}")
                    overview = result.get("overview", "No description available.")
                    runtime = result.get("runtime", runtime)  # Movie runtime if present
                else:
                    overview = "TMDB info not found."

        
        # If it's a TV show, fetch episode info
        if content_type == "tv":
            show_id = result["id"]
            episode_info = await self.tmdb_get_episode_info(show_id, season, ep)
            if episode_info:
                runtime = episode_info.get("runtime", runtime)
                overview = episode_info.get("overview", overview)
        
        # Prepare event name
        if content_type == "movie":
            event_name = f"🎬 {title}"
        else:
            event_name = f"🎬 {title} - Season {season} Ep {ep}" 

        # Create scheduled event
        try:
            await interaction.guild.create_scheduled_event(
                name=event_name,
                description=overview,
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