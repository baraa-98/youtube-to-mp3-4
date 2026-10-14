import logging
import os
import re
import shutil
import tempfile

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest
import yt_dlp

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MAX_TELEGRAM_FILE_MB = 50  # hard limit for uploads via the standard Bot API

# Comma-separated Telegram numeric user IDs allowed to use the bot,
# e.g. "111111111,222222222". If this is empty, NOBODY is allowed —
# set it in Railway Variables before deploying.
_allowed_env = os.environ.get("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = {
    int(uid.strip()) for uid in _allowed_env.split(",") if uid.strip()
}


def is_authorized(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS

# Optional: paste the full contents of a cookies.txt file (Netscape format)
# into a Railway variable called YTDLP_COOKIES if the android-client trick
# below isn't enough for some videos.
COOKIES_PATH = None
_cookies_env = os.environ.get("YTDLP_COOKIES")
if _cookies_env:
    COOKIES_PATH = "/tmp/cookies.txt"
    with open(COOKIES_PATH, "w") as f:
        f.write(_cookies_env)

YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/\S+", re.IGNORECASE
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 مش مسموحلك تستخدم البوت ده.")
        return
    await update.message.reply_text(
        "ابعتلي رابط يوتيوب وهقولك عايز تحوله MP3 ولا MP4."
    )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 مش مسموحلك تستخدم البوت ده.")
        return

    text = update.message.text or ""
    match = YOUTUBE_REGEX.search(text)
    if not match:
        await update.message.reply_text("ابعتلي رابط يوتيوب صحيح.")
        return

    url = match.group(0)
    context.user_data["url"] = url

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎵 MP3", callback_data="mp3"),
                InlineKeyboardButton("🎬 MP4", callback_data="mp4"),
            ]
        ]
    )
    await update.message.reply_text("عايز تحوله لإيه؟", reply_markup=keyboard)


async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(update.effective_user.id):
        await query.edit_message_text("🚫 مش مسموحلك تستخدم البوت ده.")
        return

    url = context.user_data.get("url")
    if not url:
        await query.edit_message_text("ابعت الرابط تاني.")
        return

    fmt = query.data  # "mp3" or "mp4"
    await query.edit_message_text("⏳ بحمّل...")

    tmp_dir = tempfile.mkdtemp()
    try:
        filepath = await download(url, fmt, tmp_dir)

        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if size_mb > MAX_TELEGRAM_FILE_MB:
            await query.edit_message_text(
                f"❌ الملف حجمه {size_mb:.1f}MB وده أكبر من حد تليجرام "
                f"({MAX_TELEGRAM_FILE_MB}MB). جرّب فيديو أقصر أو جودة أقل."
            )
            return

        await query.edit_message_text("📤 بترفع...")
        with open(filepath, "rb") as f:
            if fmt == "mp3":
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=f,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=60,
                )
            else:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=f,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=60,
                )

        await query.edit_message_text("✅ خلصت.")

    except Exception as e:
        logger.exception("Download failed")
        await query.edit_message_text(f"❌ حصل خطأ: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def download(url: str, fmt: str, out_dir: str) -> str:
    if fmt == "mp3":
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "noplaylist": True,
            "quiet": True,
        }
    else:
        # Capped at 480p to keep most videos under Telegram's 50MB limit
        ydl_opts = {
            "format": "best[height<=480][ext=mp4]/best[ext=mp4]/best",
            "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
        }

    # Pretend to be the Android app instead of a browser — YouTube's bot
    # check is far less aggressive against this client, especially from
    # datacenter IPs like Railway's.
    ydl_opts["extractor_args"] = {"youtube": {"player_client": ["android"]}}

    if COOKIES_PATH:
        ydl_opts["cookiefile"] = COOKIES_PATH

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        if fmt == "mp3":
            filepath = os.path.splitext(filepath)[0] + ".mp3"
        return filepath


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Set the TELEGRAM_BOT_TOKEN environment variable")

    request = HTTPXRequest(
        connect_timeout=60,
        read_timeout=60,
        write_timeout=60,
        pool_timeout=60,
    )
    app = Application.builder().token(BOT_TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(handle_choice))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
