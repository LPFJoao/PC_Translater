import os
import discord
from discord.ext import commands
import aiohttp

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("Set DISCORD_TOKEN in your environment!")

# ──────────────────────────────────────────────────────────────────────────────
#  TWO category IDs that should auto-translate every message to English
#  Replace these numeric IDs with your own category IDs exactly as shown
# ──────────────────────────────────────────────────────────────────────────────
AUTO_CATEGORY_IDS = {1380497681688035450}

SUPPORTED_LANGS = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "pt": "Portuguese",
    "it": "Italian",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
}

async def translate_text(text: str, source: str, target: str) -> str:
    url = "https://libretranslate.com/translate"
    payload = {"q": text, "source": source, "target": target, "format": "text"}
    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Translation API returned HTTP {resp.status}")
            data = await resp.json()
            return data.get("translatedText", "")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_message(message: discord.Message):
    # 1) Don’t translate the bot’s own messages
    if message.author.bot:
        return

    # 2) Check if this channel is inside one of our AUTO_CATEGORY_IDS
    category = message.channel.category
    if category and category.id in AUTO_CATEGORY_IDS:
        try:
            # Translate into English (target="en"), auto-detect source language
            translated = await translate_text(message.content, "auto", "en")
            # Reply beneath the user’s message with the English text
            await message.reply(f"🇬🇧 (en): {translated}", mention_author=False)
        except Exception as e:
            await message.reply(f"❌ Auto-translate failed: {e}", mention_author=False)

    # 3) Process any other commands (if you add commands later)
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ Translator Bot active as {bot.user}")

bot.run(TOKEN)
