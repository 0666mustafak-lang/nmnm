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
ACCESS_CODE = "20002000"

sessions = {}
authorized_users = set()
running_processes = {}

# ---------- أزرار ----------
def choice_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1    2011", callback_data="1")],
        [InlineKeyboardButton("2    2012", callback_data="2")],
        [InlineKeyboardButton("3    2013", callback_data="3")],
        [InlineKeyboardButton("4    2014/2023", callback_data="4")]
    ])

def delay_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱️ 1.5s (أفضل)", callback_data="1.5")],
        [InlineKeyboardButton("🐢 2.5s", callback_data="2.5")],
        [InlineKeyboardButton("🛡️ 4.0s", callback_data="4.0")]
    ])

def stop_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⛔ إيقاف", callback_data="stop")]
    ])

# ---------- تشغيل السكربت ----------
def run_script_async(context, chat_id, data):
    uid = data["uid"]

    def worker():
        delay = float(data["delay"])
        try:
            context.bot.send_message(chat_id=chat_id, text="🟢 البوت شغّال ⏳", reply_markup=stop_keyboard())

            pid, fd = pty.fork()
            if pid == 0:
                os.execv(sys.executable, [sys.executable, "Instagram o (1).py"])

            running_processes[uid] = pid

            def send(text):
                os.write(fd, (text + "\r\n").encode())
                time.sleep(delay)

            # ⏳ تأخير أولي مثل الإنسان
            time.sleep(delay)

            # ===== نفس التشغيل المحلي =====
            send(data["token"])
            send(data["id"])
            send(data["choice"])

            # نترك السكربت يشتغل
            while True:
                time.sleep(1)

        except Exception:
            running_processes.pop(uid, None)
            context.bot.send_message(chat_id=chat_id, text="❌ صار كراش وتوقفت العملية")

    threading.Thread(target=worker, daemon=True).start()

# ---------- أوامر ----------
def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    sessions[uid] = {}
    if uid not in authorized_users:
        update.message.reply_text("🔐 اكتب رمز الدخول:")
    else:
        update.message.reply_text("✏️ اكتب التوكن:")

def handle(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    text = update.message.text.strip()

    if uid not in sessions:
        update.message.reply_text("❗ لازم تكتب /start")
        return

    if uid not in authorized_users:
        if text != ACCESS_CODE:
            update.message.reply_text("كسمك")
            return
        authorized_users.add(uid)
        update.message.reply_text("✏️ اكتب التوكن:")
        return

    s = sessions[uid]

    if "token" not in s:
        s["token"] = text
        update.message.reply_text("🆔 اكتب الـ ID:")
        return

    if "id" not in s:
        s["id"] = text
        update.message.reply_text("🔢 اختر:", reply_markup=choice_keyboard())
        return

# ---------- أزرار ----------
def buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    chat_id = query.message.chat.id
    query.answer()

    if uid not in authorized_users:
        return

    if query.data in ("1", "2", "3", "4"):
        sessions[uid]["choice"] = query.data
        context.bot.send_message(chat_id=chat_id, text="⏱️ اختر التأخير:", reply_markup=delay_keyboard())
        return

    if query.data in ("1.5", "2.5", "4.0"):
        sessions[uid]["delay"] = query.data
        data = sessions.pop(uid)
        data["uid"] = uid
        run_script_async(context, chat_id, data)
        return

    if query.data == "stop":
        pid = running_processes.get(uid)
        if pid:
            try:
                os.kill(pid, 9)
            except Exception:
                pass
            running_processes.pop(uid, None)
        context.bot.send_message(chat_id=chat_id, text="⛔ تم إيقاف العملية")

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
