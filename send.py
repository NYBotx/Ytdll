import os
import math
from pyrogram.types import Message

async def send_file(client, chat_id, file_path, caption=None, status_message: Message = None):
    """
    Send a file to a Telegram user/chat with progress updates.

    Parameters:
        client (pyrogram.Client): Pyrogram client instance.
        chat_id (int): Telegram chat ID where the file will be sent.
        file_path (str): Path to the file to send.
        caption (str): Optional caption for the file.
        status_message (pyrogram.types.Message): Message object to update the progress.
    """
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)

    def progress(current, total):
        progress_percent = math.floor((current / total) * 100)
        progress_bar = "█" * (progress_percent // 10) + "-" * (10 - (progress_percent // 10))
        if status_message:
            try:
                status_message.edit_text(
                    f"**Uploading to Telegram:**\n"
                    f"[{progress_bar}] {progress_percent}%\n\n"
                    f"**File:** `{file_name}`\n"
                    f"`{current / (1024 * 1024):.2f} MB / {total / (1024 * 1024):.2f} MB`"
                )
            except Exception:
                pass

    try:
        await client.send_document(
            chat_id,
            file_path,
            caption=caption or f"🎉 Download complete!\n**File:** `{file_name}`",
            progress=progress
        )
        if status_message:
            await status_message.edit_text("✅ File successfully uploaded to Telegram!")
    except Exception as e:
        if status_message:
            await status_message.edit_text(f"❌ Failed to upload file:\n`{str(e)}`")
    finally:
        # Clean up the file after sending
        if os.path.exists(file_path):
            os.remove(file_path)
          
