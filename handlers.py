#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# handlers.py - معالجات الأزرار والأوامر

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import *
from database import *

class BotHandlers:
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء البوت - التحقق من الاشتراك"""
        user = update.effective_user
        register_user(user.id, user.username, user.first_name)
        
        if is_user_banned(user.id):
            await update.message.reply_text("❌ تم حظرك من البوت")
            return ConversationHandler.END
        
        keyboard = [[InlineKeyboardButton("🔍 تحقق من الاشتراك", callback_data="check_sub")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🎬 **بوت الأفلام والمسلسلات** 🎥

"
            f"📢 اشترك في قناة الدعم: [اضغط هنا]({SUPPORT_CHANNEL})

"
            "ثم اضغط زر التحقق 👇", 
            parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
        return CHECK_SUB

    @staticmethod
    async button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج جميع الأزرار"""
        query = update.callback_query
        await query.answer()
        
        maintenance = get_maintenance_status()
        if maintenance and query.data not in ["admin", "toggle_maintenance"]:
            await query.edit_message_text("🔧 البوت قيد الصيانة، انتظر قليلاً...")
            return

        handlers = BotHandlers()
        
        # التحقق من الاشتراك
        if query.data == "check_sub":
            keyboard = [[InlineKeyboardButton("✅ تحقق", url=SUPPORT_CHANNEL)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "✅ شكراً لاشتراكك!

"
                "📢 شارك رابط الدعوة مع 3 أشخاص
"
                "⭐ أرسل نجوم لـ @OlIiIl7

"
                "🎁 الآن يمكنك استخدام البوت كاملاً!",
                reply_markup=reply_markup
            )
        
        # القائمة الرئيسية
        elif query.data == "start":
            if maintenance:
                await query.answer("🔧 الصيانة مفعلة")
                return
            keyboard = [
                [InlineKeyboardButton("🔍 البحث", callback_data="search")],
                [InlineKeyboardButton("📊 إحصائيات", callback_data="stats"), 
                 InlineKeyboardButton("💎 دعم", callback_data="support")],
                [InlineKeyboardButton("🎁 طلب فيلم", callback_data="request")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("🎬 **القائمة الرئيسية** 👇", 
                                        parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        
        # إحصائيات
        elif query.data == "stats":
            stats = get_stats()
            await query.edit_message_text(stats, parse_mode=ParseMode.MARKDOWN)
        
        # دعم
        elif query.data == "support":
            await query.edit_message_text(
                "💎 **دعم البوت**

"
                "⭐ نجوم تليجرام → @OlIiIl7
"
                "💰 أي دعم مالي يساعد
"
                "📢 شارك البوت مع أصدقائك

"
                "شكراً 🙏", parse_mode=ParseMode.MARKDOWN
            ) 
