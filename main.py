#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio, logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from config import *
from database import *
from handlers import BotHandlers

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

class TelegramMovieBot:
    def __init__(self):
        print("🤖 بوت الأفلام والمسلسلات (النسخة الكاملة)")
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        handlers = BotHandlers()
        
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', handlers.start)],
            states={
                CHECK_SUB: [CallbackQueryHandler(handlers.button_handler)],
                SEARCH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.search_handler)],
                REQUEST_MOVIE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.request_movie_handler)],
                ADD_MOVIE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.add_movie_name_handler)],
                ADD_SERIES_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.add_series_name_handler)],
                ADDING_CONTENT: [
                    MessageHandler(filters.VIDEO, handlers.adding_content_handler),
                    CommandHandler('done', handlers.adding_content_handler)
                ],
            },
            fallbacks=[CommandHandler('start', handlers.start)],
        )
        
        self.app.add_handler(conv_handler)
        self.app.add_handler(CallbackQueryHandler(handlers.button_handler))
        self.app.add_handler(CommandHandler("admin", handlers.button_handler))
        print("✅ كل الوظائف تعمل!")

    async def run(self):
        print("🚀 البوت جاهز!")
        print("📱 /start - البحث - طلب فيلم")
        print("👨‍💼 /admin - إضافة محتوى")
        await self.app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    bot = TelegramMovieBot()
    asyncio.run(bot.run())
