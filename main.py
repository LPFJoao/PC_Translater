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
AUTO_CATEGORY_IDS = {1380497765414604884}

async def detect_language(text: str) -> str:
    """
    Call LibreTranslate’s /detect endpoint correctly, passing "q" as a list.
    The API returns a list‐of‐lists, where each inner list is the detection results
    for one input string. We only send a single string at a time, so we look at data[0][0].
    """
    detect_url = "https://libretranslate.com/detect"
    # NOTE: the API expects "q" to be a LIST of strings, even if we only detect one.
    payload = {"q": [text]}
    headers = {"Content-Type": "application/json"}
    timeout = aiohttp.ClientTimeout(total=5)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(detect_url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Language‐detection API returned HTTP {resp.status}")
            data = await resp.json()
            #
            # Example return value if you sent ["Hola"] might look like:
            # [
            #   [
            #     { "language": "es", "confidence": 0.99 },
            #     { "language": "pt", "confidence": 0.01 }
            #   ]
            # ]
            #
            # data is a list (one element per input). Inside data[0] is a list of
            # language‐objects sorted by confidence. We want data[0][0]["language"].
            if (
                not isinstance(data, list)
                or len(data) == 0
                or not isinstance(data[0], list)
                or len(data[0]) == 0
            ):
                raise RuntimeError("Language‐detection returned no results")
            top = data[0][0]
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
        # If you acquire an API key for libretranslate.com, add:
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
            # 1) Detect the language of the incoming message (as a list of one string)
            lang = await detect_language(message.content)

            # 2) If it’s already English, do nothing
            if lang == "en":
                return

            # 3) Otherwise translate from that language → English
            translated = await translate_text(message.content, lang, "en")
            await message.reply(f"🇬🇧 (en): {translated}", mention_author=False)

        except Exception as e:
            # If detection or translation fails, we send a single error reply
            await message.reply(
                f"❌ Auto‐translate failed: {e}\n"
                "Please try again later or check back in a bit.",
                mention_author=False
            )

    # Make sure any other commands (if added later) still work
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ Translator Bot active as {bot.user}")

bot.run(TOKEN)
