import os
import discord
from discord.ext import commands
import aiohttp
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("Set DISCORD_TOKEN in your environment!")

# Make sure this matches your category’s ID exactly:
AUTO_CATEGORY_IDS = {1380497765414604884}

async def detect_language(text: str) -> str:
    detect_url = "https://libretranslate.com/detect"
    payload = {"q": [text]}
    headers = {"Content-Type": "application/json"}
    timeout = aiohttp.ClientTimeout(total=5)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(detect_url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Language detection HTTP {resp.status}")
            data = await resp.json()
            if not (isinstance(data, list) and data and isinstance(data[0], list) and data[0]):
                raise RuntimeError("Language detection returned no results")
            return data[0][0].get("language", "")

async def translate_text(text: str, source: str, target: str) -> str:
    url = "https://libretranslate.com/translate"
    payload = {
        "q": text,
        "source": source,
        "target": target,
        "format": "text"
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
    print(f"[on_message] Author: {message.author}, Channel: #{message.channel.name}, Content: {message.content!r}")

    if message.author.bot:
        print("[on_message] → Author is a bot; ignoring.")
        return

    category = message.channel.category
    if not category:
        print("[on_message] → Channel has no category; ignoring.")
        await bot.process_commands(message)
        return

    print(f"[on_message] → Category name: {category.name}, Category ID: {category.id}")

    if category.id not in AUTO_CATEGORY_IDS:
        print(f"[on_message] → Category ID {category.id} NOT in AUTO_CATEGORY_IDS; ignoring.")
        await bot.process_commands(message)
        return

    # If we reach here, we know the message is in the correct category
    print("[on_message] → This is a monitored category. Attempting detect/translate…")
    try:
        lang = await detect_language(message.content)
        print(f"[on_message] → detect_language returned: {lang}")

        if lang == "en":
            print("[on_message] → Message is already English; skipping translation.")
        else:
            translated = await translate_text(message.content, lang, "en")
            print(f"[on_message] → Translated text: {translated}")
            await message.reply(f"🇬🇧 (en): {translated}", mention_author=False)
            print("[on_message] → Replied with translation.")
    except Exception as e:
        print(f"[on_message] → ERROR during detect/translate: {e}")
        await message.reply(f"❌ Auto-translate failed: {e}", mention_author=False)

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ Translator Bot active as {bot.user}")

bot.run(TOKEN)
