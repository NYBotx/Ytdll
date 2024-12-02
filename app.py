import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import yt_dlp
from send import send_file

# Configuration
BOT_TOKEN = "YOUR_BOT_TOKEN"
API_ID = 1234567  # Replace with your API ID
API_HASH = "YOUR_API_HASH"
APP_URL = "https://your-app-name.onrender.com"  # Replace with your Render app URL
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"
DOWNLOAD_DIR = "./downloads"
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # Telegram max upload size: 2GB

# Initialize Telegram Client
app = Client("youtube_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask App for Webhook
flask_app = Flask(__name__)

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def download_youtube_video(url, quality="best", audio_only=False):
    """
    Download video or audio from YouTube using yt-dlp.

    Parameters:
        url (str): YouTube video URL.
        quality (str): Video quality (e.g., 360, 720).
        audio_only (bool): If True, download only audio.

    Returns:
        str: Path to the downloaded file.
        dict: Info dictionary of the video.
    """
    ydl_opts = {
        "format": f"bestvideo[height<={quality}]+bestaudio/best" if not audio_only else "bestaudio",
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_name = ydl.prepare_filename(info)
        return file_name, info


@app.on_message(filters.command("start"))
async def start(client, message):
    """Handle the /start command."""
    await message.reply_text(
        f"👋 Hi {message.from_user.first_name}!\n"
        "I can help you download YouTube videos and audio. Send me a YouTube link to get started!",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Help", callback_data="help")]]
        ),
    )


@app.on_message(filters.regex(r"^https?://(www\.)?(youtube\.com|youtu\.be)/.+$"))
async def youtube_link(client, message):
    """Handle YouTube links."""
    url = message.text
    await message.reply_text(
        "🔍 Processing your link... Please select an option:",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("360p", callback_data=f"download|{url}|360"),
                    InlineKeyboardButton("480p", callback_data=f"download|{url}|480"),
                    InlineKeyboardButton("720p", callback_data=f"download|{url}|720"),
                    InlineKeyboardButton("1080p", callback_data=f"download|{url}|1080"),
                ],
                [
                    InlineKeyboardButton("Audio Only", callback_data=f"download|{url}|audio"),
                    InlineKeyboardButton("Cancel", callback_data="cancel"),
                ],
            ]
        ),
    )


@app.on_callback_query(filters.regex(r"^download\|"))
async def handle_download(client, callback_query):
    """Handle the download options."""
    data = callback_query.data.split("|")
    url, quality = data[1], data[2]
    audio_only = quality == "audio"
    status_message = await callback_query.message.edit_text("⏳ Starting download...")

    try:
        # Download video/audio
        file_name, info = await download_youtube_video(url, quality if not audio_only else "best", audio_only)

        # Check file size
        file_size = os.path.getsize(file_name)
        if file_size > MAX_FILE_SIZE:
            raise ValueError("File size exceeds Telegram's 2GB limit.")

        # Upload to Telegram
        await send_file(
            client,
            chat_id=callback_query.message.chat.id,
            file_path=file_name,
            status_message=status_message,
            caption=f"🎉 Download complete!\n**File:** `{file_name}`"
        )

    except Exception as e:
        await status_message.edit_text(f"❌ Error: {str(e)}")
    finally:
        # Cleanup is handled in send.py
        pass


@app.on_callback_query(filters.regex("cancel"))
async def cancel_download(client, callback_query):
    """Handle cancel button."""
    await callback_query.message.edit_text("🚫 Download canceled!")


@app.on_callback_query(filters.regex("help"))
async def help(client, callback_query):
    """Display help information."""
    await callback_query.message.edit_text(
        "📖 **Help**\n\n"
        "1️⃣ Send a YouTube link.\n"
        "2️⃣ Choose a quality or audio-only option.\n"
        "3️⃣ Wait for the file to be downloaded and uploaded.\n\n"
        "💡 You can cancel the process anytime by clicking 'Cancel'."
    )


@flask_app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    """Webhook endpoint for Telegram updates."""
    update = request.get_json()
    asyncio.run(app.process_update(update))
    return "OK", 200


if __name__ == "__main__":
    app.start()
    flask_app.run(host="0.0.0.0", port=8080)
                                                       
