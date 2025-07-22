import aiohttp
import os
from dotenv import load_dotenv
import random

load_dotenv()
TENOR_API_KEY = os.getenv("TENOR_API_KEY")

async def fetch_gif(query):
    if not TENOR_API_KEY:
        return None
    
    url = "https://tenor.googleapis.com/v2/search?"
    params = {
        "q": query,
        "key": TENOR_API_KEY,
        "limit": 8,
        "media_filter": "minimal"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                results = data.get("results", [])
                if results:
                    return random.choice(results)["media_formats"]["gif"]["url"]
    return None
