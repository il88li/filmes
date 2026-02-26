import json
import logging
from typing import Dict, Optional, Any
from pathlib import Path

from config import DB_PATH

# إعداد تسجيل الأحداث
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SeriesDatabase:
    """إدارة قاعدة بيانات المسلسلات والأفلام باستخدام ملف JSON."""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.data: Dict[str, Any] = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """تحميل البيانات من ملف JSON أو إنشاء هيكل جديد إذا لم يكن الملف موجوداً."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"خطأ في قراءة قاعدة البيانات: {e}. سيتم إنشاء قاعدة بيانات جديدة.")
                return self._get_empty_structure()
        else:
            logger.info("لم يتم العثور على قاعدة بيانات. سيتم إنشاء قاعدة جديدة.")
            return self._get_empty_structure()

    def _get_empty_structure(self) -> Dict[str, Any]:
        """إرجاع هيكل قاعدة البيانات الفارغ."""
        return {
            "series": {},      # حفظ معلومات المسلسلات: {"اسم_المسلسل": {"last_episode": 5, "channel_id": -100...}}
            "movies": {},      # حفظ معلومات الأفلام: {"اسم_الفيلم": {"file_id": "..."}}
            "sent_videos": {}  # حفظ الفيديوهات التي تم إرسالها لتجنب التكرار: {"file_unique_id": {"series_name": "...", "episode": ...}}
        }

    def save(self) -> None:
        """حفظ البيانات الحالية إلى ملف JSON."""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"خطأ في حفظ قاعدة البيانات: {e}")

    def add_series_episode(self, series_name: str, episode: int, file_id: str, file_unique_id: str, channel_id: int) -> None:
        """
        إضافة حلقة جديدة لمسلسل معين.
        
        - series_name: اسم المسلسل
        - episode: رقم الحلقة
        - file_id: معرف الفيديو من تليجرام
        - file_unique_id: معرف فريد للفيديو (للكشف عن التكرار)
        - channel_id: معرف القناة التي أرسل إليها الفيديو
        """
        # تحديث معلومات المسلسل
        series_info = self.data["series"].get(series_name, {"last_episode": 0, "channel_id": channel_id})
        if episode > series_info["last_episode"]:
            series_info["last_episode"] = episode
        series_info["channel_id"] = channel_id
        self.data["series"][series_name] = series_info

        # تسجيل الفيديو المرسل
        self.data["sent_videos"][file_unique_id] = {
            "series_name": series_name,
            "episode": episode,
            "file_id": file_id
        }
        self.save()

    def add_movie(self, movie_name: str, file_id: str, file_unique_id: str, channel_id: int) -> None:
        """إضافة فيلم جديد."""
        self.data["movies"][movie_name] = {
            "file_id": file_id,
            "channel_id": channel_id
        }
        self.data["sent_videos"][file_unique_id] = {
            "movie_name": movie_name
        }
        self.save()

    def is_video_sent(self, file_unique_id: str) -> bool:
        """التحقق مما إذا كان الفيديو قد أرسل من قبل باستخدام معرفه الفريد."""
        return file_unique_id in self.data["sent_videos"]

    def get_video_info(self, file_unique_id: str) -> Optional[Dict[str, Any]]:
        """استرجاع معلومات فيديو تم إرساله مسبقاً."""
        return self.data["sent_videos"].get(file_unique_id)

    def get_series_last_episode(self, series_name: str) -> int:
        """الحصول على رقم آخر حلقة تم إرسالها لمسلسل معين."""
        return self.data["series"].get(series_name, {}).get("last_episode", 0)

    def search_series_or_movie(self, query: str) -> Dict[str, Any]:
        """البحث عن مسلسل أو فيلم باسمه (للاستخدام المستقبلي)."""
        results = {"series": [], "movies": []}
        query_lower = query.lower()
        for series_name in self.data["series"]:
            if query_lower in series_name.lower():
                results["series"].append(series_name)
        for movie_name in self.data["movies"]:
            if query_lower in movie_name.lower():
                results["movies"].append(movie_name)
        return results
