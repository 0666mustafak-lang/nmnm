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

# ========= إعدادات =========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ACCESS_CODE = "20002000"  # رمز الدخول ثابت داخل الكود

# ========= تخزين =========
sessions = {}
authorized_users = set()
running_processes = {}

# ========= أزرار =========
def choice_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1️⃣", callback_data="choice_1"),
            InlineKeyboardButton("2️⃣", callback_data="choice_2")
        ],
        [
            InlineKeyboardButton("3️⃣", callback_data="choice_3"),
            InlineKeyboardButton("4️⃣", callback_data="choice_4")
        ]
    ])

def delay_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱️ 1.2s", callback_data="delay_1")],
        [InlineKeyboardButton("🐢 2.0s", callback_data="delay_2")],
        [InlineKeyboardButton("🛡️ 3.0s", callback_data="delay_3")]
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

# ========= تشغيل السكربت (Thread + PTY) =========
def run_script_async(context, chat_id, data):
    uid = data["uid"]

    def worker():
        delay = data["delay"]
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text="🟢 البوت شغّال ⏳",
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

            # ترتيب الإدخال
            type_text(data["token"])
            type_text(data["id"])
            type_text(data["choice"])  # رقم فقط

            try:
                while True:
                    os.read(fd, 1024)
            except OSError:
                pass

            running_processes.pop(uid, None)
            context.bot.send_message(
                chat_id=chat_id,
                text="🔴 البوت توقف (انتهت العملية)"
            )

        except Exception:
            running_processes.pop(uid, None)
            context.bot.send_message(
                chat_id=chat_id,
                text="❌ صار كراش وتوقفت العملية"
            )

    threading.Thread(target=worker, daemon=True).start()

# ========= أوامر =========
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

    # تحقق الرمز
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
        update.message.reply_text("🔢 اختر رقم:", reply_markup=choice_keyboard())
        return

# ========= أزرار =========
def buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    chat_id = query.message.chat_id
    query.answer()

    if uid not in authorized_users:
        context.bot.send_message(chat_id=chat_id, text="❌ غير مصرح")
        return

    if query.data.startswith("choice_"):
        if uid not in sessions:
            return
        sessions[uid]["choice"] = query.data.split("_")[1]
        context.bot.send_message(
            chat_id=chat_id,
            text="⏱️ اختر التأخير:",
            reply_markup=delay_keyboard()
        )
        return

    if query.data.startswith("delay_"):
        if uid not in sessions:
            return
        sessions[uid]["delay"] = DELAY_MAP[query.data]
        data = sessions.pop(uid)
        data["uid"] = uid
        run_script_async(context, chat_id, data)
        return

    if query.data == "stop":
        pid = running_processes.get(uid)
        if not pid:
            context.bot.send_message(chat_id=chat_id, text="ℹ️ ماكو عملية شغّالة")
            return
        try:
            os.kill(pid, 9)
        except Exception:
            pass
        running_processes.pop(uid, None)
        context.bot.send_message(chat_id=chat_id, text="⛔ تم إيقاف العملية")

# ========= main =========
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
