from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import config
import database as db
import utils
from invite import handle_new_user, handle_invite_link

# سيتم تسجيل هذه الدوال في main.py

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if args and args[0].startswith('invite_'):
        # مستخدم جديد عبر رابط دعوة
        inviter_id = int(args[0].split('_')[1])
        # تخزين معرف الداعي في user_data
        context.user_data['invited_by'] = inviter_id
        await update.message.reply_text("مرحباً! يرجى الاشتراك في القناة أولاً لتأكيد دعوتك.")
    else:
        # بداية عادية
        await update.message.reply_text("مرحباً بك في بوت الأفلام والمسلسلات!")

    # إضافة المستخدم إلى قاعدة البيانات
    db.add_user(user.id, user.username, user.first_name)

    # التحقق من الاشتراك الإجباري
    if not await utils.check_subscription(user.id, context):
        await update.message.reply_text(
            "يرجى الاشتراك في القناة أولاً لاستخدام البوت.",
            reply_markup=await utils.force_subscribe_markup()
        )
        return

    # بعد الاشتراك، تحقق من نظام الدعوة
    await handle_post_subscribe(update, context)

async def handle_post_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if await utils.is_admin(user.id):
        await show_main_menu(update, context)
        return

    invite_enabled = db.get_invite_setting('enabled') == 'true'
    if not invite_enabled:
        # نظام الدعوة معطل، يمكنه استخدام البوت مباشرة
        db.set_user_can_use(user.id, True)
        await show_main_menu(update, context)
        return

    user_data = db.get_user(user.id)
    if user_data and user_data[7] == 1:  # can_use_bot
        await show_main_menu(update, context)
    else:
        # يحتاج لدعوة أشخاص
        required = int(db.get_invite_setting('required_count') or 5)
        await update.message.reply_text(
            f"مرحباً! لاستخدام البوت، يجب عليك دعوة {required} من الأصدقاء للاشتراك في القناة.\n"
            "رابط الدعوة الخاص بك هو:\n"
            f"https://t.me/{config.BOT_USERNAME}?start=invite_{user.id}\n\n"
            "بعد أن يشترك كل صديق عبر رابطك في القناة، سيتم احتساب الدعوة.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("تحقق من الدعوات", callback_data="check_invites")
            ]])
        )

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

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if await utils.check_subscription(user.id, context):
        # بعد الاشتراك، تحقق من الدعوة
        # إذا كان هناك من دعاه، سجل ذلك
        if 'invited_by' in context.user_data:
            inviter_id = context.user_data['invited_by']
            # تحقق من أن المدعو ليس الداعي نفسه
            if inviter_id != user.id:
                # سجل الدعوة للداعي
                db.update_user_invites(inviter_id, user.id)
                # أرسل إشعار للمدير
                await context.bot.send_message(
                    config.ADMIN_ID,
                    f"قام المستخدم {user.id} بالاشتراك في القناة بدعوة من {inviter_id}."
                )
            # حذف البيانات المؤقتة
            del context.user_data['invited_by']

        await handle_post_subscribe(update, context)
    else:
        await query.edit_message_text(
            "لم تشترك بعد. يرجى الاشتراك ثم الضغط على تحقق.",
            reply_markup=await utils.force_subscribe_markup()
        )

# معالجات القوائم (مختصرة)
async def series_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # عرض قائمة المسلسلات مع أزرار تمرير
    query = update.callback_query
    await query.answer()
    # استرجاع المسلسلات من قاعدة البيانات
    series_list = db.execute_query("SELECT name FROM series ORDER BY name", fetchall=True)
    buttons = []
    for s in series_list:
        buttons.append(InlineKeyboardButton(s[0], callback_data=f"series_{s[0]}"))
    # إضافة أزرار التنقل (الصفحات) ولكن هنا سنبسط ونعرض الكل
    # يمكن إضافة pagination لاحقاً
    buttons.append(utils.back_button("back_main"))
    reply_markup = InlineKeyboardMarkup(utils.build_menu(buttons, n_cols=2))
    await query.edit_message_text("اختر مسلسل:", reply_markup=reply_markup)

# ... وهكذا لباقي الوظائف
