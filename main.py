import os
import discord
from discord.ext import commands
import aiohttp
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("Set DISCORD_TOKEN in your environment!")

# Replace this with your actual category ID:
AUTO_CATEGORY_IDS = {1380497681688035450}

async def translate_text(text: str, target: str = "en") -> str:
    """
    Call LibreTranslate’s /translate endpoint with source="auto" → target="en".
    If the API returns a 200, we return the translated text.
    Otherwise we raise RuntimeError.
    """
    url = "https://libretranslate.com/translate"
    payload = {
        "q": text,
        "source": "auto",
        "target": target,
        "format": "text"
        # If you get an API key later, add:
        # "api_key": os.getenv("LIBRETRANSLATE_API_KEY")
    }
    headers = {"Content-Type": "application/json"}
    timeout = aiohttp.ClientTimeout(total=10)

    # Try twice in case of a transient network hiccup
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
    # 1) Ignore messages from bots (including ourselves)
    if message.author.bot:
        return

    # 2) Log for debugging
    print(f"[on_message] From {message.author} in #{message.channel.name}: {message.content!r}")

    # 3) Check if the channel is under one of our AUTO_CATEGORY_IDS
    category = message.channel.category
    if not category:
        print("[on_message] → Channel has no category; ignoring.")
        await bot.process_commands(message)
        return

    print(f"[on_message] → Category {category.name} (ID={category.id})")
    if category.id not in AUTO_CATEGORY_IDS:
        print(f"[on_message] → Not an auto-translate category; ignoring.")
        await bot.process_commands(message)
        return

    # 4) This is a monitored category—attempt to translate
    print("[on_message] → Translating (auto → en)...")

    try:
        translated = await translate_text(message.content, target="en")
        print(f"[on_message] → Translated result: {translated!r}")

        # 5) If the translation is effectively identical to the original, skip replying
        #    (normalize by stripping whitespace and lowercasing)
        orig_norm = message.content.strip().lower()
        trans_norm = (translated or "").strip().lower()
        if orig_norm == trans_norm:
            print("[on_message] → Original was already English (or equivalent); skipping reply.")
        else:
            # 6) Reply with the English version
            await message.reply(f"🇬🇧 (en): {translated}", mention_author=False)
            print("[on_message] → Replied with translation.")
    except Exception as e:
        # 7) If something goes wrong (timeout, HTTP error, etc.), show one error message
        print(f"[on_message] → ERROR during translation: {e}")
        await message.reply(
            f"❌ Auto-translate failed: {e}\nPlease try again later.",
            mention_author=False
        )

    # 8) Always let commands (if any) be processed afterward
    await bot.process_commands(message)


@bot.event
async def on_ready():
    print(f"✅ Translator Bot active as {bot.user}")

bot.run(TOKEN)
