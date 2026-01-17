import os
import pty
import sys
import time
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler,
    Filters, CallbackQueryHandler, CallbackContext
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

DELAYS = {
    "1": 0.5,
    "2": 1.0,
    "3": 1.5,
    "4": 2.0
}

sessions = {}
last_data = {}

# ---------- تشغيل السكربت (Thread + PTY) ----------
def run_script_async(update, context, data):
    def worker():
        choice = data["choice"]
        delay = DELAYS[choice]

        try:
            update.message.reply_text("🟢 البوت شغّال ⏳")

            pid, fd = pty.fork()
            if pid == 0:
                os.execv(sys.executable, [sys.executable, "Instagram o (1).py"])

            def write_line(text):
                os.write(fd, (text + "\n").encode())
                time.sleep(delay)

            write_line(data["token"])
            write_line(data["id"])
            write_line(choice)

            # ننتظر السكربت يخلص بدون إرسال output
            try:
                while True:
                    os.read(fd, 1024)
            except OSError:
                pass

            update.message.reply_text("🔴 البوت توقف (العملية انتهت)")

        except Exception:
            update.message.reply_text("❌ صار كراش وتوقف البوت")

    threading.Thread(target=worker, daemon=True).start()

# ---------- أوامر ----------
def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    sessions[uid] = {}
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
        update.message.reply_text("🔢 اختر رقم (1 / 2 / 3 / 4):")
        return

    if "choice" not in s:
        if text not in DELAYS:
            update.message.reply_text("❌ اختر 1 / 2 / 3 / 4 فقط")
            return

        s["choice"] = text
        last_data[uid] = s.copy()

        run_script_async(update, context, s)
        del sessions[uid]

# ---------- أزرار ----------
def buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    query.answer()

    if query.data == "restart":
        sessions[uid] = {}
        query.message.reply_text("🔄 إعادة من البداية\n✏️ اكتب التوكن:")
        return

    if query.data == "repeat":
        if uid not in last_data:
            query.message.reply_text("❌ ماكو بيانات سابقة")
            return

        run_script_async(update, context, last_data[uid])

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
