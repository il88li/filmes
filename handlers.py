import telebot
from telebot.types import CallbackQuery
from database import load_data, save_data
from utils import *
from invite import *
from admin import *
from config import ADMIN_ID, CHANNEL_USERNAME, CHANNELS
import re
import threading
import time

user_states = {}  # حالة المستخدمين

def register_handlers(bot):
    
    @bot.message_handler(commands=['start'])
    def start_handler(message):
        user_id = str(message.from_user.id)
        username = message.from_user.username or message.from_user.first_name
        
        # التحقق من الرابط الدعوة
        if len(message.text.split()) > 1:
            referrer_id = message.text.split()[1]
            users = load_data('users')
            invites = load_data('invites')
            handle_referral(users, invites, referrer_id, user_id, username, bot)
        
        users = load_data('users')
        if user_id in users and users[user_id].get('active', False):
            bot.send_message(message.chat.id, "القائمة الرئيسية:", reply_markup=main_menu(user_id, user_id == str(ADMIN_ID)))
            return
        
        users[user_id] = users.get(user_id, {'invites_needed': 5, 'invites_done': 0, 'active': False})
        save_data('states', user_states)
        save_data('users', users)
        
        if check_subscription(bot, message.from_user.id):
            handle_after_subscribe(bot, message.chat.id, user_id, username)
        else:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("اشتراك في القناة", url="https://t.me/iIl337"))
            kb.add(InlineKeyboardButton("التحقق من الاشتراك", callback_data=f"check_sub:{user_id}"))
            bot.send_message(message.chat.id, "🎭 يرجى الاشتراك في القناة الرسمية أولاً:", reply_markup=kb)

    def handle_after_subscribe(bot, chat_id, user_id, username):
        notify_admin_join(bot, message.from_user.id, username)
        if user_id == str(ADMIN_ID):
            bot.send_message(chat_id, "🎯 مرحباً يا مدير!")
            bot.send_message(chat_id, "القائمة الرئيسية:", reply_markup=main_menu(user_id, True))
            return
        
        thank_msg = """🎉 شكراً جزيلاً لاشتراكك في قناتنا الرسمية!

نحن مضطرون لاستخدام نظام الدعوة لأننا نحتاج أعضاء جدد لاستمرار البوت وتقديم محتوى أفضل للجميع.

💝 نشكرك على تفهمك وتعاونك ❤️
"""
        bot.send_message(chat_id, thank_msg)
        
        users = load_data('users')
        needed = users[user_id]['invites_needed'] - users[user_id]['invites_done']
        if needed > 0:
            ref_link = get_referral_link(user_id)
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("الحصول على رابط الدعوة", callback_data=f"get_ref:{user_id}"))
            bot.send_message(chat_id, f"📢 يرجى دعوة {needed} أشخاص جدد:

`{ref_link}`", reply_markup=kb, parse_mode='Markdown')
        else:
            users[user_id]['active'] = True
            save_data('users', users)
            bot.send_message(chat_id, "✅ تم تفعيل البوت!", reply_markup=main_menu(user_id))

    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        user_id = str(call.from_user.id)
        data = call.data
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        
        users = load_data('users')
        banned_users = load_data('banned')
        if user_id in banned_users:
            bot.answer_callback_query(call.id, "🚫 تم حظرك")
            return
        
        # التحقق من الاشتراك للمحتوى
        if data in ['menu_series', 'menu_movies', 'menu_search'] and not check_subscription(bot, call.from_user.id):
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("اشتراك في القناة", url="https://t.me/iIl337"))
            kb.add(InlineKeyboardButton("التحقق", callback_data=f"check_sub:{user_id}"))
            bot.edit_message_text("يجب الاشتراك في القناة أولاً!", chat_id, msg_id, reply_markup=kb)
            return
        
        # التحقق من الدعوات
        if users.get(user_id, {}).get('invites_done', 0) < users.get(user_id, {}).get('invites_needed', 5) and user_id != str(ADMIN_ID):
            needed = users[user_id]['invites_needed'] - users[user_id]['invites_done']
            bot.answer_callback_query(call.id, f"📢 مطلوب {needed} دعوة")
            return
        
        if data.startswith('check_sub:'):
            user_id_check = data.split(':')[1]
            if check_subscription(bot, int(user_id_check)):
                handle_after_subscribe(bot, chat_id, user_id_check, call.from_user.first_name)
                bot.answer_callback_query(call.id, "✅ تم التحقق")
            else:
                bot.answer_callback_query(call.id, "❌ لم تشترك بعد!")
        
        elif data == 'menu_series':
            series_data = load_data('series')
            if series_data:
                bot.edit_message_text("📺 اختر مسلسل:", chat_id, msg_id, 
                    reply_markup=pagination_keyboard(list(series_data.keys()), 0, 'series', user_id))
            else:
                bot.edit_message_text("لا توجد مسلسلات", chat_id, msg_id, reply_markup=main_menu(user_id))
        
        elif data == 'menu_movies':
            movies_data = load_data('movies')
            if movies_data:
                bot.edit_message_text("🎥 اختر فيلم:", chat_id, msg_id, 
                    reply_markup=pagination_keyboard(list(movies_data.keys()), 0, 'movies', user_id))
            else:
                bot.edit_message_text("لا توجد أفلام", chat_id, msg_id, reply_markup=main_menu(user_id))
        
        elif data.startswith('series:') or data.startswith('movies:'):
            parts = data.split(':')
            prefix = parts[0]
            name = parts[1]
            page = int(parts[2]) if len(parts) > 2 else 0
            
            if prefix == 'series':
                videos = load_data('series')[name]
                bot.send_video(chat_id, videos[0], caption=f"مسلسل: {name} - الحلقة 1", 
                             reply_markup=episode_keyboard(name, 1, len(videos), user_id))
            else:  # movies
                videos = load_data('movies')[name]
                bot.send_video(chat_id, videos[0], caption=f"فيلم: {name} - الجزء 1", 
                             reply_markup=episode_keyboard(name, 1, len(videos), user_id))
        
        elif data.startswith('ep:'):
            parts = data.split(':')
            name = parts[1]
            ep_num = int(parts[2])
            
            if data.startswith('series:ep:'):
                videos = load_data('series')[name]
            else:
                videos = load_data('movies')[name]
            
            if ep_num <= len(videos):
                video_id = videos[ep_num-1]
                caption = f"الحلقة {ep_num}" if 'series' in data else f"الجزء {ep_num}"
                bot.send_video(chat_id, video_id, caption=f"{name} - {caption}",
                             reply_markup=episode_keyboard(name, ep_num, len(videos), user_id))
        
        elif data == 'menu_search':
            bot.send_message(chat_id, "اكتب اسم المسلسل أو الفيلم:")
            user_states[user_id] = 'searching'
        
        elif data == 'menu_admin' and user_id == str(ADMIN_ID):
            bot.edit_message_text("لوحة الإدارة:", chat_id, msg_id, reply_markup=admin_menu())
        
        elif data == 'admin_series' and user_id == str(ADMIN_ID):
            bot.edit_message_text("إدارة المسلسلات:", chat_id, msg_id, reply_markup=series_admin_menu())
        
        elif data == 'admin_movies' and user_id == str(ADMIN_ID):
            bot.edit_message_text("إدارة الأفلام:", chat_id, msg_id, reply_markup=movies_admin_menu())
        
        elif data == 'add_series' and user_id == str(ADMIN_ID):
            bot.edit_message_text("ارسل اسم المسلسل:", chat_id, msg_id)
            user_states[user_id] = 'add_series_name'
        
        elif data == 'add_movie' and user_id == str(ADMIN_ID):
            bot.edit_message_text("ارسل اسم الفيلم:", chat_id, msg_id)
            user_states[user_id] = 'add_movie_name'
        
        elif data == 'admin_broadcast' and user_id == str(ADMIN_ID):
            bot.edit_message_text("ارسل رسالة الإذاعة:", chat_id, msg_id)
            user_states[user_id] = 'broadcasting'
        
        elif data == 'back_main':
            bot.edit_message_text("القائمة الرئيسية:", chat_id, msg_id, reply_markup=main_menu(user_id, user_id == str(ADMIN_ID)))
        
        bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda m: True)
    def message_handler(message):
        user_id = str(message.from_user.id)
        text = message.text
        
        if user_id == str(ADMIN_ID) and user_states.get(user_id) == 'add_series_name':
            series = load_data('series')
            series[text] = []
            save_data('series', series)
            bot.reply_to(message, f"تم حفظ اسم المسلسل: {text}
الآن ارسل الفيديوهات ثم /done")
            user_states[user_id] = f'add_series_videos:{text}'
            save_data('states', user_states)
        
        elif user_id == str(ADMIN_ID) and user_states.get(user_id) and user_states[user_id].startswith('add_series_videos:'):
            series_name = user_states[user_id].split(':')[2]
            series = load_data('series')
            
            if text == '/done':
                bot.reply_to(message, f"✅ تم إضافة المسلسل {series_name}")
                user_states[user_id] = None
            else:
                series[series_name].append(message.video.file_id if message.video else None)
                save_data('series', series)
                bot.reply_to(message, f"تم إضافة فيديو لحلقة {len(series[series_name])}")
        
        elif user_id == str(ADMIN_ID) and user_states.get(user_id) == 'add_movie_name':
            movies = load_data('movies')
            movies[text] = []
            save_data('movies', movies)
            bot.reply_to(message, f"تم حفظ اسم الفيلم: {text}
الآن ارسل الفيديوهات ثم /done")
            user_states[user_id] = f'add_movie_videos:{text}'
        
        elif user_states.get(user_id) == 'searching':
            series = load_data('series')
            movies = load_data('movies')
            results = []
            
            for name in series:
                if text.lower() in name.lower():
                    results.append(f"📺 مسلسل: {name}")
            for name in movies:
                if text.lower() in name.lower():
                    results.append(f"🎥 فيلم: {name}")
            
            if results:
                kb = search_keyboard(results)
                bot.send_message(message.chat.id, "نتائج البحث:", reply_markup=kb)
            else:
                bot.send_message(message.chat.id, "لا توجد نتائج")
            user_states[user_id] = None
        
        else:
            bot.reply_to(message, "استخدم الأزرار!", reply_markup=main_menu(user_id))
