import os
import requests
import yt_dlp
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

TOKEN = os.environ.get("TOKEN")  # هيتظبط في Koyeb

def download_youtube(url):
    ydl_opts = {
        'outtmpl': '/tmp/video.%(ext)s',
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
        'noplaylist': True,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return filename

def get_instagram_download(url):
    api = f"https://saveinsta.app/api/lookup/?url={url}"
    resp = requests.get(api, timeout=20)
    data = resp.json()
    return data["media"][0].get("downloadUrl")

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    chat_id = update.message.chat_id
    try:
        if "youtube.com" in text or "youtu.be" in text:
            update.message.reply_text("جاري تحميل الفيديو من YouTube... انتظر شوية")
            file_path = download_youtube(text)
            with open(file_path, "rb") as f:
                update.message.reply_video(video=f)
            try:
                os.remove(file_path)
            except:
                pass

        elif "instagram.com" in text:
            update.message.reply_text("جاري استخراج رابط التحميل من Instagram...")
            dl = get_instagram_download(text)
            if dl:
                update.message.reply_video(dl)
            else:
                update.message.reply_text("معلش، مينفعش أجيب الفيديو دلوقتي.")

        else:
            update.message.reply_text("ابعت لينك من YouTube أو Instagram بس.")

    except Exception as e:
        update.message.reply_text("حصل خطأ في التحميل. جرب تاني أو ابعت لينك تاني.")
        print("ERROR:", e)

def main():
    if not TOKEN:
        print("ERROR: TOKEN not set in environment variables.")
        return

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if name == "__main__":
    main()
