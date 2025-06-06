import os
import discord
from discord.ext import commands
import aiohttp
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("Set DISCORD_TOKEN in your environment!")

# Make sure this matches your category’s ID exactly:
AUTO_CATEGORY_IDS = {1380497681688035450}


async def translate_text(text: str, target: str = "en") -> str:
    """
    Call the lt.blitzw.in LibreTranslate mirror (no API key needed):
      https://lt.blitzw.in/translate
    Retries once on failure, with a 10s timeout each try.
    Raises RuntimeError if both attempts fail or return non-200.
    """
    url = "https://lt.blitzw.in/translate"
    payload = {
        "q": text,
        "source": "auto",
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
    # 1) Ignore messages from any bot
    if message.author.bot:
        return

    # 2) Quick log for debugging
    print(f"[on_message] From {message.author} in #{message.channel.name}: {message.content!r}")

    # 3) Check if channel’s category is one we auto-translate
    category = message.channel.category
    if not category:
        print("[on_message] → No category; ignoring.")
        await bot.process_commands(message)
        return

    print(f"[on_message] → Category: {category.name} (ID={category.id})")
    if category.id not in AUTO_CATEGORY_IDS:
        print("[on_message] → Not watched; ignoring.")
        await bot.process_commands(message)
        return

    # 4) We’re in a watched category—attempt to translate
    print("[on_message] → Translating (auto→en)…")
    try:
        translated = await translate_text(message.content, target="en")
        print(f"[on_message] → Translated result: {translated!r}")

        # 5) If the translated text is effectively identical to the original,
        #    assume it was already English and skip replying.
        orig_norm = message.content.strip().lower()
        trans_norm = (translated or "").strip().lower()
        if orig_norm == trans_norm:
            print("[on_message] → Already English; skipping reply.")
        else:
            await message.reply(f"🇬🇧 (en): {translated}", mention_author=False)
            print("[on_message] → Replied with translation.")
    except Exception as e:
        print(f"[on_message] → ERROR during translation: {e}")
        await message.reply(
            f"❌ Auto-translate failed: {e}\nPlease try again later.",
            mention_author=False
        )

    # 6) Always let other commands (if any) run afterward
    await bot.process_commands(message)


@bot.event
async def on_ready():
    print(f"✅ Translator Bot active as {bot.user}")


bot.run(TOKEN)
