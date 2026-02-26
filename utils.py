from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
import database as db

async def check_subscription(user_id, context, channel=None):
    """التحقق من اشتراك المستخدم في قناة معينة. إذا لم يحدد، يتحقق من القناة الإجبارية."""
    if channel is None:
        channel = config.FORCE_CHANNEL
    try:
        member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

async def force_subscribe_markup():
    keyboard = [[InlineKeyboardButton("اشترك في القناة", url=config.FORCE_CHANNEL_LINK)],
                [InlineKeyboardButton("تحقق من الاشتراك", callback_data="check_sub")]]
    return InlineKeyboardMarkup(keyboard)

def back_button(callback_data="back"):
    return [InlineKeyboardButton("رجوع", callback_data=callback_data)]

def build_menu(buttons, n_cols=1, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu

async def is_admin(user_id):
    return user_id == config.ADMIN_ID

async def user_can_access(user_id, context):
    """التحقق مما إذا كان المستخدم يستطيع استخدام البوت (غير محظور ومستوفي شروط الدعوة إن وجدت)."""
    if await is_admin(user_id):
        return True
    user = db.get_user(user_id)
    if not user:
        return False
    if user[3] == 1:  # محظور
        return False
    # التحقق من تفعيل نظام الدعوة
    invite_enabled = db.get_invite_setting('enabled') == 'true'
    if invite_enabled:
        if user[7] == 0:  # can_use_bot
            # يجب أن يدعو العدد المطلوب أولاً
            return False
    return True
