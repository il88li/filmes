import telebot
import logging
import threading
import time
from config import BOT_TOKEN
from database import load_data, save_data, restore_from_backup, backup_all_data
from handlers import register_handlers

logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(BOT_TOKEN)

def periodic_backup():
    while True:
        time.sleep(3600)  # كل ساعة
        backup_all_data(bot)

if __name__ == '__main__':
    # استعادة البيانات
    restore_from_backup(bot)
    
    register_handlers(bot)
    
    # بدء النسخ الاحتياطي الدوري
    threading.Thread(target=periodic_backup, daemon=True).start()
    
    print("🚀 البوت يعمل بكامل ميزاته...")
    bot.infinity_polling()
