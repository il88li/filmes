# ================================================================
# app.py - خادم Flask لإدارة الموقع بالكامل
# ================================================================

import os
import json
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

# ================================================================
# 1. إعدادات البيانات ومسار الملف
# ================================================================
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'site_data.json')

# البيانات الافتراضية عند أول تشغيل
DEFAULT_DATA = {
    "siteName": "موقعي الإبداعي",
    "heroTitle": "مرحباً، أنا",
    "heroHighlight": "المطور",
    "heroSubtitle": "أبني تجارب رقمية استثنائية تجمع بين الجمال والأداء.",
    "bioText": "مطور واجهات مستخدم بخبرة 5 سنوات، شغوف بتصميم الأنظمة التفاعلية وحل المشكلات التقنية المعقدة.",
    "ctaText": "تواصل معي",
    "ctaLink": "#",
    "footerText": "© 2026 جميع الحقوق محفوظة.",
    "primaryColor": "#2563eb",
    "secondaryColor": "#f59e0b",
    "services": [
        {"name": "تصميم واجهات UX/UI", "desc": "تصميم تجارب مستخدم سلسة وجذابة بناءً على أحدث المعايير."},
        {"name": "تطوير الواجهات الأمامية", "desc": "تحويل التصاميم إلى كود نظيف باستخدام React و CSS الحديث."},
        {"name": "تحسين الأداء و SEO", "desc": "رفع سرعة الموقع وتحسين ظهوره في محركات البحث."}
    ],
    "projects": [
        {"name": "منصة التعلم الذكي", "desc": "منصة تفاعلية للتعليم عن بعد تضم مئات الدروس.", "img": ""},
        {"name": "تطبيق إدارة المهام", "desc": "تطبيق ويب متكامل لإدارة المشاريع والفرق.", "img": ""},
        {"name": "موقع المتجر الإلكتروني", "desc": "متجر متكامل مع نظام دفع وإدارة مخزون.", "img": ""}
    ],
    "social": [
        {"name": "تويتر", "url": "https://twitter.com"},
        {"name": "لينكدإن", "url": "https://linkedin.com"},
        {"name": "جيثب", "url": "https://github.com"}
    ]
}


def load_data():
    """تحميل البيانات من ملف JSON، وإنشاء الملف بالبيانات الافتراضية إذا لم يكن موجوداً."""
    if not os.path.exists(DATA_FILE):
        # إنشاء مجلد data إذا لم يكن موجوداً
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        save_data(DEFAULT_DATA)
        return DEFAULT_DATA.copy()
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        # في حال تلف الملف، نستعيد البيانات الافتراضية
        save_data(DEFAULT_DATA)
        return DEFAULT_DATA.copy()


def save_data(data):
    """حفظ البيانات إلى ملف JSON."""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ================================================================
# 2. المسارات (Routes) - عرض الصفحات
# ================================================================

@app.route('/')
def index():
    """الصفحة الرئيسية - تعرض جميع البيانات من الخادم."""
    data = load_data()
    # تمرير البيانات إلى القالب لعرضها
    return render_template('index.html', data=data)


@app.route('/admin')
def admin_panel():
    """صفحة لوحة التحكم (تظهر كصفحة منفصلة أو يمكن تضمينها)."""
    data = load_data()
    return render_template('admin_panel.html', data=data)


# ================================================================
# 3. واجهة برمجة التطبيقات (API) - تعديل البيانات
# ================================================================

@app.route('/api/data', methods=['GET'])
def get_data():
    """إرجاع جميع البيانات بصيغة JSON."""
    return jsonify(load_data())


@app.route('/api/data', methods=['POST'])
def update_data():
    """
    تحديث البيانات بالكامل.
    يجب إرسال كائن JSON كامل يحتوي على جميع الحقول.
    """
    try:
        new_data = request.get_json()
        if not new_data:
            return jsonify({"error": "البيانات غير صالحة"}), 400

        # التحقق من وجود الحقول الأساسية
        required_fields = ['siteName', 'heroTitle', 'heroHighlight', 'heroSubtitle',
                           'bioText', 'ctaText', 'ctaLink', 'footerText',
                           'primaryColor', 'secondaryColor', 'services', 'projects', 'social']
        for field in required_fields:
            if field not in new_data:
                return jsonify({"error": f"الحقل {field} مفقود"}), 400

        save_data(new_data)
        return jsonify({"message": "تم حفظ البيانات بنجاح", "data": new_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================================================================
# 4. تشغيل الخادم
# ================================================================

if __name__ == '__main__':
    # تشغيل الخادم على المنفذ 5000 مع خاصية التحديث التلقائي
    app.run(debug=True, host='0.0.0.0', port=5000)