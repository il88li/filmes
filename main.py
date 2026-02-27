import telebot
import logging
from config import BOT_TOKEN
from handlers import register_handlers

logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(BOT_TOKEN)

if __name__ == '__main__':
    register_handlers(bot)
    print("🚀 البوت يعمل...")
    bot.infinity_polling()
