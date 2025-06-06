import os
import discord
from discord.ext import commands
import aiohttp
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("Set DISCORD_TOKEN in your environment!")

# ──────────────────────────────────────────────────────────────────────────────
#  TWO category IDs whose messages should be auto‐translated into English
# ──────────────────────────────────────────────────────────────────────────────
AUTO_CATEGORY_IDS = {1380497681688035450}

async def detect_language(text: str) -> str:
    """
    Call LibreTranslate’s /detect endpoint to figure out the language code of `text`.
    Returns the top‐confidence language code (e.g. "en", "es", "fr").
    Raises RuntimeError on HTTP errors.
    """
    detect_url = "https://libretranslate.com/detect"
    payload = {"q": text}
    headers = {"Content-Type": "application/json"}
    timeout = aiohttp.ClientTimeout(total=5)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(detect_url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Language‐detection API returned HTTP {resp.status}")
            data = await resp.json()
            # data is a list of { "language": "<code>", "confidence": <float> } sorted by confidence
            if not isinstance(data, list) or len(data) == 0:
                raise RuntimeError("Language‐detection returned no results")
            # Pick the code with the highest confidence
            top = data[0]
            return top.get("language", "")

async def translate_text(text: str, source: str, target: str) -> str:
    """
    Call LibreTranslate’s /translate endpoint with a 10s timeout + one retry.
    Raises RuntimeError if both attempts fail.
    """
    url = "https://libretranslate.com/translate"
    payload = {
        "q": text,
        "source": source,
        "target": target,
        "format": "text"
        # If you acquire an API key for libretranslate.com in the future, add:
        # "api_key": os.getenv("LIBRETRANSLATE_API_KEY")
    }
    headers = {"Content-Type": "application/json"}
    timeout = aiohttp.ClientTimeout(total=10)

    for attempt in range(2):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"HTTP {resp.status}")
                    data = await resp.json()
                    return data.get("translatedText", "")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == 1:
                raise RuntimeError(f"Translation API failed: {e}")
            await asyncio.sleep(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    category = message.channel.category
    if category and category.id in AUTO_CATEGORY_IDS:
        try:
            # 1) Detect language first:
            lang = await detect_language(message.content)

            # 2) If it's already English, do nothing:
            if lang == "en":
                return

            # 3) Otherwise, translate from the detected language into English:
            translated = await translate_text(message.content, lang, "en")
            await message.reply(f"🇬🇧 (en): {translated}", mention_author=False)

        except Exception as e:
            # If detection or translation fails, show an error reply once:
            await message.reply(
                f"❌ Auto‐translate failed: {e}\n"
                "Please try again later or check back in a bit.",
                mention_author=False
            )

    # Make sure other commands (if any) still get processed:
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ Translator Bot active as {bot.user}")

bot.run(TOKEN)
