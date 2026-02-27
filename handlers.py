#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import *
from database import *

class BotHandlers:
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        register_user(user.id, user.username, user.first_name)
        
        if is_user_banned(user.id):
            await update.message.reply_text("❌ تم حظرك من البوت")
            return ConversationHandler.END
        
        keyboard = [[InlineKeyboardButton("🔍 تحقق من الاشتراك", callback_data="check_sub")]]
        await update.message.reply_text(
            "🎬 **بوت الأفلام والمسلسلات** 🎥

"
            f"📢 اشترك: [اضغط هنا]({SUPPORT_CHANNEL})

"
            "ثم اضغط الزر 👇", 
            parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CHECK_SUB

    @staticmethod
    async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.message.text.strip()
        results = search_content(query)
        
        if not results:
            await update.message.reply_text(
                f"❌ لم يتم العثور على «{query}»

"
                "💡 اطلب الفيلم أو انتظر المدير يضيفه!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 القائمة", callback_data="start")]])
            )
            return SEARCH_NAME
        
        for content in results:
            _, ctype, name, parts, total_parts, msg_ids, unique_id, _, _ = content
            channel = MOVIES_CHANNEL if ctype == "movie" else SERIES_CHANNEL
            link = f"https://t.me/c/{channel[4:]}/{msg_ids.split(',')[0] if msg_ids else '1'}"
            
            keyboard = [[InlineKeyboardButton("🎬 شاهد الآن", url=link)], [InlineKeyboardButton("🏠 القائمة", callback_data="start")]]
            caption = f"🎬 **{name}**

📂 {'📺 مسلسل' if ctype == 'series' else '🎥 فيلم'}
📋 الحلقة {parts}/{total_parts}"
            
            await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        await update.message.reply_text("🏠 العودة:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 القائمة", callback_data="start")]]))
        return ConversationHandler.END

    @staticmethod
    async def request_movie_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        movie_name = update.message.text.strip()
        user = update.effective_user
        add_request(user.id, f"{user.first_name} (@{user.username or ''})", movie_name)
        
        await context.bot.send_message(ADMIN_ID, f"📢 طلب جديد
👤 {user.first_name}
🆔 `{user.id}`
🎬 {movie_name}", parse_mode=ParseMode.MARKDOWN)
        await update.message.reply_text(f"✅ تم إرسال «{movie_name}» للمدير!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 القائمة", callback_data="start")]]))
        return ConversationHandler.END

    @staticmethod
    async def add_movie_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إضافة اسم الفيلم"""
        if update.effective_user.id != ADMIN_ID:
            return ADMIN_MODE
        
        context.user_data['content_type'] = 'movie'
        context.user_data['content_name'] = update.message.text.strip()
        context.user_data['parts_count'] = 0
        context.user_data['message_ids'] = []
        
        await update.message.reply_text(
            f"🎬 **إضافة فيلم: {context.user_data['content_name']}**

"
            "📤 أرسل الفيديو الأول (الجزء 1)
"
            "للإنهاء اكتب `/done`",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADDING_CONTENT

    @staticmethod
    async def add_series_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إضافة اسم المسلسل"""
        if update.effective_user.id != ADMIN_ID:
            return ADMIN_MODE
        
        context.user_data['content_type'] = 'series'
        context.user_data['content_name'] = update.message.text.strip()
        context.user_data['parts_count'] = 0
        context.user_data['message_ids'] = []
        
        await update.message.reply_text(
            f"📺 **إضافة مسلسل: {context.user_data['content_name']}**

"
            "📤 أرسل الحلقة الأولى
"
            "للإنهاء اكتب `/done`",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADDING_CONTENT

    @staticmethod
    async def adding_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """استقبال الفيديوهات"""
        if update.effective_user.id != ADMIN_ID:
            return ADDING_CONTENT
        
        content_type = context.user_data['content_type']
        content_name = context.user_data['content_name']
        parts_count = context.user_data['parts_count']
        
        if update.message.video:
            parts_count += 1
            
            # إرسال للقناة المناسبة
            channel_id = MOVIES_CHANNEL if content_type == 'movie' else SERIES_CHANNEL
            caption = f"🎬 **{content_name}**

"
            caption += f"🆔 {context.user_data.get('unique_id', 'جار الإضافة')} | "
            caption += f"الجزء {parts_count}"
            if content_type == 'series':
                caption += " | من بوت الأفلام"
            
            msg = await context.bot.send_video(channel_id, update.message.video.file_id, caption=caption, parse_mode=ParseMode.MARKDOWN)
            context.user_data['message_ids'].append(str(msg.message_id))
            
            await update.message.reply_text(f"✅ تم رفع الجزء {parts_count}
📤 أرسل الجزء التالي أو `/done`")
            context.user_data['parts_count'] = parts_count
            
        elif update.message.text == '/done':
            # حفظ في قاعدة البيانات
            unique_id = str(uuid.uuid4())[:8]
            context.user_data['unique_id'] = unique_id
            
            add_content(
                content_type, content_name, 1, parts_count,
                ','.join(context.user_data['message_ids']), ADMIN_ID
            )
            
            await update.message.reply_text(
                f"🎉 **تم إضافة {content_name} بنجاح!**

"
                f"📊 الأجزاء: {parts_count}
"
                f"🆔 المعرف: `{unique_id}`
"
                f"📺 القناة: {'الأفلام' if content_type == 'movie' else 'المسلسلات'}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 القائمة", callback_data="start")]])
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        return ADDING_CONTENT

    @staticmethod
    async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if get_maintenance_status() and query.data not in ["admin", "toggle_maintenance"]:
            await query.edit_message_text("🔧 البوت قيد الصيانة...")
            return
        
        user_id = update.effective_user.id
        handlers = BotHandlers()
        
        # القوائم
        if query.data == "start":
            keyboard = [
                [InlineKeyboardButton("🔍 البحث", callback_data="search")],
                [InlineKeyboardButton("📊 إحصائيات", callback_data="stats"), InlineKeyboardButton("💎 دعم", callback_data="support")],
                [InlineKeyboardButton("🎁 طلب فيلم", callback_data="request")]
            ]
            await query.edit_message_text("🎬 **القائمة الرئيسية**", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif query.data == "admin" and user_id == ADMIN_ID:
            keyboard = [
                [InlineKeyboardButton("🎬 إضافة فيلم", callback_data="add_movie")],
                [InlineKeyboardButton("📺 إضافة مسلسل", callback_data="add_series")],
                [InlineKeyboardButton("🔧 الصيانة", callback_data="toggle_maintenance"), InlineKeyboardButton("📢 الطلبات", callback_data="admin_requests")],
                [InlineKeyboardButton("🏠 القائمة", callback_data="start")]
            ]
            await query.edit_message_text("🔧 **لوحة المدير**", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif query.data in ["search", "request"]:
            await handlers.button_handler_basic(query, context)
