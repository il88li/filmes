import database as db
from telegram import Update
from telegram.ext import ContextTypes

async def handle_new_user(user_id, inviter_id):
    """معالجة مستخدم جديد جاء عبر رابط دعوة."""
    # يتم استدعاؤها بعد اشتراكه في القناة
    if inviter_id and inviter_id != user_id:
        # تحقق من أن الداعي غير محظور الخ
        inviter = db.get_user(inviter_id)
        if inviter and inviter[3] == 0:  # غير محظور
            db.update_user_invites(inviter_id, user_id)
            # إرسال إشعار للمدير
            # (يتم في مكان آخر)
            return True
    return False

async def handle_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # معالج الرابط (يتم في start)
    pass
