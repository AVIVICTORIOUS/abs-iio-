import os
import yt_dlp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")

# --- States ---
WAITING_TYPE, WAITING_LINK = range(2)
user_state = {}  # {chat_id: state}
user_choice = {}  # {chat_id: "video" or "playlist"}

# --- Helpers ---
async def get_video_info(url):
    ydl_opts = {'quiet': True, 'format': 'best'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_state[chat_id] = WAITING_TYPE

    keyboard = [
        [InlineKeyboardButton("🎬 Single Video", callback_data="single")],
        [InlineKeyboardButton("📃 Playlist", callback_data="playlist")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Hello! What do you want to download?", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id
    await query.answer()

    if user_state.get(chat_id) == WAITING_TYPE:
        user_choice[chat_id] = query.data
        user_state[chat_id] = WAITING_LINK
        await query.edit_message_text("Great! Send me the YouTube link now.")
    elif user_state.get(chat_id) == WAITING_LINK:
        # Handling quality buttons for single video
        url, fmt = query.data.split("|")
        await query.edit_message_caption(caption="Downloading...")

        ydl_opts = {'format': fmt, 'quiet': True, 'outtmpl': 'video.%(ext)s'}
        loop = context.application.loop

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return "video.mp4"

        path = await loop.run_in_executor(None, download)
        await query.message.reply_document(document=open(path, "rb"), caption="Here’s your video!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if user_state.get(chat_id) != WAITING_LINK:
        await update.message.reply_text("Please click /start first to begin.")
        return

    choice = user_choice.get(chat_id)
    if choice == "single":
        info = await get_video_info(text)
        title = info.get("title")
        thumbnail = info.get("thumbnail")

        keyboard = [
            [InlineKeyboardButton("360p", callback_data=f"{text}|best[height<=360]")],
            [InlineKeyboardButton("480p", callback_data=f"{text}|best[height<=480]")],
            [InlineKeyboardButton("720p", callback_data=f"{text}|best[height<=720]")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_photo(photo=thumbnail, caption=title, reply_markup=reply_markup)

    elif choice == "playlist":
        ydl_opts = {'quiet': True, 'extract_flat': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(text, download=False)
        entries = info.get("entries", [])
        await update.message.reply_text(f"Playlist contains {len(entries)} videos. Currently downloading all...")

        loop = context.application.loop

        def download_all():
            ydl_opts2 = {'format': 'best', 'outtmpl': 'video.%(ext)s'}
            with yt_dlp.YoutubeDL(ydl_opts2) as ydl2:
                ydl2.download([text])
            return True

        await loop.run_in_executor(None, download_all)
        await update.message.reply_text("Playlist download completed!")

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
