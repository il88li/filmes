from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
import config
import database as db
import utils
from utils import ensure_subscribed

# ================== البداية والاشتراك ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    # تخزين معرف الداعي إن وجد
    inviter_id = None
    if args and args[0].startswith('invite_'):
        try:
            inviter_id = int(args[0].split('_')[1])
            if inviter_id == user.id:
                inviter_id = None  # لا يمكن دعوة النفس
            else:
                context.user_data['invited_by'] = inviter_id
        except:
            pass

    # إضافة المستخدم إلى قاعدة البيانات
    db.add_user(user.id, user.username, user.first_name, invite_link_used=inviter_id)

    # التحقق من الاشتراك الإجباري
    if not await utils.check_subscription(user.id, context):
        await update.message.reply_text(
            "يرجى الاشتراك في القناة أولاً لاستخدام البوت.",
            reply_markup=await utils.force_subscribe_markup()
        )
        return

    await handle_post_subscribe(update, context)

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if await utils.check_subscription(user.id, context):
        # تحقق من وجود داعي
        if 'invited_by' in context.user_data:
            inviter_id = context.user_data['invited_by']
            if inviter_id and inviter_id != user.id:
                # سجل الدعوة للداعي إذا كان موجوداً
                db.update_user_invites(inviter_id, user.id)
                # إشعار المدير
                await context.bot.send_message(
                    config.ADMIN_ID,
                    f"✅ مستخدم جديد {user.id} اشترك في القناة بدعوة من {inviter_id}."
                )
            del context.user_data['invited_by']

        await handle_post_subscribe(update, context)
    else:
        await query.edit_message_text(
            "لم تشترك بعد. يرجى الاشتراك ثم الضغط على تحقق.",
            reply_markup=await utils.force_subscribe_markup()
        )

async def handle_post_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if await utils.is_admin(user.id):
        await show_main_menu(update, context)
        return

    invite_enabled = db.get_invite_setting('enabled') == 'true'
    user_data = db.get_user(user.id)
    if not invite_enabled or (user_data and user_data[7] == 1):
        # يمكنه استخدام البوت
        await show_main_menu(update, context)
    else:
        # يحتاج لدعوة
        required = int(db.get_invite_setting('required_count') or 5)
        await update.effective_message.reply_text(
            f"مرحباً! لاستخدام البوت، يجب عليك دعوة {required} من الأصدقاء للاشتراك في القناة.\n"
            f"رابط الدعوة الخاص بك هو:\n"
            f"https://t.me/{config.BOT_USERNAME}?start=invite_{user.id}\n\n"
            "بعد أن يشترك كل صديق عبر رابطك في القناة، سيتم احتساب الدعوة.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("تحقق من الدعوات", callback_data="check_invites")
            ]])
        )

async def check_invites_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_data = db.get_user(user.id)
    if not user_data:
        await query.edit_message_text("حدث خطأ. أعد المحاولة.")
        return
    current = user_data[5]  # invites_count
    required = int(db.get_invite_setting('required_count') or 5)
    if current >= required:
        db.set_user_can_use(user.id, True)
        await query.edit_message_text("تهانينا! يمكنك الآن استخدام البوت.")
        await show_main_menu(update, context)
    else:
        await query.edit_message_text(
            f"لقد دعوت {current} من أصل {required}. استمر في الدعوة.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("رجوع", callback_data="back_start")
            ]])
        )

# ================== القائمة الرئيسية ==================
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("مسلسلات", callback_data="menu_series")],
        [InlineKeyboardButton("افلام عربي", callback_data="menu_movies")],
        [InlineKeyboardButton("بحث", callback_data="menu_search")],
        [InlineKeyboardButton("توصيات", callback_data="menu_recommendations")],
        [InlineKeyboardButton("دعم البوت بالنجوم", callback_data="menu_support")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text("القائمة الرئيسية", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("القائمة الرئيسية", reply_markup=InlineKeyboardMarkup(keyboard))

# ================== المسلسلات ==================
@ensure_subscribed
async def series_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    series_list = db.get_all_series_names()
    if not series_list:
        await query.edit_message_text("لا توجد مسلسلات حالياً.", reply_markup=InlineKeyboardMarkup([utils.back_button("back_main")]))
        return

    # تخزين القائمة في context للتنقل
    context.user_data['series_list'] = series_list
    context.user_data['series_page'] = 0
    await show_series_page(update, context)

async def show_series_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    series_list = context.user_data.get('series_list', [])
    page = context.user_data.get('series_page', 0)
    page_size = 10
    start = page * page_size
    end = start + page_size
    current_page = series_list[start:end]
    has_next = end < len(series_list)
    has_prev = page > 0

    buttons = []
    for name in current_page:
        buttons.append(InlineKeyboardButton(name, callback_data=f"series_{name}"))

    nav_buttons = []
    if has_prev:
        nav_buttons.append(InlineKeyboardButton("السابق", callback_data="series_prev"))
    if has_next:
        nav_buttons.append(InlineKeyboardButton("التالي", callback_data="series_next"))
    footer = nav_buttons + [InlineKeyboardButton("رجوع", callback_data="back_main")]

    reply_markup = InlineKeyboardMarkup(utils.build_menu(buttons, n_cols=2, footer_buttons=footer))
    await query.edit_message_text("اختر مسلسل:", reply_markup=reply_markup)

async def series_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "series_next":
        context.user_data['series_page'] = context.user_data.get('series_page', 0) + 1
    elif data == "series_prev":
        context.user_data['series_page'] = context.user_data.get('series_page', 0) - 1
    await show_series_page(update, context)

async def series_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    series_name = query.data.split('_', 1)[1]
    series = db.get_series_by_name(series_name)
    if not series:
        await query.edit_message_text("المسلسل غير موجود.", reply_markup=InlineKeyboardMarkup([utils.back_button("menu_series")]))
        return
    series_id = series[0]
    episodes = db.get_episodes(series_id)
    if not episodes:
        await query.edit_message_text("لا توجد حلقات لهذا المسلسل.", reply_markup=InlineKeyboardMarkup([utils.back_button("menu_series")]))
        return

    # تخزين بيانات المسلسل
    context.user_data['current_series'] = {
        'id': series_id,
        'name': series_name,
        'episodes': episodes,
        'current_episode': 0  # الفهرس
    }
    await show_episode(update, context)

async def show_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    series_data = context.user_data['current_series']
    ep_index = series_data['current_episode']
    episodes = series_data['episodes']
    ep_number, file_id, message_id = episodes[ep_index]

    # الحصول على متوسط التقييم
    avg_rating = db.get_average_rating('series', series_data['id'])
    rating_text = f"⭐ متوسط التقييم: {avg_rating:.1f}/10" if avg_rating else "لم يتم التقييم بعد"

    keyboard = [
        [InlineKeyboardButton("تقييم وملاحظة", callback_data=f"rate_series_{series_data['id']}"),
         InlineKeyboardButton("ابلاغ", callback_data=f"report_series_{series_data['id']}")]
    ]
    # أزرار التنقل بين الحلقات
    nav = []
    if ep_index > 0:
        nav.append(InlineKeyboardButton("السابقة", callback_data="ep_prev"))
    if ep_index < len(episodes) - 1:
        nav.append(InlineKeyboardButton("التالية", callback_data="ep_next"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data="back_main")])

    await query.delete_message()  # حذف الرسالة السابقة
    await context.bot.send_video(
        chat_id=query.message.chat_id,
        video=file_id,
        caption=f"🎬 {series_data['name']} - الحلقة {ep_number}\n{rating_text}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def episode_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    series_data = context.user_data.get('current_series')
    if not series_data:
        await query.edit_message_text("حدث خطأ.", reply_markup=InlineKeyboardMarkup([utils.back_button("menu_series")]))
        return
    if query.data == "ep_next":
        series_data['current_episode'] += 1
    elif query.data == "ep_prev":
        series_data['current_episode'] -= 1
    context.user_data['current_series'] = series_data
    await show_episode(update, context)

# ================== التقييم ==================
async def rate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    # مثال: rate_series_5
    parts = data.split('_')
    content_type = parts[1]  # series or movie
    content_id = int(parts[2])
    context.user_data['rating_content'] = (content_type, content_id)

    # عرض أزرار التقييم من 1 إلى 10
    buttons = []
    for i in range(1, 11):
        buttons.append(InlineKeyboardButton(str(i), callback_data=f"set_rate_{i}"))
    # تقسيم إلى صفين (5 لكل صف)
    row1 = buttons[:5]
    row2 = buttons[5:]
    keyboard = [row1, row2, [InlineKeyboardButton("رجوع", callback_data="back_to_content")]]
    await query.edit_message_text("اختر تقييمك من 1 إلى 10:", reply_markup=InlineKeyboardMarkup(keyboard))

async def set_rate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rating = int(query.data.split('_')[2])
    content_type, content_id = context.user_data.get('rating_content', (None, None))
    if not content_type:
        await query.edit_message_text("حدث خطأ.")
        return
    user_id = query.from_user.id
    db.add_rating(user_id, content_type, content_id, rating)
    await query.edit_message_text(f"تم تسجيل تقييمك: {rating}/10. شكراً لك!", reply_markup=InlineKeyboardMarkup([utils.back_button("back_to_content")]))

async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split('_')
    content_type = parts[1]
    content_id = int(parts[2])
    user_id = query.from_user.id
    db.add_report(user_id, content_type, content_id)
    await query.edit_message_text("تم الإبلاغ. شكراً لمساعدتك.", reply_markup=InlineKeyboardMarkup([utils.back_button("back_to_content")]))

# ================== الأفلام (مشابه للمسلسلات) ==================
@ensure_subscribed
async def movies_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movies_list = db.get_all_movies_names()
    if not movies_list:
        await query.edit_message_text("لا توجد أفلام حالياً.", reply_markup=InlineKeyboardMarkup([utils.back_button("back_main")]))
        return
    context.user_data['movies_list'] = movies_list
    context.user_data['movies_page'] = 0
    await show_movies_page(update, context)

async def show_movies_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    movies_list = context.user_data.get('movies_list', [])
    page = context.user_data.get('movies_page', 0)
    page_size = 10
    start = page * page_size
    end = start + page_size
    current_page = movies_list[start:end]
    has_next = end < len(movies_list)
    has_prev = page > 0

    buttons = []
    for name in current_page:
        buttons.append(InlineKeyboardButton(name, callback_data=f"movie_{name}"))

    nav_buttons = []
    if has_prev:
        nav_buttons.append(InlineKeyboardButton("السابق", callback_data="movies_prev"))
    if has_next:
        nav_buttons.append(InlineKeyboardButton("التالي", callback_data="movies_next"))
    footer = nav_buttons + [InlineKeyboardButton("رجوع", callback_data="back_main")]

    reply_markup = InlineKeyboardMarkup(utils.build_menu(buttons, n_cols=2, footer_buttons=footer))
    await query.edit_message_text("اختر فيلم:", reply_markup=reply_markup)

async def movies_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "movies_next":
        context.user_data['movies_page'] += 1
    elif data == "movies_prev":
        context.user_data['movies_page'] -= 1
    await show_movies_page(update, context)

async def movie_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_name = query.data.split('_', 1)[1]
    movie = db.get_movie_by_name(movie_name)
    if not movie:
        await query.edit_message_text("الفيلم غير موجود.", reply_markup=InlineKeyboardMarkup([utils.back_button("menu_movies")]))
        return
    movie_id = movie[0]
    parts = db.get_movie_parts(movie_id)
    if not parts:
        await query.edit_message_text("لا توجد أجزاء لهذا الفيلم.", reply_markup=InlineKeyboardMarkup([utils.back_button("menu_movies")]))
        return

    context.user_data['current_movie'] = {
        'id': movie_id,
        'name': movie_name,
        'parts': parts,
        'current_part': 0
    }
    await show_movie_part(update, context)

async def show_movie_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    movie_data = context.user_data['current_movie']
    part_index = movie_data['current_part']
    parts = movie_data['parts']
    part_number, file_id, message_id = parts[part_index]

    avg_rating = db.get_average_rating('movie', movie_data['id'])
    rating_text = f"⭐ متوسط التقييم: {avg_rating:.1f}/10" if avg_rating else "لم يتم التقييم بعد"

    keyboard = [
        [InlineKeyboardButton("تقييم وملاحظة", callback_data=f"rate_movie_{movie_data['id']}"),
         InlineKeyboardButton("ابلاغ", callback_data=f"report_movie_{movie_data['id']}")]
    ]
    nav = []
    if part_index > 0:
        nav.append(InlineKeyboardButton("السابق", callback_data="part_prev"))
    if part_index < len(parts) - 1:
        nav.append(InlineKeyboardButton("التالي", callback_data="part_next"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data="back_main")])

    await query.delete_message()
    await context.bot.send_video(
        chat_id=query.message.chat_id,
        video=file_id,
        caption=f"🎬 {movie_data['name']} - الجزء {part_number}\n{rating_text}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def part_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_data = context.user_data.get('current_movie')
    if not movie_data:
        await query.edit_message_text("حدث خطأ.", reply_markup=InlineKeyboardMarkup([utils.back_button("menu_movies")]))
        return
    if query.data == "part_next":
        movie_data['current_part'] += 1
    elif query.data == "part_prev":
        movie_data['current_part'] -= 1
    context.user_data['current_movie'] = movie_data
    await show_movie_part(update, context)

# ================== البحث ==================
@ensure_subscribed
async def search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "أرسل اسم المسلسل أو الفيلم الذي تبحث عنه:",
        reply_markup=InlineKeyboardMarkup([utils.back_button("back_main")])
    )
    # ننتظر رسالة نصية من المستخدم
    return "SEARCH"  # حالة للـ ConversationHandler

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # البحث في المسلسلات
    series_names = db.get_all_series_names()
    movie_names = db.get_all_movies_names()
    results = []
    for name in series_names:
        if text.lower() in name.lower():
            results.append(("مسلسل", name))
    for name in movie_names:
        if text.lower() in name.lower():
            results.append(("فيلم", name))

    if not results:
        await update.message.reply_text("لا توجد نتائج.", reply_markup=InlineKeyboardMarkup([utils.back_button("back_main")]))
        return

    buttons = []
    for typ, name in results:
        if typ == "مسلسل":
            buttons.append(InlineKeyboardButton(f"📺 {name}", callback_data=f"series_{name}"))
        else:
            buttons.append(InlineKeyboardButton(f"🎥 {name}", callback_data=f"movie_{name}"))
    buttons.append(utils.back_button("back_main"))
    reply_markup = InlineKeyboardMarkup(utils.build_menu(buttons, n_cols=1))
    await update.message.reply_text("نتائج البحث:", reply_markup=reply_markup)
    # إنهاء الحالة
    return -1

# ================== التوصيات ==================
@ensure_subscribed
async def recommendations_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    recs = db.get_all_recommendations()
    if not recs:
        await query.edit_message_text("لا توجد توصيات حالياً.", reply_markup=InlineKeyboardMarkup([utils.back_button("back_main")]))
        return
    context.user_data['recommendations'] = recs
    context.user_data['rec_index'] = 0
    await show_recommendation(update, context)

async def show_recommendation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    recs = context.user_data['recommendations']
    index = context.user_data['rec_index']
    title, content_type, content_id, photo, desc = recs[index]

    keyboard = []
    nav = []
    if index > 0:
        nav.append(InlineKeyboardButton("السابقة", callback_data="rec_prev"))
    if index < len(recs) - 1:
        nav.append(InlineKeyboardButton("التالية", callback_data="rec_next"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data="back_main")])

    if photo:
        await query.delete_message()
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=photo,
            caption=f"*{title}*\n\n{desc}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text(
            f"*{title}*\n\n{desc}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def rec_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "rec_next":
        context.user_data['rec_index'] += 1
    elif query.data == "rec_prev":
        context.user_data['rec_index'] -= 1
    await show_recommendation(update, context)

# ================== دعم البوت ==================
async def support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    message = (
        "عزيزي المستخدم،\n\n"
        "نحن فريق صغير يعمل بجد لتوفير محتوى ترفيهي ممتع لك. البوت يعتمد على دعمكم ليبقى مستمراً.\n"
        "إذا أعجبك البوت، يمكنك دعمنا بإرسال نجوم (Stars) إلى حساب المدير:\n"
        f"@{config.ADMIN_ID} (هذا ليس اسم مستخدم صحيح، أضف @OlIiIl7)\n\n"
        "كل نجمة تصلنا تزيد من حماسنا لتطوير البوت وإضافة المزيد من الأفلام والمسلسلات.\n"
        "شكراً لدعمك ❤️"
    )
    # تصحيح: اسم المستخدم الصحيح هو @OlIiIl7
    message = message.replace("@6689435577", "@OlIiIl7")
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup([utils.back_button("back_main")])
    )

# ================== أزرار الرجوع العامة ==================
async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "back_main":
        await show_main_menu(update, context)
    elif data == "back_to_content":
        # العودة إلى المحتوى الحالي (مسلسل أو فيلم)
        if 'current_series' in context.user_data:
            await show_episode(update, context)
        elif 'current_movie' in context.user_data:
            await show_movie_part(update, context)
        else:
            await show_main_menu(update, context)
    elif data == "back_start":
        await handle_post_subscribe(update, context)
    else:
        # افتراضياً الرجوع للقائمة الرئيسية
        await show_main_menu(update, context) 
