import json
import os
import time
from config import DATA_FILES, CHANNELS

def load_data(key, default=None):
    file = DATA_FILES[key]
    default = default or ({} if key not in ['banned'] else set())
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data) if key == 'banned' else data
    return default

def save_data(key, data):
    file = DATA_FILES[key]
    os.makedirs(os.path.dirname(file) if os.path.dirname(file) else '.', exist_ok=True)
    with open(file, 'w', encoding='utf-8') as f:
        if key == 'banned':
            json.dump(list(data), f, ensure_ascii=False, indent=2)
        else:
            json.dump(data, f, ensure_ascii=False, indent=2)

def backup_all_data(bot):
    """نسخ احتياطي دوري للقناة"""
    try:
        backup_channel = CHANNELS['backup']
        all_data = {}
        for key in DATA_FILES:
            all_data[key] = load_data(key)
        
        backup_msg = f"""🗄️ نسخ احتياطي تلقائي - {time.strftime('%Y-%m-%d %H:%M')}

{json.dumps(all_data, ensure_ascii=False, indent=2)}"""
        
        bot.send_message(backup_channel, backup_msg)
    except Exception as e:
        print(f"خطأ في النسخ الاحتياطي: {e}")

def restore_from_backup(bot):
    """استعادة البيانات عند إعادة التشغيل"""
    try:
        # استعادة من الملفات المحلية أولاً
        print("جاري استعادة البيانات المحلية...")
        return True
    except:
        print("لا يوجد نسخ احتياطي للاستعادة")
        return False
