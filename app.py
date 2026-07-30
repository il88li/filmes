import os
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import ImageUploadField
from werkzeug.utils import secure_filename
import uuid

# ============================================================
# تهيئة التطبيق وقاعدة البيانات
# ============================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///projects.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# مجلد رفع الصور
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# ============================================================
# نموذج قاعدة البيانات (جدول المشاريع)
# ============================================================
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)  # رابط خارجي
    image_file = db.Column(db.String(200), nullable=True) # ملف مرفوع محلياً
    video_url = db.Column(db.String(500), nullable=True) # رابط فيديو (يوتيوب/فيميو)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Project {self.title}>'

# إنشاء الجداول (تشغيل مرة واحدة)
with app.app_context():
    db.create_all()

# ============================================================
# تكوين Flask-Admin (لوحة التحكم)
# ============================================================
class ProjectAdmin(ModelView):
    # الأعمدة المعروضة في القائمة
    column_list = ['id', 'title', 'category', 'image_file', 'image_url', 'is_active', 'sort_order']
    column_labels = {
        'title': 'العنوان',
        'category': 'الفئة',
        'image_url': 'رابط الصورة (خارجي)',
        'image_file': 'رفع صورة (محلي)',
        'video_url': 'رابط الفيديو',
        'is_active': 'مفعل',
        'sort_order': 'ترتيب العرض'
    }
    column_choices = {
        'category': [
            ('social', 'تصاميم السوشيال ميديا'),
            ('logo', 'الشعارات'),
            ('brand', 'الهوية البصرية'),
            ('banner', 'البنرات'),
            ('thumbnail', 'الصور المصغرة'),
            ('editing', 'المونتاج'),
            ('reels', 'الريلز والشورتس'),
            ('ads', 'فيديوهات إعلانية')
        ]
    }
    
    # حقول النموذج في صفحة الإضافة/التعديل
    form_columns = ['title', 'category', 'image_url', 'image_file', 'video_url', 'is_active', 'sort_order']
    form_widget_args = {
        'title': {'placeholder': 'أدخل عنوان العمل'},
        'image_url': {'placeholder': 'https://example.com/image.jpg'},
        'video_url': {'placeholder': 'https://youtube.com/embed/...'},
    }

    # دعم رفع الملفات المحلية
    form_extra_fields = {
        'image_file': ImageUploadField(
            'رفع صورة',
            base_path=app.config['UPLOAD_FOLDER'],
            url_relative_path='uploads/',
            namegen=lambda obj, file_data: f"{uuid.uuid4().hex}_{secure_filename(file_data.filename)}",
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp']
        )
    }

    # جعل الحقول اختيارية
    form_args = {
        'image_url': {'required': False},
        'image_file': {'required': False},
        'video_url': {'required': False},
    }

    def get_image_url(self, obj):
        """إرجاع رابط الصورة النهائي (يستخدم الأولوية للملف المحلي)"""
        if obj.image_file:
            return f"/static/uploads/{obj.image_file}"
        return obj.image_url or ''

# إضافة الواجهة الإدارية
admin = Admin(app, name='YM Studio - لوحة التحكم', template_mode='bootstrap4')
admin.add_view(ProjectAdmin(Project, db.session, name='المشاريع', endpoint='admin_projects'))

# ============================================================
# نقطة نهاية API لجلب البيانات (للواجهة الأمامية)
# ============================================================
@app.route('/api/projects')
def get_projects():
    """إرجاع قائمة المشاريع النشطة بصيغة JSON"""
    projects = Project.query.filter_by(is_active=True).order_by(Project.sort_order.asc()).all()
    data = []
    for p in projects:
        img = p.image_file if p.image_file else p.image_url
        data.append({
            'id': p.id,
            'title': p.title,
            'category': p.category,
            'image_url': f"/static/uploads/{p.image_file}" if p.image_file else p.image_url,
            'video_url': p.video_url
        })
    return jsonify(data)

# ============================================================
# الصفحة الرئيسية
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')

# ============================================================
# تشغيل التطبيق
# ============================================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)