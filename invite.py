from database import load_data, save_data
from config import ADMIN_ID, CHANNEL_USERNAME
import telebot

def check_subscription(bot, user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def notify_admin_join(bot, user_id, username):
    bot.send_message(ADMIN_ID, f"عضو جديد اشترك: [{username}](tg://user?id={user_id})", parse_mode='Markdown')

def handle_referral(users, invites, referrer_id, user_id, username, bot):
    if referrer_id != user_id and referrer_id in users:
        if referrer_id not in invites:
            invites[referrer_id] = {'invited': [], 'needed': 5}
        if user_id not in invites[referrer_id]['invited']:
            invites[referrer_id]['invited'].append(user_id)
            users[referrer_id]['invites_done'] = users[referrer_id].get('invites_done', 0) + 1
            save_data('users', users)
            save_data('invites', invites)
            notify_admin_join(bot, user_id, username)
            if users[referrer_id]['invites_done'] >= users[referrer_id]['invites_needed']:
                bot.send_message(referrer_id, "مبروك! تم تفعيل البوت.")
