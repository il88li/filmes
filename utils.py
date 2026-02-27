from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_USERNAME, BOT_USERNAME
import telebot

def pagination_keyboard(items, page, prefix, user_id, per_page=5):
    total_pages = (len(items) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    kb = InlineKeyboardMarkup(row_width=1)
    for item in items[start:end]:
        kb.add(InlineKeyboardButton(item, callback_data=f"{prefix}:{item}:{page}"))
    if page > 0:
        kb.add(InlineKeyboardButton("السابق", callback_data=f"{prefix}:prev:{page-1}"))
    if page < total_pages - 1:
        kb.add(InlineKeyboardButton("التالي", callback_data=f"{prefix}:next:{page}"))
    kb.add(InlineKeyboardButton("رجوع", callback_data=f"back_main:{user_id}"))
    return kb

def episode_keyboard(series_name, episode, total, user_id):
    kb = InlineKeyboardMarkup()
    if episode > 1:
        kb.row(InlineKeyboardButton("السابقة", callback_data=f"ep:{series_name}:{episode-1}"))
    if episode < total:
        kb.row(InlineKeyboardButton("التالية", callback_data=f"ep:{series_name}:{episode+1}"))
    kb.row(
        InlineKeyboardButton("تقييم وملاحظة", callback_data=f"rate:{series_name}"),
        InlineKeyboardButton("ابلاغ", callback_data=f"report:{series_name}")
    )
    kb.add(InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data=f"back_main:{user_id}"))
    return kb

def main_menu(user_id, is_admin=False):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("مسلسلات", callback_data="menu_series"),
        InlineKeyboardButton("افلام عربي", callback_data="menu_movies")
    )
    kb.row(
        InlineKeyboardButton("بحث", callback_data="menu_search"),
        InlineKeyboardButton("توصيات", callback_data="menu_recommendations")
    )
    kb.row(
        InlineKeyboardButton("دعم البوت بالنجوم", callback_data="menu_support")
    )
    if is_admin:
        kb.row(InlineKeyboardButton("اداره", callback_data="menu_admin"))
    kb.add(InlineKeyboardButton("رجوع", callback_data="back_main"))
    return kb

def get_referral_link(user_id):
    return f"https://t.me/{BOT_USERNAME[1:]}?start={user_id}"
