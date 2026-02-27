# database.py
import sqlite3
from datetime import datetime
from config import DB_FILE

def init_db():
    """إنشاء قاعدة البيانات و الجداول"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, 
                  joined_date TEXT, invite_count INTEGER DEFAULT 0, banned INTEGER DEFAULT 0)''')
    
    # Content table
    c.execute('''CREATE TABLE IF NOT EXISTS content 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, name TEXT, 
                  parts TEXT, channel_id TEXT, unique_id TEXT, added_by INTEGER, 
                  added_date TEXT)''')
    
    # Stats table
    c.execute('''CREATE TABLE IF NOT EXISTS stats 
                 (uploader_id INTEGER, uploads INTEGER DEFAULT 0, PRIMARY KEY(uploader_id))''')
    
    # Settings table
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', '0')")
    
    conn.commit()
    conn.close()

def get_maintenance_status():
    """جلب حالة الصيانة"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='maintenance'")
    result = c.fetchone()
    conn.close()
    return result[0] == '1' if result else False

def set_maintenance_status(status):
    """تغيير حالة الصيانة"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('maintenance', ?)", (str(int(status)),))
    conn.commit()
    conn.close()
    return status

def is_user_banned(user_id):
    """التحقق من حظر المستخدم"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 1

def register_user(user_id, username, first_name):
    """تسجيل مستخدم جديد"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date) VALUES (?, ?, ?, ?)",
             (user_id, username, first_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def ban_user(user_id):
    """حظر مستخدم"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET banned=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    """رفع حظر عن مستخدم"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET banned=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_stats():
    """جلب الإحصائيات"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE banned=0")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM content")
    videos = c.fetchone()[0]
    c.execute('''SELECT u.first_name, s.uploads FROM stats s 
                 JOIN users u ON s.uploader_id = u.user_id 
                 ORDER BY s.uploads DESC LIMIT 1''')
    top_uploader = c.fetchone()
    top_name = top_uploader[0] if top_uploader else "لا يوجد"
    top_uploads = top_uploader[1] if top_uploader else 0
    conn.close()
    
    return f"""📊 **إحصائيات البوت**

👥 عدد المستخدمين: {users}
🎥 عدد الفيديوهات: {videos}
🏆 الأكثر مساهمة: {top_name} ({top_uploads} فيديو)"""

# Initialize database
init_db() 
