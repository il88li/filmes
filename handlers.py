import telebot
from telebot.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import load_data, save_data
from utils import *
from invite import *
from admin import *
from config import ADMIN_ID, CHANNEL_USERNAME
import re

user_states = {}

def register_handlers(bot):
    
    @bot.message_handler(commands=['start'])
    def start_handler(message):
        user_id = str(message.from_user.id)
        username = message.from_user.username or message.from_user.first_name
        
        # التحقق من رابط الدعوة
        if len(message.text.split()) > 1:
            referrer_id = message.text.split()[1]
            users = load_data('users')
            invites = load_data('invites')
            handle_referral(users, invites, referrer_id, user_id, username, bot)
        
        users = load_data('users')
        if user_id in users and users[user_id].get('active', False):
            bot.send_message(message.chat.id, "القائمة الرئيسية:", 
                           reply_markup=main_menu(user_id, user_id == str(ADMIN_ID)))
            return
        
        # مستخدم جديد
        users[user_id] = users.get(user_id, {'invites_needed': 5, 'invites_done': 0, 'active': False})
        save_data('users', users)
        
        if check_subscription(bot, message.from_user.id):
            handle_after_subscribe(bot, message.chat.id, user_id, username)
        else:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("اشتراك في القناة", url="https://t.me/iIl337"))
            kb.add(InlineKeyboardButton("التحقق من الاشتراك", callback_data="check_sub:" + user_id))
            bot.send_message(message.chat.id, "يرجى الاشتراك في القناة الرسمية أولاً:", reply_markup=kb)

    def handle_after_subscribe(bot, chat_id, user_id, username):
        notify_admin_join(bot, int(user_id), username)
        if user_id == str(ADMIN_ID):
            bot.send_message(chat_id, "مرحباً يا مدير!")
            bot.send_message(chat_id, "القائمة الرئيسية:", reply_markup=main_menu(user_id, True))
            return
        
        thank_msg = """شكراً جزيلاً لاشتراكك في قناتنا الرسمية!

نحن مضطرون لاستخدام نظام الدعوة لأننا نحتاج أعضاء جدد لاستمرار البوت وتقديم محتوى أفضل للجميع.

نشكرك على تفهمك وتعاونك"""
        bot.send_message(chat_id, thank_msg)
        
        users = load_data('users')
        needed = users[user_id]['invites_needed'] - users[user_id]['invites_done']
        if needed > 0:
            ref_link = get_referral_link(user_id)
            msg_text = "يرجى دعوة " + str(needed) + " أشخاص جدد:

" + ref_link
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("الحصول على رابط الدعوة", callback_data="get_ref:" + user_id))
            bot.send_message(chat_id, msg_text, reply_markup=kb)
        else:
            users[user_id]['active'] = True
            save_data('users', users)
            bot.send_message(chat_id, "تم تفعيل البوت!", reply_markup=main_menu(user_id))

    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        user_id = str(call.from_user.id)
        data = call.data
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        
        users = load_data('users')
        banned_users = load_data('banned')
        if user_id in banned_users:
            bot.answer_callback_query(call.id, "تم حظرك")
            return
        
        # التحقق من الاشتراك
        if data in ['menu_series', 'menu_movies', 'menu_search'] and not check_subscription(bot, call.from_user.id):
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("اشتراك في القناة", url="https://t.me/iIl337"))
            kb.add(InlineKeyboardButton("التحقق", callback_data="check_sub:" + user_id))
            try:
                bot.edit_message_text("يجب الاشتراك في القناة أولاً!", chat_id, msg_id, reply_markup=kb)
            except:
                pass
            bot.answer_callback_query(call.id, "اشترك أولاً!")
            return
        
        # التحقق من الدعوات
        if users.get(user_id, {}).get('invites_done', 0) < users.get(user_id, {}).get('invites_needed', 5) and user_id != str(ADMIN_ID):
            needed = users[user_id]['invites_needed'] - users[user_id]['invites_done']
            bot.answer_callback_query(call.id, "مطلوب " + str(needed) + " دعوة")
            return
        
        if data.startswith('check_sub:'):
            if check_subscription(bot, int(user_id)):
                bot.answer_callback_query(call.id, "تم التحقق")
                bot.edit_message_text("شكراً لاشتراكك!", chat_id, msg_id)
            else:
                bot.answer_callback_query(call.id, "لم تشترك بعد!")
        
        elif data == 'menu_series':
            series_data = load_data('series')
            if series_data:
                bot.edit_message_text("اختر مسلسل:", chat_id, msg_id, 
                    reply_markup=pagination_keyboard(list(series_data.keys()), 0, 'series', user_id))
            else:
                bot.edit_message_text("لا توجد مسلسلات", chat_id, msg_id, reply_markup=main_menu(user_id))
        
        elif data == 'menu_movies':
            movies_data = load_data('movies')
            if movies_data:
                bot.edit_message_text("اختر فيلم:", chat_id, msg_id, 
                    reply_markup=pagination_keyboard(list(movies_data.keys()), 0, 'movies', user_id))
            else:
                bot.edit_message_text("لا توجد أفلام", chat_id, msg_id, reply_markup=main_menu(user_id))
        
        elif data == 'back_main':
            bot.edit_message_text("القائمة الرئيسية:", chat_id, msg_id, 
                                reply_markup=main_menu(user_id, user_id == str(ADMIN_ID)))
        
        elif data == 'menu_admin' and user_id == str(ADMIN_ID):
            bot.edit_message_text("لوحة الإدارة:", chat_id, msg_id, reply_markup=admin_menu())
        
        bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda m: True)
    def message_handler(message):
        user_id = str(message.from_user.id)
        text = message.text
        
        bot.reply_to(message, "استخدم الأزرار!", reply_markup=main_menu(user_id, user_id == str(ADMIN_ID)))
