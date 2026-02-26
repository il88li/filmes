import os
from pathlib import Path

# توكن البوت من متغيرات البيئة (طريقة آمنة)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# قائمة بأيدي القنوات التي سيتم النشر فيها (يمكنك إضافة المزيد)
# للحصول على أيدي القنوات، يمكنك استخدام بوت @getidsbot
CHANNELS_IDS = [
    -1001234567890,  # استبدل هذا بمعرف قناتك الأولى
    -1001234567891,  # استبدل هذا بمعرف قناتك الثانية
]

# مسار ملف قاعدة البيانات
DB_PATH = Path("series_data.json")

# مسار ملف persistence الخاص بالمكتبة (لحفظ بيانات المستخدمين والمحادثات)
PERSISTENCE_PATH = Path("bot_persistence.pkl")
