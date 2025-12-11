import os
from yt_dlp import YoutubeDL
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")  # Safe: read from environment variable

# ----------------------------
# Extract video info without downloading
# ----------------------------
def get_video_info(url):
    ydl_opts = {"quiet": True, "noplaylist": True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info

# ----------------------------
# Download video in selected quality
# ----------------------------
def download_video(url, quality):
    output_folder = "downloads"
    os.makedirs(output_folder, exist_ok=True)

    format_map = {
        "360p": "bestvideo[height<=360]+bestaudio/best",
        "480p": "bestvideo[height<=480]+bestaudio/best",
        "720p": "bestvideo[height<=720]+bestaudio/best",
        "1080p": "bestvideo[height<=1080]+bestaudio/best",
    }

    ydl_opts = {
        "format": format_map.get(quality, "best"),
        "outtmpl": f"{output_folder}/%(title)s.%(ext)s",
        "merge_output_format": "mp4",
        "quiet": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    filename = f"{output_folder}/{info['title']}.mp4"
    return filename

# ----------------------------
# /start command
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a YouTube link and I will show options!")

# ----------------------------
# Handle user message with YouTube link
# ----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text

    if "youtu" not in url:
        await update.message.reply_text("Please send a valid YouTube link.")
        return

    await update.message.reply_text("Fetching video info...")

    try:
        info = get_video_info(url)
        context.user_data["video_url"] = url

        title = info.get("title", "Unknown Title")
        thumbnail = info.get("thumbnail")

        # Quality selection buttons
        keyboard = [
            [
                InlineKeyboardButton("360p", callback_data="360p"),
                InlineKeyboardButton("480p", callback_data="480p"),
            ],
            [
                InlineKeyboardButton("720p", callback_data="720p"),
                InlineKeyboardButton("1080p", callback_data="1080p"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_photo(
            photo=thumbnail,
            caption=f"🎬 *{title}*\n\nChoose quality to download:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# ----------------------------
# Handle quality selection button
# ----------------------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quality = query.data
    url = context.user_data.get("video_url")

    await query.edit_message_caption(
        caption=f"Downloading in *{quality}* quality...\nPlease wait ⏳",
        parse_mode="Markdown"
    )

    try:
        file_path = download_video(url, quality)
        await query.message.reply_video(video=open(file_path, "rb"))

    except Exception as e:
        await query.message.reply_text(f"Error occurred: {e}")

# ----------------------------
# Main function
# ----------------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()

if __name__ == "__main__":
    main()
