from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import config
import database as db

async def is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE, channel: str = None) -> bool:
    """التحقق من اشتراك المستخدم في قناة معينة. إذا لم يحدد، يتحقق من القناة الإجبارية."""
    if channel is None:
        channel = config.FORCE_CHANNEL
    try:
        member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

async def force_subscribe_markup():
    keyboard = [
        [InlineKeyboardButton("اشترك في القناة", url=config.FORCE_CHANNEL_LINK)],
        [InlineKeyboardButton("تحقق من الاشتراك", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button(callback_data: str = "back"):
    return [InlineKeyboardButton("رجوع", callback_data=callback_data)]

def build_menu(buttons, n_cols=1, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons if isinstance(header_buttons, list) else [header_buttons])
    if footer_buttons:
        menu.append(footer_buttons if isinstance(footer_buttons, list) else [footer_buttons])
    return menu

async def user_can_access(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من أن المستخدم غير محظور ومستوفي شروط الدعوة (إن وجدت) ومشترك في القناة الإجبارية."""
    if await is_admin(user_id):
        return True

    # التحقق من الاشتراك الإجباري
    if not await check_subscription(user_id, context):
        return False

    user = db.get_user(user_id)
    if not user:
        return False

    if user[3] == 1:  # محظور
        return False

    # التحقق من نظام الدعوة
    invite_enabled = db.get_invite_setting('enabled') == 'true'
    if invite_enabled:
        if user[7] == 0:  # can_use_bot
            return False
    return True

async def ensure_subscribed(func):
    """ديكوريتور للتحقق من الاشتراك قبل تنفيذ الدالة."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not await user_can_access(user.id, context):
            # إذا كان غير مشترك، أرسل رسالة الاشتراك
            if not await check_subscription(user.id, context):
                await update.effective_message.reply_text(
                    "يرجى الاشتراك في القناة أولاً لاستخدام البوت.",
                    reply_markup=await force_subscribe_markup()
                )
            else:
                # مشترك لكن لا يستطيع استخدام البوت بسبب الدعوات
                await update.effective_message.reply_text(
                    "تحتاج إلى دعوة 5 أشخاص لاستخدام البوت. استخدم /start لعرض رابط الدعوة."
                )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def split_list(lst, page, page_size=10):
    """تقسيم القائمة للصفحات."""
    start = page * page_size
    end = start + page_size
    return lst[start:end], len(lst) > end
