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

        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            is_banned INTEGER DEFAULT 0,
            invite_link_used TEXT,
            invites_count INTEGER DEFAULT 0,
            invited_users TEXT,
            can_use_bot INTEGER DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            total_episodes INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id INTEGER,
            episode_number INTEGER,
            file_id TEXT,
            message_id INTEGER,
            FOREIGN KEY(series_id) REFERENCES series(id) ON DELETE CASCADE
        )''')

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

        c.execute('''CREATE TABLE IF NOT EXISTS ratings (
            user_id INTEGER,
            content_type TEXT,
            content_id INTEGER,
            rating INTEGER CHECK(rating BETWEEN 1 AND 10),
            PRIMARY KEY(user_id, content_type, content_id)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content_type TEXT,
            content_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content_type TEXT,
            content_id INTEGER,
            photo_file_id TEXT,
            description TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS channels (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS funding_channel (
            chat_id TEXT PRIMARY KEY,
            required_members INTEGER,
            current_members TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS invite_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        c.execute("INSERT OR IGNORE INTO invite_settings (key, value) VALUES ('enabled', 'true')")
        c.execute("INSERT OR IGNORE INTO invite_settings (key, value) VALUES ('required_count', '5')")

        conn.commit()
        conn.close()

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

# ===== دوال المستخدمين =====
def add_user(user_id, username, first_name, invite_link_used=None):
    user = get_user(user_id)
    if not user:
        execute_query(
            "INSERT INTO users (user_id, username, first_name, invite_link_used) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, invite_link_used)
        )
    else:
        execute_query(
            "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
            (username, first_name, user_id)
        )

def get_user(user_id):
    return execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)

def set_user_banned(user_id, banned):
    execute_query("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if banned else 0, user_id))

def set_user_can_use(user_id, can_use):
    execute_query("UPDATE users SET can_use_bot = ? WHERE user_id = ?", (1 if can_use else 0, user_id))

def update_user_invites(inviter_id, invited_user_id):
    inviter = get_user(inviter_id)
    if not inviter:
        return False
    invited_list = inviter[6].split(',') if inviter[6] else []
    if str(invited_user_id) in invited_list:
        return False
    invited_list.append(str(invited_user_id))
    new_invited = ','.join(invited_list)
    new_count = inviter[5] + 1
    required = int(get_invite_setting('required_count') or 5)
    can_use = 1 if new_count >= required else 0
    execute_query(
        "UPDATE users SET invites_count = ?, invited_users = ?, can_use_bot = ? WHERE user_id = ?",
        (new_count, new_invited, can_use, inviter_id)
    )
    return True

def get_all_users():
    rows = execute_query("SELECT user_id FROM users", fetchall=True)
    return [row[0] for row in rows] if rows else []

# ===== دوال المسلسلات =====
def add_series(name):
    try:
        execute_query("INSERT INTO series (name) VALUES (?)", (name,))
        return execute_query("SELECT id FROM series WHERE name = ?", (name,), fetchone=True)[0]
    except:
        return None

def get_series_by_name(name):
    return execute_query("SELECT * FROM series WHERE name = ?", (name,), fetchone=True)

def get_series_by_id(series_id):
    return execute_query("SELECT * FROM series WHERE id = ?", (series_id,), fetchone=True)

def get_all_series_names():
    rows = execute_query("SELECT name FROM series ORDER BY name", fetchall=True)
    return [row[0] for row in rows] if rows else []

def get_all_series():
    return execute_query("SELECT id, name FROM series ORDER BY name", fetchall=True) or []

def update_series_name(old_name, new_name):
    execute_query("UPDATE series SET name = ? WHERE name = ?", (new_name, old_name))
    return True

def delete_series(name):
    execute_query("DELETE FROM series WHERE name = ?", (name,))
    return True

def add_episode(series_id, episode_number, file_id, message_id):
    execute_query(
        "INSERT INTO episodes (series_id, episode_number, file_id, message_id) VALUES (?, ?, ?, ?)",
        (series_id, episode_number, file_id, message_id)
    )
    execute_query("UPDATE series SET total_episodes = ? WHERE id = ?", (episode_number, series_id))

def get_episodes(series_id):
    return execute_query(
        "SELECT episode_number, file_id, message_id FROM episodes WHERE series_id = ? ORDER BY episode_number",
        (series_id,), fetchall=True
    ) or []

# ===== دوال الأفلام =====
def add_movie(name):
    try:
        execute_query("INSERT INTO movies (name) VALUES (?)", (name,))
        return execute_query("SELECT id FROM movies WHERE name = ?", (name,), fetchone=True)[0]
    except:
        return None

def get_movie_by_name(name):
    return execute_query("SELECT * FROM movies WHERE name = ?", (name,), fetchone=True)

def get_movie_by_id(movie_id):
    return execute_query("SELECT * FROM movies WHERE id = ?", (movie_id,), fetchone=True)

def get_all_movies_names():
    rows = execute_query("SELECT name FROM movies ORDER BY name", fetchall=True)
    return [row[0] for row in rows] if rows else []

def get_all_movies():
    return execute_query("SELECT id, name FROM movies ORDER BY name", fetchall=True) or []

def update_movie_name(old_name, new_name):
    execute_query("UPDATE movies SET name = ? WHERE name = ?", (new_name, old_name))
    return True

def delete_movie(name):
    execute_query("DELETE FROM movies WHERE name = ?", (name,))
    return True

def add_movie_part(movie_id, part_number, file_id, message_id):
    execute_query(
        "INSERT INTO movie_parts (movie_id, part_number, file_id, message_id) VALUES (?, ?, ?, ?)",
        (movie_id, part_number, file_id, message_id)
    )
    execute_query("UPDATE movies SET parts_count = ? WHERE id = ?", (part_number, movie_id))

def get_movie_parts(movie_id):
    return execute_query(
        "SELECT part_number, file_id, message_id FROM movie_parts WHERE movie_id = ? ORDER BY part_number",
        (movie_id,), fetchall=True
    ) or []

# ===== دوال التقييم =====
def add_rating(user_id, content_type, content_id, rating):
    execute_query(
        "INSERT OR REPLACE INTO ratings (user_id, content_type, content_id, rating) VALUES (?, ?, ?, ?)",
        (user_id, content_type, content_id, rating)
    )

def get_average_rating(content_type, content_id):
    row = execute_query(
        "SELECT AVG(rating) FROM ratings WHERE content_type = ? AND content_id = ?",
        (content_type, content_id), fetchone=True
    )
    return row[0] if row and row[0] else 0

# ===== دوال البلاغات =====
def add_report(user_id, content_type, content_id):
    execute_query(
        "INSERT INTO reports (user_id, content_type, content_id) VALUES (?, ?, ?)",
        (user_id, content_type, content_id)
    )

# ===== دوال التوصيات =====
def add_recommendation(title, content_type, content_id, photo_file_id, description):
    execute_query(
        "INSERT INTO recommendations (title, content_type, content_id, photo_file_id, description) VALUES (?, ?, ?, ?, ?)",
        (title, content_type, content_id, photo_file_id, description)
    )

def delete_recommendation(title):
    execute_query("DELETE FROM recommendations WHERE title = ?", (title,))

def get_all_recommendations():
    return execute_query(
        "SELECT title, content_type, content_id, photo_file_id, description FROM recommendations",
        fetchall=True
    ) or []

# ===== دوال القنوات =====
def set_channel(key, value):
    execute_query("INSERT OR REPLACE INTO channels (key, value) VALUES (?, ?)", (key, value))

def get_channel(key):
    row = execute_query("SELECT value FROM channels WHERE key = ?", (key,), fetchone=True)
    return row[0] if row else None

def set_recommendations_channel(chat_id):
    set_channel('recommendations_channel', chat_id)

def get_recommendations_channel():
    return get_channel('recommendations_channel')

# ===== دوال قناة التمويل =====
def set_funding_channel(chat_id, required_members):
    execute_query(
        "INSERT OR REPLACE INTO funding_channel (chat_id, required_members, current_members) VALUES (?, ?, ?)",
        (chat_id, required_members, '')
    )

def get_funding_channel():
    return execute_query("SELECT chat_id, required_members, current_members FROM funding_channel", fetchone=True)

def update_funding_member(chat_id, user_id):
    row = execute_query("SELECT current_members FROM funding_channel WHERE chat_id = ?", (chat_id,), fetchone=True)
    if not row:
        return False
    current = row[0]
    members = current.split(',') if current else []
    if str(user_id) in members:
        return False
    members.append(str(user_id))
    new_current = ','.join(members)
    execute_query("UPDATE funding_channel SET current_members = ? WHERE chat_id = ?", (new_current, chat_id))
    required = execute_query("SELECT required_members FROM funding_channel WHERE chat_id = ?", (chat_id,), fetchone=True)[0]
    return len(members) >= required

def delete_funding_channel():
    execute_query("DELETE FROM funding_channel")

# ===== دوال إعدادات الدعوة =====
def get_invite_setting(key):
    row = execute_query("SELECT value FROM invite_settings WHERE key = ?", (key,), fetchone=True)
    return row[0] if row else None

def set_invite_setting(key, value):
    execute_query("INSERT OR REPLACE INTO invite_settings (key, value) VALUES (?, ?)", (key, value)) 
