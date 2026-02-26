from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import config
import database as db
import utils

# حالات المحادثات للإضافة
ADD_SERIES_NAME, ADD_SERIES_VIDEOS = range(2)
ADD_MOVIE_NAME, ADD_MOVIE_VIDEOS = range(2, 4)
# ... إلخ

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await utils.is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return
    keyboard = [
        [InlineKeyboardButton("ادارة المسلسلات", callback_data="admin_series")],
        [InlineKeyboardButton("ادارة الأفلام", callback_data="admin_movies")],
        [InlineKeyboardButton("اذاعه", callback_data="admin_broadcast")],
        [InlineKeyboardButton("ادارة الأعضاء", callback_data="admin_users")],
        [InlineKeyboardButton("ادارة رابط الدعوة", callback_data="admin_invite")],
        [InlineKeyboardButton("ادارة القنوات", callback_data="admin_channels")],
        [InlineKeyboardButton("ادارة التوصيات", callback_data="admin_recommend")],
        [InlineKeyboardButton("العودة", callback_data="back_main")]
    ]
    await update.message.reply_text("لوحة التحكم", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_series_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("اضافة مسلسل", callback_data="admin_add_series")],
        [InlineKeyboardButton("تعديل اسم مسلسل", callback_data="admin_edit_series")],
        [InlineKeyboardButton("حذف مسلسل", callback_data="admin_del_series")],
        utils.back_button("admin_back")
    ]
    await query.edit_message_text("ادارة المسلسلات", reply_markup=InlineKeyboardMarkup(keyboard))

# دوال إضافة المسلسل (مثال)
async def add_series_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("أرسل اسم المسلسل:")
    return ADD_SERIES_NAME

async def add_series_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    context.user_data['new_series'] = name
    # إنشاء السلسلة في قاعدة البيانات
    db.execute_query("INSERT INTO series (name) VALUES (?)", (name,))
    # الحصول على id السلسلة
    series = db.execute_query("SELECT id FROM series WHERE name = ?", (name,), fetchone=True)
    context.user_data['series_id'] = series[0]
    context.user_data['episode_count'] = 0
    await update.message.reply_text("أرسل الفيديو الأول (الحلقة 1)، وعند الانتهاء أرسل /done")
    return ADD_SERIES_VIDEOS

async def add_series_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    if not video:
        await update.message.reply_text("يرجى إرسال فيديو.")
        return ADD_SERIES_VIDEOS
    # حفظ الفيديو في قناة المسلسلات
    channel = db.execute_query("SELECT value FROM channels WHERE key='series_channel'", fetchone=True)
    if not channel:
        await update.message.reply_text("لم يتم تعيين قناة المسلسلات بعد.")
        return ConversationHandler.END
    channel_id = channel[0]
    # إرسال الفيديو إلى القناة
    sent = await context.bot.send_video(chat_id=channel_id, video=video.file_id, caption=f"مسلسل: {context.user_data['new_series']} - حلقة {context.user_data['episode_count']+1}")
    # تخزين message_id في قاعدة البيانات
    db.execute_query(
        "INSERT INTO episodes (series_id, episode_number, file_id, message_id) VALUES (?, ?, ?, ?)",
        (context.user_data['series_id'], context.user_data['episode_count']+1, video.file_id, sent.message_id)
    )
    context.user_data['episode_count'] += 1
    await update.message.reply_text(f"تم استلام الحلقة {context.user_data['episode_count']}. أرسل التالية أو /done للانتهاء.")
    return ADD_SERIES_VIDEOS

async def add_series_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # تحديث عدد الحلقات في جدول المسلسلات
    db.execute_query("UPDATE series SET total_episodes = ? WHERE id = ?", (context.user_data['episode_count'], context.user_data['series_id']))
    await update.message.reply_text("تم إضافة المسلسل بنجاح.")
    return ConversationHandler.END

# ... بقية دوال الإدارة
