import os
from pytube import YouTube
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import math
from flask import Flask

app_flask = Flask(__name__)  # For Render to detect a running service

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your bot token

bot = Client("NYBotz", bot_token=BOT_TOKEN)

START_TEXT = """Hello {}, 
I am a YouTube Downloader Bot. I can:
- Download videos in various qualities (360p, 480p, 720p, 1080p)
- Merge audio and video when necessary
- Show progress while downloading and uploading!

Just send me a YouTube video URL to get started!"""

START_BUTTONS = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Source Code", url="https://github.com/NYBotz")],
        [InlineKeyboardButton("Help", callback_data="help")],
    ]
)

HELP_TEXT = """Send any YouTube URL to download videos. I support:
- Videos in 360p, 480p, 720p, 1080p
- Audio-only downloads
- Automatic merging of audio and video when necessary.
"""

progress_template = "[{0}{1}] {2}%\n"

def humanbytes(size):
    """Convert bytes to a readable format."""
    power = 1024
    n = 0
    power_labels = ["B", "KB", "MB", "GB", "TB"]
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {power_labels[n]}"

def progress_bar(current, total):
    """Create a progress bar."""
    percentage = current * 100 / total
    filled = "█" * int(percentage / 10)
    empty = "░" * (10 - int(percentage / 10))
    return filled, empty, round(percentage, 2)

@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        text=START_TEXT.format(message.from_user.mention),
        reply_markup=START_BUTTONS,
        disable_web_page_preview=True,
    )

@bot.on_message(filters.regex(r"https?://(www\.)?youtube\.com/watch\?v=.+"))
async def youtube_downloader(client, message):
    url = message.text.strip()
    yt = YouTube(url)

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(f"360p", callback_data=f"360|{url}"),
                InlineKeyboardButton(f"480p", callback_data=f"480|{url}"),
            ],
            [
                InlineKeyboardButton(f"720p", callback_data=f"720|{url}"),
                InlineKeyboardButton(f"1080p", callback_data=f"1080|{url}"),
            ],
            [InlineKeyboardButton(f"Audio", callback_data=f"audio|{url}")],
        ]
    )

    await message.reply_photo(
        photo=yt.thumbnail_url,
        caption=f"**Title:** {yt.title}\n**Channel:** {yt.author}\nSelect the desired quality to download.",
        reply_markup=buttons,
    )

@bot.on_callback_query()
async def callback_query(client, query):
    data = query.data.split("|")
    quality = data[0]
    url = data[1]
    yt = YouTube(url)
    video_stream = None

    await query.message.edit_text("**Downloading...** Please wait.")
    start_time = time.time()

    if quality == "audio":
        stream = yt.streams.filter(only_audio=True).first()
        file_name = stream.download()
    else:
        # Fetch video and audio streams
        video_stream = yt.streams.filter(res=quality + "p", mime_type="video/mp4").first()
        audio_stream = yt.streams.filter(only_audio=True, mime_type="audio/mp4").first()

        if not video_stream:
            await query.message.edit_text(f"**{quality}p not available.** Choose another quality.")
            return

        # Download video
        video_path = video_stream.download(filename=f"{yt.title}_video.mp4")
        video_size = os.path.getsize(video_path)

        # Check if audio is available
        if audio_stream and video_stream.includes_audio_track:
            file_name = video_path
        else:
            # Download audio and merge
            audio_path = audio_stream.download(filename=f"{yt.title}_audio.mp4")
            merged_file = f"{yt.title}_merged.mp4"
            command = f"ffmpeg -i {video_path} -i {audio_path} -c:v copy -c:a aac {merged_file}"
            subprocess.run(command, shell=True)

            file_name = merged_file

    end_time = time.time()
    elapsed_time = end_time - start_time
    size = os.path.getsize(file_name)

    await query.message.edit_text(
        f"**Download completed!**\n**File Size:** {humanbytes(size)}\n**Time Taken:** {round(elapsed_time, 2)} seconds.\nUploading to Telegram..."
    )

    # Uploading Progress
    async def upload_progress(current, total):
        filled, empty, percent = progress_bar(current, total)
        await query.message.edit_text(
            f"**Uploading...**\n{progress_template.format(filled, empty, percent)}"
        )

    # Upload the file
    await client.send_document(
        chat_id=query.message.chat.id,
        document=file_name,
        caption=f"**Title:** {yt.title}\n**Size:** {humanbytes(size)}",
        progress=upload_progress,
    )

    os.remove(file_name)

@app_flask.route("/")
def home():
    return "YouTube Downloader Bot is Running!"

bot.start()

if __name__ == "__main__":
    app_flask.run(host="0.0.0.0", port=8080)
    
