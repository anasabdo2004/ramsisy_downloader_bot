import os
import requests
import yt_dlp
import logging
from telegram import Update
# استيراد CommandHandler لمعالجة الأوامر مثل /start
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from telegram.error import TelegramError

# إعدادات التسجيل - Logger Configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# يتم جلب التوكن من متغير البيئة
TOKEN = os.environ.get("TOKEN")
# جلب رابط الـ Webhook الجديد
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
# المنفذ: يستخدم 8000 افتراضياً، لكن الأفضل تركه يحدده Railway
PORT = int(os.environ.get("PORT", "8000")) 

if not TOKEN:
    logger.error("ERROR: TOKEN environment variable not set. Please set the 'TOKEN'.")
    exit(1)
if not WEBHOOK_URL:
    logger.warning("WARNING: WEBHOOK_URL not set. Running in Polling mode (less reliable).")

# دالة تحميل الفيديو من يوتيوب باستخدام yt-dlp - Downloads video from YouTube
def download_youtube(url):
    temp_path = '/tmp/'
    ydl_opts = {
        'outtmpl': os.path.join(temp_path, '%(id)s.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4', 
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'max_filesize': 50 * 1024 * 1024, 
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# دالة استخراج رابط التحميل من إنستجرام - Extracts download link from Instagram
def get_instagram_download(url):
    api = f"https://saveinsta.app/api/lookup/?url={url}"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(api, headers=headers, timeout=15)
        resp.raise_for_status() 
        data = resp.json()
        
        if data and data.get("media"):
            return data["media"][0].get("downloadUrl")
        return None
    except requests.RequestException as e:
        logger.error(f"Error fetching Instagram API: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing Instagram JSON: {e}")
        return None

# دالة معالجة الأمر /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "مرحبًا بك في بوت التنزيل! 👋\n\n"
        "أنا متخصص في تحميل الفيديوهات.\n"
        "**فقط أرسل لي رابط فيديو من:**\n"
        "1. **YouTube** 🌐\n"
        "2. **Instagram** 📸\n\n"
        "وسأقوم بتنزيله وإرساله لك مباشرةً. (الحد الأقصى للحجم: 50 ميجابايت)."
    )
    await update.message.reply_text(welcome_message)


# دالة معالجة الرسائل - Handles incoming text messages (دالة غير متزامنة)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()
    file_path = None
    
    try:
        await update.message.reply_chat_action("typing")

        if "youtube.com" in text or "youtu.be" in text:
            await update.message.reply_text("جاري تحميل الفيديو من YouTube... قد يستغرق الأمر بعض الوقت.")
            
            file_path = await context.application.loop.run_in_executor(
                None, download_youtube, text
            )

            await update.message.reply_video(
                video=file_path, 
                caption="✅ تم التحميل بنجاح! (YouTube)"
            )

        elif "instagram.com" in text:
            await update.message.reply_text("جاري استخراج رابط التحميل من Instagram...")
            
            dl_url = get_instagram_download(text)
            
            if dl_url:
                await update.message.reply_video(
                    video=dl_url, 
                    caption="✅ تم التحميل بنجاح! (Instagram)"
                )
            else:
                await update.message.reply_text("معلش، مينفعش أجيب الفيديو دلوقتي. (قد يكون الرابط غير صالح، خاص، أو الـ API غير متوفر).")

        else:
            await update.message.reply_text("ابعت لينك من YouTube أو Instagram بس لو سمحت.")

    except TelegramError as te:
        logger.error(f"Telegram Error sending video: {te}")
        await update.message.reply_text("حدث خطأ أثناء إرسال الفيديو للتيليجرام. (قد يكون حجم الفيديو كبيرًا جدًا).")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        await update.message.reply_text("حصل خطأ غير متوقع في التحميل. جرب تاني أو ابعت لينك تاني.")

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.error(f"Error cleaning up file: {e}")


def main():
    """بدء تشغيل البوت باستخدام Webhook (الأكثر استقراراً) أو Polling (احتياطياً)."""
    application = Application.builder().token(TOKEN).build()

    # إضافة معالجات الأوامر والرسائل
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    if WEBHOOK_URL:
        # وضع Webhook: يستخدم في بيئات السحابة مثل Railway
        logger.info(f"Setting up Webhook at port {PORT}")
        # Railway يوفر مسار التوجيه (Route) المناسب للبوت تلقائياً
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN, # نستخدم التوكن كمسار سري
            webhook_url=WEBHOOK_URL + TOKEN
        )
    else:
        # وضع Polling: يستخدم إذا لم يتم تعريف الـ Webhook
        logger.info("Starting bot polling (Fallback mode)...")
        application.run_polling(poll_interval=3.0)

if __name__ == "__main__":
    main()