import os
import pty
import sys
import time
import threading
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Updater, CommandHandler, MessageHandler,
    Filters, CallbackQueryHandler, CallbackContext
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

sessions = {}
running_processes = {}

# ---------- أزرار اختيار الرقم ----------
def choice_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ (2011)", callback_data="choice_1")],
        [InlineKeyboardButton("2️⃣ (2012)", callback_data="choice_2")],
        [InlineKeyboardButton("3️⃣ (2013)", callback_data="choice_3")],
        [InlineKeyboardButton("4️⃣ (2012 / 2023)", callback_data="choice_4")]
    ])

def delay_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱️ طبيعي 1.2s", callback_data="delay_1")],
        [InlineKeyboardButton("🐢 بطيء 2.0s", callback_data="delay_2")],
        [InlineKeyboardButton("🛡️ آمن جداً 3.0s", callback_data="delay_3")]
    ])

def stop_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⛔ إيقاف", callback_data="stop")]
    ])

DELAY_MAP = {
    "delay_1": 1.2,
    "delay_2": 2.0,
    "delay_3": 3.0
}

# ---------- تشغيل السكربت ----------
def run_script_async(update, data):
    uid = update.effective_user.id

    def worker():
        delay = data["delay"]

        try:
            update.message.reply_text(
                f"🟢 البوت شغّال ⏳\n⏱️ التأخير: {delay}s",
                reply_markup=stop_keyboard()
            )

            pid, fd = pty.fork()
            if pid == 0:
                os.execv(sys.executable, [sys.executable, "Instagram o (1).py"])

            running_processes[uid] = pid

            def type_text(text):
                for ch in text:
                    os.write(fd, ch.encode())
                    time.sleep(delay)
                os.write(fd, b"\n")
                time.sleep(delay)

            # إدخال البيانات
            type_text(data["token"])
            type_text(data["id"])
            type_text(data["choice"])  # رقم فقط 1 / 2 / 3 / 4

            try:
                while True:
                    os.read(fd, 1024)
            except OSError:
                pass

            running_processes.pop(uid, None)
            update.message.reply_text("🔴 البوت توقف (العملية انتهت)")

        except Exception:
            running_processes.pop(uid, None)
            update.message.reply_text("❌ صار كراش وتوقفت العملية")

    threading.Thread(target=worker, daemon=True).start()

# ---------- أوامر ----------
def start(update: Update, context: CallbackContext):
    sessions[update.effective_user.id] = {}
    update.message.reply_text("✏️ اكتب التوكن:")

def handle(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    text = update.message.text.strip()

    if uid not in sessions:
        update.message.reply_text("❗ لازم تكتب /start بالبداية")
        return

    s = sessions[uid]

    if "token" not in s:
        s["token"] = text
        update.message.reply_text("🆔 اكتب الـ ID:")
        return

    if "id" not in s:
        s["id"] = text
        update.message.reply_text(
            "🔢 اختر الفترة:",
            reply_markup=choice_keyboard()
        )
        return

# ---------- أزرار ----------
def buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    query.answer()

    # اختيار الرقم (يرسل رقم فقط)
    if query.data.startswith("choice_"):
        if uid not in sessions:
            query.message.reply_text("❌ انتهت الجلسة، اكتب /start")
            return

        sessions[uid]["choice"] = query.data.split("_")[1]
        query.message.reply_text(
            "⏱️ اختر التأخير:",
            reply_markup=delay_keyboard()
        )
        return

    # اختيار التأخير
    if query.data.startswith("delay_"):
        if uid not in sessions:
            query.message.reply_text("❌ انتهت الجلسة، اكتب /start")
            return

        sessions[uid]["delay"] = DELAY_MAP[query.data]
        data = sessions.pop(uid)

        run_script_async(update, data)
        return

    # زر إيقاف
    if query.data == "stop":
        pid = running_processes.get(uid)
        if not pid:
            query.message.reply_text("ℹ️ ماكو عملية شغّالة")
            return

        try:
            os.kill(pid, 9)
        except Exception:
            pass

        running_processes.pop(uid, None)
        query.message.reply_text("⛔ تم إيقاف العملية")

# ---------- main ----------
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle))
    dp.add_handler(CallbackQueryHandler(buttons))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
