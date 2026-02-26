import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from config import DB_PATH

logger = logging.getLogger(__name__)

class Database:
    """إدارة جميع البيانات باستخدام ملف JSON."""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.data = self._load()

    def _load(self) -> Dict:
        """تحميل البيانات من الملف أو إنشاء هيكل جديد."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"خطأ في قراءة قاعدة البيانات: {e}")
                return self._empty_data()
        else:
            return self._empty_data()

    def _empty_data(self) -> Dict:
        """هيكل البيانات الافتراضي."""
        return {
            "series": {},          # اسم المسلسل -> {last_episode, channel_id, added_date}
            "movies": {},          # اسم الفيلم -> {file_id, channel_id, added_date}
            "sent_videos": {},     # file_unique_id -> {series_name, episode, file_id} or {movie_name}
            "channels": [],        # قائمة معرفات القنوات المسموح بها
            "users": {}            # user_id -> {"role": "admin" or "user"} (للبساطة)
        }

    def save(self):
        """حفظ البيانات إلى ملف JSON."""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ قاعدة البيانات: {e}")

    # ------------------ إدارة القنوات ------------------
    def get_channels(self) -> List[int]:
        return self.data["channels"]

    def add_channel(self, channel_id: int) -> bool:
        if channel_id not in self.data["channels"]:
            self.data["channels"].append(channel_id)
            self.save()
            return True
        return False

    def remove_channel(self, channel_id: int) -> bool:
        if channel_id in self.data["channels"]:
            self.data["channels"].remove(channel_id)
            self.save()
            return True
        return False

    # ------------------ المسلسلات ------------------
    def add_series_episode(self, series_name: str, episode: int, file_id: str, file_unique_id: str, channel_id: int):
        """تسجيل حلقة جديدة لمسلسل."""
        # تحديث معلومات المسلسل
        if series_name not in self.data["series"]:
            self.data["series"][series_name] = {
                "last_episode": 0,
                "channel_id": channel_id,
                "added_date": datetime.now().isoformat()
            }
        if episode > self.data["series"][series_name]["last_episode"]:
            self.data["series"][series_name]["last_episode"] = episode

        # تسجيل الفيديو المرسل
        self.data["sent_videos"][file_unique_id] = {
            "series_name": series_name,
            "episode": episode,
            "file_id": file_id
        }
        self.save()

    def get_series_list(self) -> List[str]:
        return list(self.data["series"].keys())

    def get_series_info(self, series_name: str) -> Optional[Dict]:
        return self.data["series"].get(series_name)

    def get_last_episode(self, series_name: str) -> int:
        return self.data["series"].get(series_name, {}).get("last_episode", 0)

    # ------------------ الأفلام ------------------
    def add_movie(self, movie_name: str, file_id: str, file_unique_id: str, channel_id: int):
        self.data["movies"][movie_name] = {
            "file_id": file_id,
            "channel_id": channel_id,
            "added_date": datetime.now().isoformat()
        }
        self.data["sent_videos"][file_unique_id] = {"movie_name": movie_name}
        self.save()

    def get_movies_list(self) -> List[str]:
        return list(self.data["movies"].keys())

    def get_movie_info(self, movie_name: str) -> Optional[Dict]:
        return self.data["movies"].get(movie_name)

    # ------------------ التحقق من التكرار ------------------
    def is_video_sent(self, file_unique_id: str) -> bool:
        return file_unique_id in self.data["sent_videos"]

    def get_video_info(self, file_unique_id: str) -> Optional[Dict]:
        return self.data["sent_videos"].get(file_unique_id)

    # ------------------ البحث ------------------
    def search(self, query: str) -> Dict[str, List[str]]:
        """البحث في المسلسلات والأفلام."""
        query = query.lower()
        result = {"series": [], "movies": []}
        for s in self.data["series"]:
            if query in s.lower():
                result["series"].append(s)
        for m in self.data["movies"]:
            if query in m.lower():
                result["movies"].append(m)
        return result

    # ------------------ المستخدمين (للبساطة نعتبر الجميع مشرفين) ------------------
    def is_admin(self, user_id: int) -> bool:
        # يمكنك تخصيص صلاحيات المشرفين هنا
        return True  # للتبسيط، كل المستخدمين مشرفون
