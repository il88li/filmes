from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import load_data, save_data
from utils import pagination_keyboard
import telebot
import threading
import time
from config import ADMIN_ID, CHANNELS

def admin_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("ادارة المسلسلات", callback_data="admin_series"))
    kb.add(InlineKeyboardButton("ادارة الأفلام", callback_data="admin_movies"))
    kb.add(InlineKeyboardButton("اذاعه", callback_data="admin_broadcast"))
    kb.add(InlineKeyboardButton("ادارة الأعضاء", callback_data="admin_users"))
    kb.add(InlineKeyboardButton("ادارة رابط الدعوة", callback_data="admin_invites"))
    kb.add(InlineKeyboardButton("ادارة القنوات", callback_data="admin_channels"))
    kb.add(InlineKeyboardButton("إدارة التوصيات", callback_data="admin_recs"))
    kb.add(InlineKeyboardButton("رجوع", callback_data="back_main"))
    return kb

def series_admin_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("اضافة مسلسل", callback_data="add_series"))
    kb.add(InlineKeyboardButton("تعديل اسم مسلسل", callback_data="edit_series_name"))
    kb.add(InlineKeyboardButton("حذف مسلسل", callback_data="delete_series"))
    kb.add(InlineKeyboardButton("رجوع", callback_data="menu_admin"))
    return kb

def movies_admin_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("اضافة فلم", callback_data="add_movie"))
    kb.add(InlineKeyboardButton("تعديل اسم فلم", callback_data="edit_movie_name"))
    kb.add(InlineKeyboardButton("حذف فلم", callback_data="delete_movie"))
    kb.add(InlineKeyboardButton("رجوع", callback_data="menu_admin"))
    return kb

def broadcast_progress(bot, chat_id, msg_id, users_list):
    total = len(users_list)
    sent = 0
    progress_msg = bot.edit_message_text("بدء الإذاعة... 0%", chat_id, msg_id)
    
    for i, user_id in enumerate(users_list):
        try:
            bot.send_message(user_id, "رسالة الإذاعة هنا")
            sent += 1
        except:
            pass
        progress = int((i+1)/total * 100)
        bot.edit_message_text(f"جاري الإرسال... {progress}% ({sent}/{total})", chat_id, msg_id)
        time.sleep(0.05)
    
    bot.edit_message_text(f"✅ تم الإرسال لـ {sent}/{total}", chat_id, msg_id) 
