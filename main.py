#!/usr/bin/env python3
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from telegram import Update
import config
import database as db
import handlers
import admin
from admin import (ADD_SERIES_NAME, ADD_SERIES_VIDEOS, ADD_MOVIE_NAME, ADD_MOVIE_VIDEOS,
                   EDIT_SERIES_OLD, EDIT_SERIES_NEW, EDIT_MOVIE_OLD, EDIT_MOVIE_NEW,
                   DELETE_SERIES_NAME, DELETE_MOVIE_NAME, BROADCAST_MESSAGE,
                   BAN_USER_ID, UNBAN_USER_ID, ADD_REC_TITLE, ADD_REC_PHOTO, ADD_REC_DESC, DEL_REC_TITLE)
import logging

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تسجيل الأخطاء وإعلام المطور."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    # يمكن إرسال رسالة للمدير
    if update and update.effective_message:
        await context.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=f"حدث خطأ: {context.error}\n\nتحديث: {update}"
        )

def main():
    db.init_db()

    app = Application.builder().token(config.TOKEN).build()

    # إضافة معالج الأخطاء
    app.add_error_handler(error_handler)

    # ===== معالجات المستخدمين =====
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CallbackQueryHandler(handlers.check_subscription_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(handlers.check_invites_callback, pattern="^check_invites$"))

    # القوائم الرئيسية (ملاحظة: ترتيب المعالجات مهم: الأكثر تحديداً أولاً)
    app.add_handler(CallbackQueryHandler(handlers.show_main_menu, pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(handlers.series_menu, pattern="^menu_series$"))
    app.add_handler(CallbackQueryHandler(handlers.movies_menu, pattern="^menu_movies$"))
    app.add_handler(CallbackQueryHandler(handlers.recommendations_menu, pattern="^menu_recommendations$"))
    app.add_handler(CallbackQueryHandler(handlers.support_menu, pattern="^menu_support$"))
    app.add_handler(CallbackQueryHandler(handlers.search_menu, pattern="^menu_search$"))

    # التنقل في المسلسلات
    app.add_handler(CallbackQueryHandler(handlers.series_pagination, pattern="^(series_next|series_prev)$"))
    app.add_handler(CallbackQueryHandler(handlers.series_select, pattern="^series_.+"))
    app.add_handler(CallbackQueryHandler(handlers.episode_navigation, pattern="^(ep_next|ep_prev)$"))

    # التنقل في الأفلام
    app.add_handler(CallbackQueryHandler(handlers.movies_pagination, pattern="^(movies_next|movies_prev)$"))
    app.add_handler(CallbackQueryHandler(handlers.movie_select, pattern="^movie_.+"))
    app.add_handler(CallbackQueryHandler(handlers.part_navigation, pattern="^(part_next|part_prev)$"))

    # التقييم والإبلاغ
    app.add_handler(CallbackQueryHandler(handlers.rate_callback, pattern="^rate_(series|movie)_\\d+$"))
    app.add_handler(CallbackQueryHandler(handlers.set_rate_callback, pattern="^set_rate_\\d+$"))
    app.add_handler(CallbackQueryHandler(handlers.report_callback, pattern="^report_(series|movie)_\\d+$"))

    # التوصيات
    app.add_handler(CallbackQueryHandler(handlers.rec_navigation, pattern="^(rec_next|rec_prev)$"))

    # أزرار الرجوع العامة (يجب أن يكون بعد جميع الأنماط الأكثر تحديداً)
    app.add_handler(CallbackQueryHandler(handlers.back_callback, pattern="^back_"))

    # ===== معالجات البحث (محادثة) =====
    search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handlers.search_menu, pattern="^menu_search$")],
        states={
            "SEARCH": [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_search)]
        },
        fallbacks=[CommandHandler("cancel", handlers.back_callback)]
    )
    app.add_handler(search_conv)

    # ===== معالجات الإدارة =====
    app.add_handler(CommandHandler("admin", admin.admin_panel))

    # قوائم الإدارة الفرعية
    app.add_handler(CallbackQueryHandler(admin.admin_series_menu, pattern="^admin_series$"))
    app.add_handler(CallbackQueryHandler(admin.admin_movies_menu, pattern="^admin_movies$"))
    app.add_handler(CallbackQueryHandler(admin.admin_users_menu, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin.admin_invite_menu, pattern="^admin_invite$"))
    app.add_handler(CallbackQueryHandler(admin.admin_channels_menu, pattern="^admin_channels$"))
    app.add_handler(CallbackQueryHandler(admin.admin_recommend_menu, pattern="^admin_recommend$"))
    app.add_handler(CallbackQueryHandler(admin.admin_back, pattern="^admin_back$"))

    # أزرار الإدارة الفردية
    app.add_handler(CallbackQueryHandler(admin.toggle_invite, pattern="^admin_toggle_invite$"))
    app.add_handler(CallbackQueryHandler(admin.set_invite_count_start, pattern="^admin_set_invite_count$"))
    app.add_handler(CallbackQueryHandler(admin.set_series_channel_start, pattern="^admin_set_series_ch$"))
    app.add_handler(CallbackQueryHandler(admin.set_movies_channel_start, pattern="^admin_set_movies_ch$"))
    app.add_handler(CallbackQueryHandler(admin.funding_start, pattern="^admin_funding$"))
    app.add_handler(CallbackQueryHandler(admin.broadcast_start, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(admin.ban_start, pattern="^admin_ban$"))
    app.add_handler(CallbackQueryHandler(admin.unban_start, pattern="^admin_unban$"))
    app.add_handler(CallbackQueryHandler(admin.add_rec_start, pattern="^admin_add_rec$"))
    app.add_handler(CallbackQueryHandler(admin.del_rec_start, pattern="^admin_del_rec$"))

    # محادثات الإضافة (ConversationHandlers)
    add_series_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.add_series_start, pattern="^admin_add_series$")],
        states={
            ADD_SERIES_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_series_get_name)],
            ADD_SERIES_VIDEOS: [MessageHandler(filters.VIDEO, admin.add_series_video),
                                CommandHandler("done", admin.add_series_done)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(add_series_conv)

    add_movie_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.add_movie_start, pattern="^admin_add_movie$")],
        states={
            ADD_MOVIE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_movie_get_name)],
            ADD_MOVIE_VIDEOS: [MessageHandler(filters.VIDEO, admin.add_movie_video),
                               CommandHandler("done", admin.add_movie_done)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(add_movie_conv)

    edit_series_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.edit_series_start, pattern="^admin_edit_series$")],
        states={
            EDIT_SERIES_OLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.edit_series_get_old)],
            EDIT_SERIES_NEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.edit_series_get_new)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(edit_series_conv)

    del_series_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.delete_series_start, pattern="^admin_del_series$")],
        states={
            DELETE_SERIES_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.delete_series_confirm)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(del_series_conv)

    edit_movie_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.edit_movie_start, pattern="^admin_edit_movie$")],
        states={
            EDIT_MOVIE_OLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.edit_movie_get_old)],
            EDIT_MOVIE_NEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.edit_movie_get_new)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(edit_movie_conv)

    del_movie_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.delete_movie_start, pattern="^admin_del_movie$")],
        states={
            DELETE_MOVIE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.delete_movie_confirm)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(del_movie_conv)

    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.broadcast_start, pattern="^admin_broadcast$")],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.ALL, admin.broadcast_send)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(broadcast_conv)

    ban_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.ban_start, pattern="^admin_ban$")],
        states={
            BAN_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.ban_user)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(ban_conv)

    unban_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.unban_start, pattern="^admin_unban$")],
        states={
            UNBAN_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.unban_user)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(unban_conv)

    set_invite_count_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.set_invite_count_start, pattern="^admin_set_invite_count$")],
        states={
            17: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.set_invite_count)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(set_invite_count_conv)

    set_series_ch_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.set_series_channel_start, pattern="^admin_set_series_ch$")],
        states={
            18: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.set_series_channel)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(set_series_ch_conv)

    set_movies_ch_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.set_movies_channel_start, pattern="^admin_set_movies_ch$")],
        states={
            19: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.set_movies_channel)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(set_movies_ch_conv)

    funding_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.funding_start, pattern="^admin_funding$")],
        states={
            20: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.funding_get_channel)],
            21: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.funding_get_count)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(funding_conv)

    add_rec_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.add_rec_start, pattern="^admin_add_rec$")],
        states={
            ADD_REC_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_rec_get_title)],
            ADD_REC_PHOTO: [MessageHandler(filters.PHOTO, admin.add_rec_get_photo)],
            ADD_REC_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_rec_get_desc)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(add_rec_conv)

    del_rec_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.del_rec_start, pattern="^admin_del_rec$")],
        states={
            DEL_REC_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.del_rec_confirm)]
        },
        fallbacks=[CommandHandler("cancel", admin.cancel)]
    )
    app.add_handler(del_rec_conv)

    print("✅ البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main() 
