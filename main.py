#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# main.py - تشغيل البوت

import asyncio
import logging
import os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, ContextTypes

from config import *
from database import *
from handlers import BotHandlers

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramMovieBot:
    def __init__(self):
        print("🤖 بدء تشغيل بوت الأفلام...")
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """إعداد معالجات البوت"""
        handlers = BotHandlers()
        
        # معالج البداية
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', handlers.start)],
            states={
                CHECK_SUB: [CallbackQueryHandler(handlers.button_handler)],
            },
            fallbacks=[CommandHandler('start', handlers.start)],
        )
        
        # إضافة المعالجات
        self.app.add_handler(conv_handler)
        self.app.add_handler(CallbackQueryHandler(handlers.button_handler))
        self.app.add_handler(CommandHandler("admin", handlers.button_handler))
        
        print("✅ تم إعداد المعالجات")
    
    async def run(self):
        """تشغيل البوت"""
        maintenance = get_maintenance_status()
        print(f"🔧 الصيانة: {'مفعلة' if maintenance else 'معطلة'}")
        print("🚀 البوت يعمل الآن...")
        await self.app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    bot = TelegramMovieBot()
    asyncio.run(bot.run())
