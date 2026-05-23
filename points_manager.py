import os
import json
import logging
import threading

logger = logging.getLogger(__name__)

class PointsManager:
    """Sistema de puntos/coins por viewer. Thread-safe."""

    def __init__(self, data_dir=None):
        self._data_dir = data_dir or os.path.dirname(os.path.abspath(__file__))
        self._path = os.path.join(self._data_dir, "data", "points.json")
        self._lock = threading.Lock()
        self._points = {}
        self._load()

    def _load(self):
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._points = data
                    else:
                        self._points = {}
        except Exception as e:
            logger.warning(f"Error cargando points: {e}")
            self._points = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._points, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando points: {e}")

    def add(self, user, amount):
        if not user or amount <= 0:
            return
        with self._lock:
            key = user.lower().strip()
            self._points[key] = self._points.get(key, 0) + amount
            self._save()

    def get(self, user):
        with self._lock:
            key = user.lower().strip() if user else ""
            return self._points.get(key, 0)

    def get_top(self, limit=10):
        with self._lock:
            sorted_users = sorted(self._points.items(), key=lambda x: x[1], reverse=True)
            return [{"user": u, "points": p} for u, p in sorted_users[:limit]]

    def get_all(self):
        with self._lock:
            return dict(self._points)

    def reset(self, user):
        with self._lock:
            key = user.lower().strip() if user else ""
            if key in self._points:
                del self._points[key]
                self._save()
