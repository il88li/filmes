#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3, os, uuid
from datetime import datetime
from config import DB_FILE

def init_db():
    """قاعدة بيانات نظيفة بدون بيانات تجريبية"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    # المستخدمين
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, 
                  joined_date TEXT, banned INTEGER DEFAULT 0)''')
    
    # المحتوى (جدول فارغ)
    c.execute('''CREATE TABLE IF NOT EXISTS content 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, name TEXT, 
                  parts INTEGER, total_parts INTEGER, channel_message_ids TEXT, 
                  unique_id TEXT, added_by INTEGER, added_date TEXT)''')
    
    # الطلبات
    c.execute('''CREATE TABLE IF NOT EXISTS requests 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                  user_name TEXT, movie_name TEXT, request_date TEXT)''')
    
    # الإعدادات
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute("INSERT OR IGNORE INTO settings (key,value) VALUES('maintenance','0')")
    
    conn.commit()
    conn.close()
    print("✅ قاعدة بيانات نظيفة جاهزة")

def search_content(query):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM content WHERE name LIKE ? LIMIT 10", (f'%{query}%',))
    results = c.fetchall()
    conn.close()
    return results

def add_request(user_id, user_name, movie_name):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO requests (user_id, user_name, movie_name, request_date) VALUES(?,?,?,?)",
             (user_id, user_name, movie_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def add_content(type_, name, parts, total_parts, channel_message_ids, added_by):
    """إضافة محتوى جديد"""
    unique_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("""INSERT INTO content (type, name, parts, total_parts, channel_message_ids, 
                 unique_id, added_by, added_date) VALUES(?,?,?,?,?,?,?,?)""",
             (type_, name, parts, total_parts, channel_message_ids, unique_id, added_by, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return unique_id

def get_maintenance_status():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='maintenance'")
    result = c.fetchone()
    conn.close()
    return result and result[0] == '1'

def set_maintenance_status(status):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES('maintenance', ?)", (str(int(status)),))
    conn.commit()
    conn.close()

def register_user(user_id, username=None, first_name=None):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date) VALUES(?,?,?,?)",
             (user_id, username, first_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def is_user_banned(user_id):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 1

init_db()
print("📭 قاعدة البيانات فارغة - جاهزة لإضافة المحتوى الحقيقي!")
