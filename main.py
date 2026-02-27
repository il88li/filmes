import telebot
from config import BOT_TOKEN
from database import load_data
from handlers import *  # Import handlers
from utils import *
import logging

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot(BOT_TOKEN)

# Register handlers here if needed
if __name__ == '__main__':
    print("البوت يعمل...")
    bot.infinity_polling()
