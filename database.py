import sqlite3
import threading
from config import DB_NAME

# تأمين للكتابة متعددة الخيوط (اختياري)
lock = threading.Lock()

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    with lock:
        conn = get_connection()
        c = conn.cursor()
        # جدول المستخدمين
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            is_banned INTEGER DEFAULT 0,
            invite_link_used TEXT,  -- الرابط الذي استخدمه للتسجيل (إن وجد)
            invites_count INTEGER DEFAULT 0,  -- عدد المدعوين الذين اشتركوا
            invited_users TEXT,  -- قائمة ids المدعوين (مفصولة بفواصل)
            can_use_bot INTEGER DEFAULT 0,  -- 1 إذا كان يستطيع استخدام البوت (بعد الدعوات)
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # جدول المسلسلات
        c.execute('''CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            total_episodes INTEGER DEFAULT 0
        )''')
        # جدول حلقات المسلسلات
        c.execute('''CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id INTEGER,
            episode_number INTEGER,
            file_id TEXT,
            message_id INTEGER,  -- message_id في قناة المسلسلات
            FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE
        )''')
        # جدول الأفلام (يمكن التعامل معها كمسلسل بحلقة واحدة أو عدة أجزاء)
        c.execute('''CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            parts_count INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS movie_parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER,
            part_number INTEGER,
            file_id TEXT,
            message_id INTEGER,
            FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
        )''')
        # جدول التقييمات
        c.execute('''CREATE TABLE IF NOT EXISTS ratings (
            user_id INTEGER,
            content_type TEXT,  -- 'series' or 'movie'
            content_id INTEGER,
            rating INTEGER,  -- 1-10
            PRIMARY KEY (user_id, content_type, content_id)
        )''')
        # جدول البلاغات
        c.execute('''CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content_type TEXT,
            content_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # جدول التوصيات
        c.execute('''CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,  -- اسم المسلسل أو الفلم
            content_type TEXT,  -- 'series' or 'movie'
            content_id INTEGER,
            photo_file_id TEXT,
            description TEXT
        )''')
        # جدول إعدادات القنوات
        c.execute('''CREATE TABLE IF NOT EXISTS channels (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        # جدول قناة التمويل (المؤقتة)
        c.execute('''CREATE TABLE IF NOT EXISTS funding_channel (
            chat_id TEXT,
            required_members INTEGER,
            current_members TEXT  -- قائمة ids الأعضاء الذين تم احتسابهم
        )''')
        # جدول إعدادات الدعوة
        c.execute('''CREATE TABLE IF NOT EXISTS invite_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        # إدخال القيم الافتراضية لإعدادات الدعوة
        c.execute("INSERT OR IGNORE INTO invite_settings (key, value) VALUES (?, ?)", ('enabled', 'true'))
        c.execute("INSERT OR IGNORE INTO invite_settings (key, value) VALUES (?, ?)", ('required_count', '5'))
        conn.commit()
        conn.close()

init_db()

# دوال مساعدة
def execute_query(query, params=(), fetchone=False, fetchall=False):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute(query, params)
        if fetchone:
            result = c.fetchone()
        elif fetchall:
            result = c.fetchall()
        else:
            result = None
        conn.commit()
        conn.close()
        return result

def add_user(user_id, username, first_name, invite_link_used=None):
    # إضافة مستخدم جديد إذا لم يكن موجوداً
    user = get_user(user_id)
    if not user:
        execute_query(
            "INSERT INTO users (user_id, username, first_name, invite_link_used) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, invite_link_used)
        )
    else:
        # تحديث البيانات
        execute_query(
            "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
            (username, first_name, user_id)
        )

def get_user(user_id):
    return execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)

def update_user_invites(user_id, invited_user_id):
    # تحديث عدد دعوات المستخدم وإضافة المدعو إلى قائمته
    user = get_user(user_id)
    if user:
        invited_list = user[6] or ''  # invited_users في العمود 6 حسب الترتيب
        invited_ids = invited_list.split(',') if invited_list else []
        if str(invited_user_id) not in invited_ids:
            invited_ids.append(str(invited_user_id))
            new_list = ','.join(invited_ids)
            new_count = user[5] + 1  # invites_count في العمود 5
            required = int(get_invite_setting('required_count') or 5)
            can_use = 1 if new_count >= required else 0
            execute_query(
                "UPDATE users SET invites_count = ?, invited_users = ?, can_use_bot = ? WHERE user_id = ?",
                (new_count, new_list, can_use, user_id)
            )
            return True
    return False

def set_user_can_use(user_id, can_use):
    execute_query("UPDATE users SET can_use_bot = ? WHERE user_id = ?", (1 if can_use else 0, user_id))

def get_invite_setting(key):
    result = execute_query("SELECT value FROM invite_settings WHERE key = ?", (key,), fetchone=True)
    return result[0] if result else None

def set_invite_setting(key, value):
    execute_query("INSERT OR REPLACE INTO invite_settings (key, value) VALUES (?, ?)", (key, value))

# دوال أخرى مماثلة للمسلسلات والأفلام والتقييمات إلخ...
# (سأضيف البعض منها لاحقاً) 
