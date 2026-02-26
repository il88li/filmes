# database.py
import sqlite3
import threading
from datetime import datetime
from config import DATABASE_FILE, ADMIN_ID

lock = threading.Lock()

def get_db_connection():
    """الحصول على اتصال بقاعدة البيانات"""
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """تهيئة قاعدة البيانات وجميع الجداول"""
    with lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جدول المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_date TEXT,
                is_banned INTEGER DEFAULT 0,
                invited_by INTEGER,
                invites_count INTEGER DEFAULT 0,
                can_use_bot INTEGER DEFAULT 0,
                invited_users TEXT DEFAULT '',
                FOREIGN KEY (invited_by) REFERENCES users(user_id)
            )
        ''')
        
        # جدول إعدادات نظام الدعوة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invite_system (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled INTEGER DEFAULT 1,
                required_invites INTEGER DEFAULT 5
            )
        `
