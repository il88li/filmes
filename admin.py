from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import config
import database as db
import utils
import asyncio

# ========== حالات المحادثات (ثوابت) ==========
(ADD_SERIES_NAME, ADD_SERIES_VIDEOS,
 ADD_MOVIE_NAME, ADD_MOVIE_VIDEOS,
 EDIT_SERIES_OLD, EDIT_SERIES_NEW,
 EDIT_MOVIE_OLD, EDIT_MOVIE_NEW,
 DELETE_SERIES_NAME, DELETE_MOVIE_NAME,
 BROADCAST_MESSAGE,
 BAN_USER_ID, UNBAN_USER_ID,
 ADD_REC_TITLE, ADD_REC_PHOTO, ADD_REC_DESC,
 DEL_REC_TITLE,
 SET_SERIES_CH, SET_MOVIES_CH, SET_RECOMMENDATIONS_CH,
 FUNDING_CH, FUNDING_COUNT,
 SET_INVITE_COUNT) = range(23)

# ================== لوحة الإدارة الرئيسية ==================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await utils.is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ غير مصرح.")
        return
    keyboard = [
        [InlineKeyboardButton("📁 ادارة المسلسلات", callback_data="admin_series")],
        [InlineKeyboardButton("🎬 ادارة الأفلام", callback_data="admin_movies")],
        [InlineKeyboardButton("📢 اذاعه", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 ادارة الأعضاء", callback_data="admin_users")],
        [InlineKeyboardButton("🔗 ادارة رابط الدعوة", callback_data="admin_invite")],
        [InlineKeyboardButton("📡 ادارة القنوات", callback_data="admin_channels")],
        [InlineKeyboardButton("⭐ ادارة التوصيات", callback_data="admin_recommend")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main")]
    ]
    await update.message.reply_text("⚙️ لوحة التحكم", reply_markup=InlineKeyboardMarkup(keyboard))

# ================== ادارة المسلسلات ==================
async def admin_series_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("➕ إضافة مسلسل", callback_data="admin_add_series")],
        [InlineKeyboardButton("✏️ تعديل اسم مسلسل", callback_data="admin_edit_series")],
        [InlineKeyboardButton("❌ حذف مسلسل", callback_data="admin_del_series")],
        utils.back_button("admin_back")
    ]
    await query.edit_message_text("📁 إدارة المسلسلات", reply_markup=InlineKeyboardMarkup(keyboard))

# --- إضافة مسلسل ---
async def add_series_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("add_series_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✏️ أرسل اسم المسلسل:")
    return ADD_SERIES_NAME

async def add_series_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("add_series_get_name called")
    name = update.message.text.strip()
    series_id = db.add_series(name)
    if not series_id:
        await update.message.reply_text("⚠️ المسلسل موجود بالفعل.")
        return ConversationHandler.END
    context.user_data['new_series'] = name
    context.user_data['series_id'] = series_id
    context.user_data['episode_count'] = 0
    await update.message.reply_text("🎥 أرسل الفيديو الأول (الحلقة 1)، وعند الانتهاء أرسل /done")
    return ADD_SERIES_VIDEOS

async def add_series_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("add_series_video called")
    video = update.message.video
    if not video:
        await update.message.reply_text("❌ يرجى إرسال فيديو.")
        return ADD_SERIES_VIDEOS

    channel = db.get_channel('series_channel')
    if not channel:
        await update.message.reply_text("❌ لم يتم تعيين قناة المسلسلات بعد. استخدم /admin لتعيينها.")
        return ConversationHandler.END

    series_name = context.user_data['new_series']
    ep_num = context.user_data['episode_count'] + 1
    try:
        sent = await context.bot.send_video(
            chat_id=channel,
            video=video.file_id,
            caption=f"📺 مسلسل: {series_name} - حلقة {ep_num}"
        )
        db.add_episode(context.user_data['series_id'], ep_num, video.file_id, sent.message_id)
        context.user_data['episode_count'] = ep_num
        await update.message.reply_text(f"✅ تم استلام الحلقة {ep_num}. أرسل التالية أو /done للانتهاء.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في الإرسال إلى القناة: {e}")
        return ADD_SERIES_VIDEOS

    return ADD_SERIES_VIDEOS

async def add_series_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("add_series_done called")
    await update.message.reply_text("✅ تم إضافة المسلسل بنجاح.")
    return ConversationHandler.END

# --- تعديل اسم مسلسل ---
async def edit_series_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("edit_series_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✏️ أرسل اسم المسلسل الذي تريد تعديله:")
    return EDIT_SERIES_OLD

async def edit_series_get_old(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("edit_series_get_old called")
    old_name = update.message.text.strip()
    series = db.get_series_by_name(old_name)
    if not series:
        await update.message.reply_text("❌ المسلسل غير موجود.")
        return ConversationHandler.END
    context.user_data['old_series'] = old_name
    await update.message.reply_text("✏️ أرسل الاسم الجديد:")
    return EDIT_SERIES_NEW

async def edit_series_get_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("edit_series_get_new called")
    new_name = update.message.text.strip()
    old_name = context.user_data['old_series']
    db.update_series_name(old_name, new_name)
    await update.message.reply_text("✅ تم تعديل الاسم بنجاح.")
    return ConversationHandler.END

# --- حذف مسلسل ---
async def delete_series_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("delete_series_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ أرسل اسم المسلسل الذي تريد حذفه:")
    return DELETE_SERIES_NAME

async def delete_series_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("delete_series_confirm called")
    name = update.message.text.strip()
    db.delete_series(name)
    await update.message.reply_text("✅ تم الحذف بنجاح.")
    return ConversationHandler.END

# ================== ادارة الأفلام ==================
async def admin_movies_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("➕ إضافة فيلم", callback_data="admin_add_movie")],
        [InlineKeyboardButton("✏️ تعديل اسم فيلم", callback_data="admin_edit_movie")],
        [InlineKeyboardButton("❌ حذف فيلم", callback_data="admin_del_movie")],
        utils.back_button("admin_back")
    ]
    await query.edit_message_text("🎬 إدارة الأفلام", reply_markup=InlineKeyboardMarkup(keyboard))

# --- إضافة فيلم ---
async def add_movie_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("add_movie_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✏️ أرسل اسم الفيلم:")
    return ADD_MOVIE_NAME

async def add_movie_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("add_movie_get_name called")
    name = update.message.text.strip()
    movie_id = db.add_movie(name)
    if not movie_id:
        await update.message.reply_text("⚠️ الفيلم موجود بالفعل.")
        return ConversationHandler.END
    context.user_data['new_movie'] = name
    context.user_data['movie_id'] = movie_id
    context.user_data['part_count'] = 0
    await update.message.reply_text("🎥 أرسل الجزء الأول، وعند الانتهاء أرسل /done")
    return ADD_MOVIE_VIDEOS

async def add_movie_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("add_movie_video called")
    video = update.message.video
    if not video:
        await update.message.reply_text("❌ يرجى إرسال فيديو.")
        return ADD_MOVIE_VIDEOS

    channel = db.get_channel('movies_channel')
    if not channel:
        await update.message.reply_text("❌ لم يتم تعيين قناة الأفلام بعد.")
        return ConversationHandler.END

    movie_name = context.user_data['new_movie']
    part_num = context.user_data['part_count'] + 1
    try:
        sent = await context.bot.send_video(
            chat_id=channel,
            video=video.file_id,
            caption=f"🎬 فيلم: {movie_name} - جزء {part_num}"
        )
        db.add_movie_part(context.user_data['movie_id'], part_num, video.file_id, sent.message_id)
        context.user_data['part_count'] = part_num
        await update.message.reply_text(f"✅ تم استلام الجزء {part_num}. أرسل الجزء التالي أو /done للانتهاء.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")
    return ADD_MOVIE_VIDEOS

async def add_movie_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("add_movie_done called")
    await update.message.reply_text("✅ تم إضافة الفيلم بنجاح.")
    return ConversationHandler.END

# --- تعديل اسم فيلم ---
async def edit_movie_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("edit_movie_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✏️ أرسل اسم الفيلم الذي تريد تعديله:")
    return EDIT_MOVIE_OLD

async def edit_movie_get_old(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("edit_movie_get_old called")
    old_name = update.message.text.strip()
    movie = db.get_movie_by_name(old_name)
    if not movie:
        await update.message.reply_text("❌ الفيلم غير موجود.")
        return ConversationHandler.END
    context.user_data['old_movie'] = old_name
    await update.message.reply_text("✏️ أرسل الاسم الجديد:")
    return EDIT_MOVIE_NEW

async def edit_movie_get_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("edit_movie_get_new called")
    new_name = update.message.text.strip()
    old_name = context.user_data['old_movie']
    db.update_movie_name(old_name, new_name)
    await update.message.reply_text("✅ تم تعديل الاسم بنجاح.")
    return ConversationHandler.END

# --- حذف فيلم ---
async def delete_movie_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("delete_movie_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ أرسل اسم الفيلم الذي تريد حذفه:")
    return DELETE_MOVIE_NAME

async def delete_movie_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("delete_movie_confirm called")
    name = update.message.text.strip()
    db.delete_movie(name)
    await update.message.reply_text("✅ تم الحذف بنجاح.")
    return ConversationHandler.END

# ================== اذاعه ==================
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("broadcast_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📨 أرسل الرسالة التي تريد إذاعتها لجميع المستخدمين:")
    return BROADCAST_MESSAGE

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("broadcast_send called")
    message = update.message
    users = db.get_all_users()
    print(f"عدد المستخدمين: {len(users)}")
    total = len(users)
    sent = 0
    failed = 0
    status_msg = await update.message.reply_text("🔄 جاري الإرسال... 0%")
    for i, user_id in enumerate(users):
        try:
            await message.copy(chat_id=user_id)
            sent += 1
        except Exception as e:
            failed += 1
            print(f"فشل الإرسال إلى {user_id}: {e}")
        if (i+1) % 10 == 0:
            percent = int((i+1)/total*100)
            await status_msg.edit_text(f"🔄 جاري الإرسال... {percent}%")
        await asyncio.sleep(0.05)
    await status_msg.edit_text(f"✅ تم الإرسال: {sent} نجاح، {failed} فشل.")
    return ConversationHandler.END

# ================== ادارة الأعضاء ==================
async def admin_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🔨 حظر عضو", callback_data="admin_ban")],
        [InlineKeyboardButton("🔓 رفع حظر", callback_data="admin_unban")],
        utils.back_button("admin_back")
    ]
    await query.edit_message_text("👥 إدارة الأعضاء", reply_markup=InlineKeyboardMarkup(keyboard))

async def ban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("ban_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🚫 أرسل أيدي العضو المراد حظره:")
    return BAN_USER_ID

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("ban_user called")
    try:
        user_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ الرجاء إرسال رقم صحيح.")
        return BAN_USER_ID
    db.set_user_banned(user_id, True)
    await update.message.reply_text("✅ تم الحظر.")
    return ConversationHandler.END

async def unban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("unban_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔓 أرسل أيدي العضو المراد رفع الحظر عنه:")
    return UNBAN_USER_ID

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("unban_user called")
    try:
        user_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ الرجاء إرسال رقم صحيح.")
        return UNBAN_USER_ID
    db.set_user_banned(user_id, False)
    await update.message.reply_text("✅ تم رفع الحظر.")
    return ConversationHandler.END

# ================== ادارة رابط الدعوة ==================
async def admin_invite_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    enabled = db.get_invite_setting('enabled') == 'true'
    required = db.get_invite_setting('required_count')
    status = "🟢 مفعل" if enabled else "🔴 معطل"
    keyboard = [
        [InlineKeyboardButton(f"تبديل الحالة ({status})", callback_data="admin_toggle_invite")],
        [InlineKeyboardButton("تعيين العدد", callback_data="admin_set_invite_count")],
        utils.back_button("admin_back")
    ]
    text = f"🔗 نظام الدعوة\nالحالة: {status}\nالعدد المطلوب: {required}"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def toggle_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    current = db.get_invite_setting('enabled')
    new = 'false' if current == 'true' else 'true'
    db.set_invite_setting('enabled', new)
    await admin_invite_menu(update, context)

async def set_invite_count_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("set_invite_count_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔢 أرسل العدد المطلوب من الدعوات:")
    return SET_INVITE_COUNT

async def set_invite_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("set_invite_count called")
    try:
        count = int(update.message.text.strip())
        if count < 1:
            raise ValueError
    except:
        await update.message.reply_text("❌ الرجاء إرسال رقم صحيح أكبر من 0.")
        return SET_INVITE_COUNT
    db.set_invite_setting('required_count', str(count))
    await update.message.reply_text("✅ تم تعيين العدد.")
    return ConversationHandler.END

# ================== ادارة القنوات ==================
async def admin_channels_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    series_ch = db.get_channel('series_channel') or 'غير معين'
    movies_ch = db.get_channel('movies_channel') or 'غير معين'
    recommendations_ch = db.get_recommendations_channel() or 'غير معين'
    funding = db.get_funding_channel()
    funding_text = f"قناة تمويل: {funding[0] if funding else 'لا يوجد'} (مطلوب {funding[1] if funding else 0})" if funding else "لا توجد قناة تمويل حالياً"
    keyboard = [
        [InlineKeyboardButton("تعيين قناة الأفلام", callback_data="admin_set_movies_ch")],
        [InlineKeyboardButton("تعيين قناة المسلسلات", callback_data="admin_set_series_ch")],
        [InlineKeyboardButton("تعيين قناة التوصيات", callback_data="admin_set_recommendations_ch")],
        [InlineKeyboardButton("تمويل قناة", callback_data="admin_funding")],
        utils.back_button("admin_back")
    ]
    text = (f"📺 قناة المسلسلات: {series_ch}\n"
            f"🎬 قناة الأفلام: {movies_ch}\n"
            f"🖼️ قناة التوصيات: {recommendations_ch}\n"
            f"{funding_text}")
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# --- تعيين قناة المسلسلات ---
async def set_series_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("set_series_channel_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📢 أرسل معرف القناة (مثال: @channel) لقناة المسلسلات:")
    return SET_SERIES_CH

async def set_series_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("set_series_channel called")
    try:
        ch = update.message.text.strip()
        db.set_channel('series_channel', ch)
        await update.message.reply_text("✅ تم تعيين قناة المسلسلات.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")
    return ConversationHandler.END

# --- تعيين قناة الأفلام ---
async def set_movies_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("set_movies_channel_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📢 أرسل معرف القناة (مثال: @channel) لقناة الأفلام:")
    return SET_MOVIES_CH

async def set_movies_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("set_movies_channel called")
    try:
        ch = update.message.text.strip()
        db.set_channel('movies_channel', ch)
        await update.message.reply_text("✅ تم تعيين قناة الأفلام.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")
    return ConversationHandler.END

# --- تعيين قناة التوصيات ---
async def set_recommendations_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("set_recommendations_channel_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🖼️ أرسل معرف القناة (مثال: @channel) لقناة التوصيات (لتخزين الصور):")
    return SET_RECOMMENDATIONS_CH

async def set_recommendations_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("set_recommendations_channel called")
    try:
        ch = update.message.text.strip()
        db.set_recommendations_channel(ch)
        await update.message.reply_text("✅ تم تعيين قناة التوصيات.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")
    return ConversationHandler.END

# --- تمويل قناة ---
async def funding_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("funding_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("💰 أرسل معرف القناة المراد تمويلها (مثال: @channel):")
    return FUNDING_CH

async def funding_get_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("funding_get_channel called")
    ch = update.message.text.strip()
    context.user_data['funding_ch'] = ch
    await update.message.reply_text("🔢 أرسل عدد الأعضاء المطلوب:")
    return FUNDING_COUNT

async def funding_get_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("funding_get_count called")
    try:
        count = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ الرجاء إرسال رقم صحيح.")
        return FUNDING_COUNT
    ch = context.user_data['funding_ch']
    db.set_funding_channel(ch, count)
    await update.message.reply_text("✅ تم تعيين قناة التمويل. سيتم متابعة الأعضاء الجدد.")
    return ConversationHandler.END

# ================== ادارة التوصيات ==================
async def admin_recommend_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("➕ إضافة توصية", callback_data="admin_add_rec")],
        [InlineKeyboardButton("❌ حذف توصية", callback_data="admin_del_rec")],
        utils.back_button("admin_back")
    ]
    await query.edit_message_text("⭐ إدارة التوصيات", reply_markup=InlineKeyboardMarkup(keyboard))

# --- إضافة توصية ---
async def add_rec_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("add_rec_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✏️ أرسل اسم المسلسل أو الفيلم للتوصية:")
    return ADD_REC_TITLE

async def add_rec_get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("add_rec_get_title called with text:", update.message.text)
    title = update.message.text.strip()
    series = db.get_series_by_name(title)
    movie = db.get_movie_by_name(title)
    if not series and not movie:
        await update.message.reply_text("❌ لم يتم العثور على هذا الاسم. تأكد من كتابته بشكل صحيح.")
        return ADD_REC_TITLE
    if series:
        context.user_data['rec_content_type'] = 'series'
        context.user_data['rec_content_id'] = series[0]
    else:
        context.user_data['rec_content_type'] = 'movie'
        context.user_data['rec_content_id'] = movie[0]
    context.user_data['rec_title'] = title
    await update.message.reply_text("🖼️ أرسل صورة للتوصية:")
    return ADD_REC_PHOTO

async def add_rec_get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("add_rec_get_photo called")
    photo = update.message.photo
    if not photo:
        await update.message.reply_text("❌ يرجى إرسال صورة.")
        return ADD_REC_PHOTO

    file_id = photo[-1].file_id

    rec_channel = db.get_recommendations_channel()
    if rec_channel:
        try:
            await context.bot.send_photo(chat_id=rec_channel, photo=file_id, caption=f"🖼️ صورة توصية: {context.user_data['rec_title']}")
        except Exception as e:
            await update.message.reply_text(f"⚠️ تحذير: لم نتمكن من إرسال الصورة إلى قناة التوصيات: {e}")

    context.user_data['rec_photo'] = file_id
    await update.message.reply_text("📝 أرسل وصفاً نصياً للتوصية:")
    return ADD_REC_DESC

async def add_rec_get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("add_rec_get_desc called")
    desc = update.message.text.strip()
    db.add_recommendation(
        context.user_data['rec_title'],
        context.user_data['rec_content_type'],
        context.user_data['rec_content_id'],
        context.user_data['rec_photo'],
        desc
    )
    await update.message.reply_text("✅ تم إضافة التوصية.")
    return ConversationHandler.END

# --- حذف توصية ---
async def del_rec_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("del_rec_start called")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ أرسل اسم التوصية (العنوان) التي تريد حذفها:")
    return DEL_REC_TITLE

async def del_rec_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("del_rec_confirm called")
    title = update.message.text.strip()
    db.delete_recommendation(title)
    await update.message.reply_text("✅ تم الحذف.")
    return ConversationHandler.END

# ================== رجوع للوحة الإدارة ==================
async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📁 ادارة المسلسلات", callback_data="admin_series")],
        [InlineKeyboardButton("🎬 ادارة الأفلام", callback_data="admin_movies")],
        [InlineKeyboardButton("📢 اذاعه", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 ادارة الأعضاء", callback_data="admin_users")],
        [InlineKeyboardButton("🔗 ادارة رابط الدعوة", callback_data="admin_invite")],
        [InlineKeyboardButton("📡 ادارة القنوات", callback_data="admin_channels")],
        [InlineKeyboardButton("⭐ ادارة التوصيات", callback_data="admin_recommend")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main")]
    ]
    await query.edit_message_text("⚙️ لوحة التحكم", reply_markup=InlineKeyboardMarkup(keyboard))

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم الإلغاء.")
    return ConversationHandler.END
