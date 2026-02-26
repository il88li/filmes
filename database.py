import sqlite3
import threading
from config import DB_NAME

lock = threading.Lock()

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    with lock:
        conn = get_connection()
        c = conn.cursor()

        # المستخدمين
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            is_banned INTEGER DEFAULT 0,
            invite_link_used TEXT,
            invites_count INTEGER DEFAULT 0,
            invited_users TEXT,  -- قائمة ids مفصولة بفواصل
            can_use_bot INTEGER DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # المسلسلات
        c.execute('''CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            total_episodes INTEGER DEFAULT 0,
            channel_message_ids TEXT  -- اختياري: لتخزين message_ids لكل الحلقات (json)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id INTEGER,
            episode_number INTEGER,
            file_id TEXT,
            message_id INTEGER,
            FOREIGN KEY(series_id) REFERENCES series(id) ON DELETE CASCADE
        )''')

        # الأفلام (يمكن أن تكون بأجزاء)
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
            FOREIGN KEY(movie_id) REFERENCES movies(id) ON DELETE CASCADE
        )''')

        # التقييمات
        c.execute('''CREATE TABLE IF NOT EXISTS ratings (
            user_id INTEGER,
            content_type TEXT,  -- 'series' or 'movie'
            content_id INTEGER,
            rating INTEGER CHECK(rating BETWEEN 1 AND 10),
            PRIMARY KEY(user_id, content_type, content_id)
        )''')

        # البلاغات
        c.execute('''CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content_type TEXT,
            content_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # التوصيات
        c.execute('''CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content_type TEXT,
            content_id INTEGER,
            photo_file_id TEXT,
            description TEXT
        )''')

        # إعدادات القنوات
        c.execute('''CREATE TABLE IF NOT EXISTS channels (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        # key: 'series_channel', 'movies_channel'

        # قناة التمويل المؤقتة
        c.execute('''CREATE TABLE IF NOT EXISTS funding_channel (
            chat_id TEXT PRIMARY KEY,
            required_members INTEGER,
            current_members TEXT  -- قائمة ids الأعضاء الذين تم احتسابهم
        )''')

        # إعدادات الدعوة
        c.execute('''CREATE TABLE IF NOT EXISTS invite_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        c.execute("INSERT OR IGNORE INTO invite_settings (key, value) VALUES (?, ?)", ('enabled', 'true'))
        c.execute("INSERT OR IGNORE INTO invite_settings (key, value) VALUES (?, ?)", ('required_count', '5'))

        conn.commit()
        conn.close()

# ================== دوال المستخدمين ==================
def add_user(user_id, username, first_name, invite_link_used=None):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT OR IGNORE INTO users 
                     (user_id, username, first_name, invite_link_used) 
                     VALUES (?, ?, ?, ?)''',
                  (user_id, username, first_name, invite_link_used))
        if c.rowcount == 0:
            # تحديث الاسم إذا كان موجوداً
            c.execute('''UPDATE users SET username = ?, first_name = ? 
                         WHERE user_id = ?''', (username, first_name, user_id))
        conn.commit()
        conn.close()

def get_user(user_id):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        conn.close()
        return user

def set_user_banned(user_id, banned):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if banned else 0, user_id))
        conn.commit()
        conn.close()

def set_user_can_use(user_id, can_use):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET can_use_bot = ? WHERE user_id = ?", (1 if can_use else 0, user_id))
        conn.commit()
        conn.close()

def update_user_invites(inviter_id, invited_user_id):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        # احصل على الداعي
        c.execute("SELECT invites_count, invited_users FROM users WHERE user_id = ?", (inviter_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return False
        invites_count, invited_users_str = row
        invited_list = invited_users_str.split(',') if invited_users_str else []
        if str(invited_user_id) in invited_list:
            conn.close()
            return False  # تمت دعوته سابقاً
        # أضف المدعو
        invited_list.append(str(invited_user_id))
        new_invited = ','.join(invited_list)
        new_count = invites_count + 1
        required = int(get_invite_setting('required_count') or 5)
        can_use = 1 if new_count >= required else 0
        c.execute('''UPDATE users SET invites_count = ?, invited_users = ?, can_use_bot = ?
                     WHERE user_id = ?''', (new_count, new_invited, can_use, inviter_id))
        conn.commit()
        conn.close()
        return True

def get_all_users():
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        users = [row[0] for row in c.fetchall()]
        conn.close()
        return users

# ================== دوال المسلسلات ==================
def add_series(name):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO series (name) VALUES (?)", (name,))
        if c.rowcount == 0:
            conn.close()
            return None  # موجود بالفعل
        conn.commit()
        c.execute("SELECT id FROM series WHERE name = ?", (name,))
        series_id = c.fetchone()[0]
        conn.close()
        return series_id

def get_series_by_name(name):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM series WHERE name = ?", (name,))
        series = c.fetchone()
        conn.close()
        return series

def get_all_series_names():
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM series ORDER BY name")
        names = [row[0] for row in c.fetchall()]
        conn.close()
        return names

def update_series_name(old_name, new_name):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE series SET name = ? WHERE name = ?", (new_name, old_name))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return affected > 0

def delete_series(name):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM series WHERE name = ?", (name,))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return affected > 0

def add_episode(series_id, episode_number, file_id, message_id):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO episodes (series_id, episode_number, file_id, message_id)
                     VALUES (?, ?, ?, ?)''', (series_id, episode_number, file_id, message_id))
        conn.commit()
        # تحديث total_episodes
        c.execute("UPDATE series SET total_episodes = ? WHERE id = ?", (episode_number, series_id))
        conn.commit()
        conn.close()

def get_episodes(series_id):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''SELECT episode_number, file_id, message_id FROM episodes 
                     WHERE series_id = ? ORDER BY episode_number''', (series_id,))
        episodes = c.fetchall()
        conn.close()
        return episodes

# ================== دوال الأفلام ==================
def add_movie(name):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO movies (name) VALUES (?)", (name,))
        if c.rowcount == 0:
            conn.close()
            return None
        conn.commit()
        c.execute("SELECT id FROM movies WHERE name = ?", (name,))
        movie_id = c.fetchone()[0]
        conn.close()
        return movie_id

def get_movie_by_name(name):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM movies WHERE name = ?", (name,))
        movie = c.fetchone()
        conn.close()
        return movie

def get_all_movies_names():
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM movies ORDER BY name")
        names = [row[0] for row in c.fetchall()]
        conn.close()
        return names

def update_movie_name(old_name, new_name):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE movies SET name = ? WHERE name = ?", (new_name, old_name))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return affected > 0

def delete_movie(name):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM movies WHERE name = ?", (name,))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return affected > 0

def add_movie_part(movie_id, part_number, file_id, message_id):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO movie_parts (movie_id, part_number, file_id, message_id)
                     VALUES (?, ?, ?, ?)''', (movie_id, part_number, file_id, message_id))
        conn.commit()
        c.execute("UPDATE movies SET parts_count = ? WHERE id = ?", (part_number, movie_id))
        conn.commit()
        conn.close()

def get_movie_parts(movie_id):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''SELECT part_number, file_id, message_id FROM movie_parts 
                     WHERE movie_id = ? ORDER BY part_number''', (movie_id,))
        parts = c.fetchall()
        conn.close()
        return parts

# ================== دوال التقييمات ==================
def add_rating(user_id, content_type, content_id, rating):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO ratings (user_id, content_type, content_id, rating)
                     VALUES (?, ?, ?, ?)''', (user_id, content_type, content_id, rating))
        conn.commit()
        conn.close()

def get_average_rating(content_type, content_id):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''SELECT AVG(rating) FROM ratings 
                     WHERE content_type = ? AND content_id = ?''', (content_type, content_id))
        avg = c.fetchone()[0]
        conn.close()
        return avg if avg else 0

def get_user_rating(user_id, content_type, content_id):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''SELECT rating FROM ratings 
                     WHERE user_id = ? AND content_type = ? AND content_id = ?''',
                  (user_id, content_type, content_id))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

# ================== دوال البلاغات ==================
def add_report(user_id, content_type, content_id):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO reports (user_id, content_type, content_id)
                     VALUES (?, ?, ?)''', (user_id, content_type, content_id))
        conn.commit()
        conn.close()

# ================== دوال التوصيات ==================
def add_recommendation(title, content_type, content_id, photo_file_id, description):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO recommendations (title, content_type, content_id, photo_file_id, description)
                     VALUES (?, ?, ?, ?, ?)''', (title, content_type, content_id, photo_file_id, description))
        conn.commit()
        conn.close()

def delete_recommendation(title):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM recommendations WHERE title = ?", (title,))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return affected > 0

def get_all_recommendations():
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT title, content_type, content_id, photo_file_id, description FROM recommendations")
        recs = c.fetchall()
        conn.close()
        return recs

# ================== دوال القنوات ==================
def set_channel(key, value):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO channels (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()

def get_channel(key):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT value FROM channels WHERE key = ?", (key,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

# ================== دوال قناة التمويل ==================
def set_funding_channel(chat_id, required_members):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO funding_channel (chat_id, required_members, current_members) VALUES (?, ?, ?)",
                  (chat_id, required_members, ''))
        conn.commit()
        conn.close()

def get_funding_channel():
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT chat_id, required_members, current_members FROM funding_channel")
        row = c.fetchone()
        conn.close()
        return row  # (chat_id, required, current_list_str) or None

def update_funding_member(chat_id, user_id):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT current_members FROM funding_channel WHERE chat_id = ?", (chat_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return False
        current = row[0]
        members = current.split(',') if current else []
        if str(user_id) in members:
            conn.close()
            return False  # موجود مسبقاً
        members.append(str(user_id))
        new_current = ','.join(members)
        c.execute("UPDATE funding_channel SET current_members = ? WHERE chat_id = ?", (new_current, chat_id))
        conn.commit()
        # تحقق إذا وصل العدد المطلوب
        c.execute("SELECT required_members FROM funding_channel WHERE chat_id = ?", (chat_id,))
        required = c.fetchone()[0]
        conn.close()
        return len(members) >= required

def delete_funding_channel():
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM funding_channel")
        conn.commit()
        conn.close()

# ================== دوال إعدادات الدعوة ==================
def get_invite_setting(key):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT value FROM invite_settings WHERE key = ?", (key,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

def set_invite_setting(key, value):
    with lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO invite_settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close() 
