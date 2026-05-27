#!/usr/bin/env python3
"""
🎬 VideoMaster Bot - بوت تيليجرام لتحميل وتجميل الفيديوهات
يدعم: YouTube, TikTok, Instagram, Twitter/X, Facebook وغيرها
"""

import os
import re
import asyncio
import logging
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes,
    filters
)
from telegram.constants import ParseMode, ChatAction

import yt_dlp

# ─────────────────────────────────────────────
# إعداد اللوجينج
# ─────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("VideoMasterBot")

# ─────────────────────────────────────────────
# إعدادات البوت
# ─────────────────────────────────────────────
BOT_TOKEN = "8753438820:AAHNmNyrJUTSC37Qv1ZS-6gX1Ziw1kcT2Nk"
WATERMARK_TEXT = "@downloanasbot"   # ← نص الووترمارك
MAX_FILE_SIZE_MB = 50                # حد حجم الملف للتيليجرام (MB)
TEMP_DIR = Path(tempfile.gettempdir()) / "videomaster"
TEMP_DIR.mkdir(exist_ok=True)

# حالات المحادثة
WAITING_TRIM_START = 1
WAITING_TRIM_END   = 2
WAITING_WATERMARK  = 3

# ─────────────────────────────────────────────
# أنماط URL المدعومة
# ─────────────────────────────────────────────
URL_PATTERNS = [
    r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/\S+",
    r"(https?://)?(www\.)?tiktok\.com/\S+",
    r"(https?://)?(www\.)?instagram\.com/\S+",
    r"(https?://)?(www\.)?twitter\.com/\S+",
    r"(https?://)?(www\.)?x\.com/\S+",
    r"(https?://)?(www\.)?facebook\.com/\S+",
    r"(https?://)?(www\.)?fb\.watch/\S+",
    r"(https?://)?(www\.)?reddit\.com/\S+",
    r"(https?://)?(www\.)?twitch\.tv/\S+",
    r"(https?://)?(www\.)?dailymotion\.com/\S+",
    r"(https?://)?(www\.)?vimeo\.com/\S+",
]

def is_valid_url(text: str) -> bool:
    for pattern in URL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def format_duration(seconds: int) -> str:
    if not seconds:
        return "غير معروف"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def format_number(n) -> str:
    if not n:
        return "غير معروف"
    try:
        n = int(n)
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.1f}K"
        return str(n)
    except:
        return str(n)

def format_size(bytes_val) -> str:
    if not bytes_val:
        return "غير معروف"
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"

def get_platform_emoji(url: str) -> str:
    url = url.lower()
    if "youtube" in url or "youtu.be" in url: return "🎬"
    if "tiktok"  in url: return "🎵"
    if "instagram" in url: return "📸"
    if "twitter" in url or "x.com" in url: return "🐦"
    if "facebook" in url or "fb.watch" in url: return "👥"
    if "reddit"  in url: return "👽"
    if "twitch"  in url: return "🎮"
    if "vimeo"   in url: return "🎞"
    return "🌐"

# ─────────────────────────────────────────────
# جلب معلومات الفيديو
# ─────────────────────────────────────────────
async def fetch_video_info(url: str) -> dict | None:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "socket_timeout": 30,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        logger.error(f"Error fetching info: {e}")
        return None

# ─────────────────────────────────────────────
# أوامر البوت الأساسية
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"🎬 *أهلاً {user.first_name}! في VideoMaster Bot*\n\n"
        "أنا بساعدك تحمّل وتجمّل الفيديوهات من أي منصة!\n\n"
        "📌 *المنصات المدعومة:*\n"
        "YouTube • TikTok • Instagram • Twitter/X\n"
        "Facebook • Reddit • Twitch • Vimeo • وأكتر!\n\n"
        "🚀 *إزاي تبدأ؟*\n"
        "ببساطة ابعتلي رابط الفيديو وأنا هعمل الباقي!\n\n"
        "📋 */help* لقائمة كل الأوامر"
    )
    keyboard = [[
        InlineKeyboardButton("📋 المساعدة", callback_data="show_help"),
        InlineKeyboardButton("ℹ️ عن البوت",  callback_data="show_about"),
    ]]
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 *قائمة الأوامر:*\n\n"
        "🔗 *أرسل رابط مباشرة* ← للحصول على خيارات التحميل\n\n"
        "⚙️ *أوامر إضافية:*\n"
        "/trim ← قص مقطع من الفيديو\n"
        "/watermark ← تغيير نص الووترمارك\n"
        "/stats ← إحصائياتك\n"
        "/about ← معلومات عن البوت\n\n"
        "💡 *تلميح:* بعد إرسال الرابط هتلاقي:\n"
        "✅ معلومات الفيديو الكاملة\n"
        "✅ تحميل بجودات مختلفة\n"
        "✅ استخراج الصوت MP3\n"
        "✅ إضافة Watermark\n"
        "✅ قص الفيديو\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *VideoMaster Bot*\n\n"
        "بوت متكامل لتحميل وتعديل الفيديوهات\n\n"
        "🛠 *التقنيات المستخدمة:*\n"
        "• python-telegram-bot\n"
        "• yt-dlp\n"
        "• FFmpeg\n\n"
        "📊 *الإصدار:* 2.0\n"
        f"📅 *تاريخ اليوم:* {datetime.now().strftime('%Y-%m-%d')}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    downloads = data.get("downloads", 0)
    mp3s      = data.get("mp3s", 0)
    trims     = data.get("trims", 0)
    text = (
        "📊 *إحصائياتك:*\n\n"
        f"📥 تحميلات: *{downloads}*\n"
        f"🎵 استخراج صوت: *{mp3s}*\n"
        f"✂️ قص فيديو: *{trims}*\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ─────────────────────────────────────────────
# معالجة الرابط المُرسَل
# ─────────────────────────────────────────────
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data["current_url"] = url

    await update.message.chat.send_action(ChatAction.TYPING)
    msg = await update.message.reply_text("🔍 جاري جلب معلومات الفيديو...")

    info = await fetch_video_info(url)
    if not info:
        await msg.edit_text("❌ مش قادر أجلب معلومات الفيديو.\nتأكد من الرابط أو جرب تاني.")
        return

    context.user_data["video_info"] = info

    # بناء رسالة المعلومات
    emoji    = get_platform_emoji(url)
    title    = info.get("title", "بدون عنوان")[:100]
    duration = format_duration(info.get("duration", 0))
    views    = format_number(info.get("view_count"))
    likes    = format_number(info.get("like_count"))
    uploader = info.get("uploader") or info.get("channel") or "غير معروف"
    platform = info.get("extractor_key", "غير معروف")

    # الجودات المتاحة
    formats = info.get("formats", [])
    video_formats = [
        f for f in formats
        if f.get("vcodec") != "none" and f.get("acodec") != "none"
        and f.get("height")
    ]
    qualities = sorted(
        set(f["height"] for f in video_formats if f.get("height")),
        reverse=True
    )[:4]

    info_text = (
        f"{emoji} *{title}*\n\n"
        f"👤 القناة: `{uploader}`\n"
        f"🌐 المنصة: `{platform}`\n"
        f"⏱ المدة: `{duration}`\n"
        f"👁 المشاهدات: `{views}`\n"
        f"❤️ الإعجابات: `{likes}`\n\n"
        f"🎥 *الجودات المتاحة:* {', '.join(f'{q}p' for q in qualities) or 'غير محدد'}\n\n"
        "اختر العملية اللي تريدها:"
    )

    # أزرار الاختيار
    keyboard = []

    # أزرار الجودة
    quality_buttons = []
    for q in qualities[:4]:
        quality_buttons.append(
            InlineKeyboardButton(f"📥 {q}p", callback_data=f"dl_video_{q}")
        )
    if quality_buttons:
        keyboard.append(quality_buttons)

    # أزرار إضافية
    keyboard.append([
        InlineKeyboardButton("🎵 MP3",        callback_data="dl_audio"),
        InlineKeyboardButton("💧 + Watermark", callback_data="dl_watermark"),
    ])
    keyboard.append([
        InlineKeyboardButton("✂️ قص مقطع",    callback_data="trim_video"),
        InlineKeyboardButton("📊 معلومات كاملة", callback_data="full_info"),
    ])
    keyboard.append([
        InlineKeyboardButton("❌ إلغاء", callback_data="cancel"),
    ])

    await msg.edit_text(
        info_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─────────────────────────────────────────────
# معالجة أزرار الإجراءات
# ─────────────────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── إلغاء ──────────────────────────────
    if data == "cancel":
        await query.edit_message_text("❌ تم الإلغاء.")
        return

    # ── مساعدة / عن البوت ──────────────────
    if data == "show_help":
        await help_command(update, context)
        return
    if data == "show_about":
        await about_command(update, context)
        return

    # ── معلومات كاملة ──────────────────────
    if data == "full_info":
        info = context.user_data.get("video_info", {})
        tags = ", ".join((info.get("tags") or [])[:5]) or "لا يوجد"
        desc = (info.get("description") or "لا يوجد وصف")[:300]
        text = (
            f"📋 *معلومات كاملة:*\n\n"
            f"🎬 *العنوان:* {info.get('title','')}\n"
            f"👤 *الرافع:* {info.get('uploader','')}\n"
            f"📅 *التاريخ:* {info.get('upload_date','')}\n"
            f"⏱ *المدة:* {format_duration(info.get('duration',0))}\n"
            f"👁 *مشاهدات:* {format_number(info.get('view_count'))}\n"
            f"❤️ *إعجابات:* {format_number(info.get('like_count'))}\n"
            f"💬 *تعليقات:* {format_number(info.get('comment_count'))}\n"
            f"🏷 *تاجات:* {tags}\n\n"
            f"📝 *الوصف:*\n{desc}..."
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        return

    # ── تحميل فيديو بجودة معينة ───────────
    if data.startswith("dl_video_"):
        height = int(data.split("_")[-1])
        await _download_video(query, context, height=height, add_watermark=False)
        return

    # ── تحميل صوت MP3 ──────────────────────
    if data == "dl_audio":
        await _download_audio(query, context)
        return

    # ── تحميل مع ووترمارك ──────────────────
    if data == "dl_watermark":
        await _download_video(query, context, height=None, add_watermark=True)
        return

    # ── قص الفيديو ─────────────────────────
    if data == "trim_video":
        await query.edit_message_text(
            "✂️ *قص الفيديو*\n\nأرسل وقت البداية (مثال: `00:01:30` أو `90`)",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["trim_msg_id"] = query.message.message_id
        return ConversationHandler.END  # نخرج، MessageHandler هيكمّل

# ─────────────────────────────────────────────
# تحميل الفيديو
# ─────────────────────────────────────────────
async def _download_video(query, context, height=None, add_watermark=False):
    url  = context.user_data.get("current_url")
    chat = query.message.chat

    label = f"{height}p" if height else "أفضل جودة"
    suffix = " + Watermark" if add_watermark else ""
    await query.edit_message_text(f"⏬ جاري تحميل الفيديو ({label}{suffix})...")
    await chat.send_action(ChatAction.UPLOAD_VIDEO)

    out_path = TEMP_DIR / f"video_{query.from_user.id}_{datetime.now().timestamp()}.mp4"

    fmt = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]" if height else "bestvideo+bestaudio/best"
    ydl_opts = {
        "format": fmt,
        "outtmpl": str(out_path),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # البحث عن الملف الناتج
        final_path = out_path
        if not final_path.exists():
            candidates = list(TEMP_DIR.glob(f"video_{query.from_user.id}_*.mp4"))
            if candidates:
                final_path = max(candidates, key=lambda p: p.stat().st_mtime)

        if not final_path.exists():
            await query.edit_message_text("❌ فشل التحميل، حاول مرة أخرى.")
            return

        # إضافة ووترمارك
        if add_watermark:
            await query.edit_message_text("💧 جاري إضافة الووترمارك...")
            watermarked = TEMP_DIR / f"wm_{final_path.name}"
            wm_text = context.user_data.get("custom_watermark", WATERMARK_TEXT)
            success = await _add_watermark(final_path, watermarked, wm_text)
            if success:
                final_path.unlink(missing_ok=True)
                final_path = watermarked

        # فحص الحجم
        size_mb = final_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            await query.edit_message_text(
                f"⚠️ حجم الفيديو كبير ({size_mb:.1f} MB).\n"
                "تيليجرام بيسمح بـ 50MB فقط.\n"
                "جرب جودة أقل."
            )
            final_path.unlink(missing_ok=True)
            return

        await query.edit_message_text("📤 جاري الرفع...")
        with open(final_path, "rb") as f:
            caption = f"🎬 {context.user_data.get('video_info', {}).get('title', '')[:100]}\n📥 {label}{suffix}\n🤖 @downloanasbot"
            await chat.send_video(
                video=InputFile(f),
                caption=caption,
                supports_streaming=True,
            )

        context.user_data["downloads"] = context.user_data.get("downloads", 0) + 1
        final_path.unlink(missing_ok=True)
        await query.edit_message_text("✅ تم التحميل بنجاح!")

    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text(f"❌ خطأ أثناء التحميل:\n`{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)

# ─────────────────────────────────────────────
# استخراج الصوت MP3
# ─────────────────────────────────────────────
async def _download_audio(query, context):
    url  = context.user_data.get("current_url")
    chat = query.message.chat

    await query.edit_message_text("🎵 جاري استخراج الصوت...")
    await chat.send_action(ChatAction.UPLOAD_DOCUMENT)

    out_path = TEMP_DIR / f"audio_{query.from_user.id}_{datetime.now().timestamp()}.mp3"
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(out_path.with_suffix("")),
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # البحث عن ملف MP3
        mp3_files = list(TEMP_DIR.glob(f"audio_{query.from_user.id}_*.mp3"))
        if not mp3_files:
            await query.edit_message_text("❌ فشل استخراج الصوت.")
            return

        final_path = max(mp3_files, key=lambda p: p.stat().st_mtime)
        size_mb = final_path.stat().st_size / (1024 * 1024)

        if size_mb > MAX_FILE_SIZE_MB:
            await query.edit_message_text(f"⚠️ حجم الصوت كبير ({size_mb:.1f} MB).")
            final_path.unlink(missing_ok=True)
            return

        await query.edit_message_text("📤 جاري الرفع...")
        info  = context.user_data.get("video_info", {})
        title = info.get("title", "audio")[:64]
        with open(final_path, "rb") as f:
            await chat.send_audio(
                audio=InputFile(f),
                title=title,
                performer=info.get("uploader", ""),
                duration=info.get("duration"),
                caption="🎵 تم الاستخراج بواسطة @downloanasbot",
            )

        context.user_data["mp3s"] = context.user_data.get("mp3s", 0) + 1
        final_path.unlink(missing_ok=True)
        await query.edit_message_text("✅ تم استخراج الصوت بنجاح!")

    except Exception as e:
        logger.error(f"Audio error: {e}")
        await query.edit_message_text(f"❌ خطأ:\n`{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)

# ─────────────────────────────────────────────
# إضافة ووترمارك باستخدام FFmpeg
# ─────────────────────────────────────────────
async def _add_watermark(input_path: Path, output_path: Path, text: str) -> bool:
    escaped = text.replace("'", "\\'").replace(":", "\\:")
    font_size = 36
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vf",
        (
            f"drawtext=text='{escaped}'"
            f":fontsize={font_size}"
            f":fontcolor=white@0.8"
            f":borderw=2:bordercolor=black@0.8"
            f":x=w-tw-20:y=h-th-20"
        ),
        "-codec:a", "copy",
        "-preset", "fast",
        str(output_path)
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return output_path.exists()
    except Exception as e:
        logger.error(f"Watermark error: {e}")
        return False

# ─────────────────────────────────────────────
# قص الفيديو (Conversation)
# ─────────────────────────────────────────────
async def trim_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("current_url"):
        await update.message.reply_text("❌ ابعت رابط الفيديو الأول!")
        return ConversationHandler.END
    await update.message.reply_text(
        "✂️ *قص الفيديو*\n\nأرسل وقت البداية (مثال: `00:01:30` أو `90` ثانية)",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_TRIM_START

async def trim_get_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["trim_start"] = update.message.text.strip()
    await update.message.reply_text(
        "⏱ الآن أرسل وقت النهاية (مثال: `00:03:00` أو `180`)"
    )
    return WAITING_TRIM_END

async def trim_get_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = context.user_data.get("trim_start")
    end   = update.message.text.strip()
    url   = context.user_data.get("current_url")
    chat  = update.message.chat

    msg = await update.message.reply_text(f"✂️ جاري القص من {start} إلى {end}...")
    await chat.send_action(ChatAction.UPLOAD_VIDEO)

    ts = datetime.now().timestamp()
    raw_path = TEMP_DIR / f"raw_{update.effective_user.id}_{ts}.mp4"
    out_path = TEMP_DIR / f"trim_{update.effective_user.id}_{ts}.mp4"

    ydl_opts = {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "outtmpl": str(raw_path),
        "merge_output_format": "mp4",
        "quiet": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not raw_path.exists():
            candidates = list(TEMP_DIR.glob(f"raw_{update.effective_user.id}_*.mp4"))
            if candidates:
                raw_path = max(candidates, key=lambda p: p.stat().st_mtime)

        cmd = [
            "ffmpeg", "-y",
            "-ss", start, "-to", end,
            "-i", str(raw_path),
            "-c", "copy",
            str(out_path)
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        raw_path.unlink(missing_ok=True)

        if not out_path.exists():
            await msg.edit_text("❌ فشل القص، تأكد من الأوقات.")
            return ConversationHandler.END

        size_mb = out_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            await msg.edit_text(f"⚠️ المقطع كبير ({size_mb:.1f} MB).")
            out_path.unlink(missing_ok=True)
            return ConversationHandler.END

        await msg.edit_text("📤 جاري الرفع...")
        with open(out_path, "rb") as f:
            await chat.send_video(
                video=InputFile(f),
                caption=f"✂️ مقطع من {start} إلى {end}\n🤖 @downloanasbot",
                supports_streaming=True,
            )

        context.user_data["trims"] = context.user_data.get("trims", 0) + 1
        out_path.unlink(missing_ok=True)
        await msg.edit_text("✅ تم القص بنجاح!")

    except Exception as e:
        logger.error(f"Trim error: {e}")
        await msg.edit_text(f"❌ خطأ:\n`{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)

    return ConversationHandler.END

async def trim_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم إلغاء القص.")
    return ConversationHandler.END

# ─────────────────────────────────────────────
# تغيير الووترمارك
# ─────────────────────────────────────────────
async def watermark_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💧 *تغيير الووترمارك*\n\nأرسل النص الجديد للووترمارك:",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_WATERMARK

async def watermark_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["custom_watermark"] = text
    await update.message.reply_text(f"✅ تم تغيير الووترمارك إلى:\n`{text}`", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

# ─────────────────────────────────────────────
# معالجة الرسائل العامة
# ─────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""

    # إذا كانت رسالة تأتي بعد طلب trim من زر
    if context.user_data.get("trim_msg_id") and not context.user_data.get("trim_start"):
        context.user_data["trim_start"] = text.strip()
        context.user_data.pop("trim_msg_id", None)
        await update.message.reply_text("⏱ الآن أرسل وقت النهاية:")
        return

    if context.user_data.get("trim_start") and not context.user_data.get("trim_end_done"):
        context.user_data["trim_end_done"] = True
        fake_update = update
        fake_update.message._text = text
        await trim_get_end(fake_update, context)
        context.user_data.pop("trim_start", None)
        context.user_data.pop("trim_end_done", None)
        return

    if is_valid_url(text):
        await handle_url(update, context)
    else:
        await update.message.reply_text(
            "❓ ما فهمتش!\nابعتلي رابط فيديو من أي منصة أو استخدم /help"
        )

async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ أمر غير معروف. جرب /help")

# ─────────────────────────────────────────────
# نقطة البداية
# ─────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation: قص الفيديو
    trim_conv = ConversationHandler(
        entry_points=[CommandHandler("trim", trim_command)],
        states={
            WAITING_TRIM_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, trim_get_start)],
            WAITING_TRIM_END:   [MessageHandler(filters.TEXT & ~filters.COMMAND, trim_get_end)],
        },
        fallbacks=[CommandHandler("cancel", trim_cancel)],
    )

    # Conversation: تغيير الووترمارك
    wm_conv = ConversationHandler(
        entry_points=[CommandHandler("watermark", watermark_command)],
        states={
            WAITING_WATERMARK: [MessageHandler(filters.TEXT & ~filters.COMMAND, watermark_set)],
        },
        fallbacks=[CommandHandler("cancel", trim_cancel)],
    )

    # تسجيل الهاندلرز
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(trim_conv)
    app.add_handler(wm_conv)
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.COMMAND, handle_unknown))

    logger.info("🚀 VideoMaster Bot يعمل الآن...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
