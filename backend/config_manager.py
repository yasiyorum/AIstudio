"""
Kalıcı Ayar Yönetimi — AI Model Stüdyosu
data_storage/config.json dosyasında ayarları güvenli ve thread-safe biçimde yönetir.
"""
import os
import json
import threading
from backend.logger import logger

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_DIR = os.path.join(_BASE_DIR, "data_storage")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "provider": "Ollama (Local)",
    "api_key": "",
    "rag_base_model": "Otomatik (En iyi model)",
    "temperature": 0.7,
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "last_model": "Model Seçiniz",
    "theme": "Dark",
    "ft_learning_rate": 0.0002,
    "ft_max_steps": 50,
    "ft_batch_size": 2
}

class ConfigManager:
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigManager, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.file_path = _CONFIG_FILE
        self._data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        """Diskteki config dosyasını yükler, eksik anahtarları varsayılanla tamamlar."""
        with self._lock:
            if os.path.exists(self.file_path):
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                        if isinstance(saved, dict):
                            self._data.update(saved)
                            logger.info(f"Ayarlar başarıyla yüklendi: {self.file_path}")
                except Exception as e:
                    logger.error(f"Ayarlar dosyası okunamadı, varsayılanlar kullanılacak: {e}")
            else:
                self.save()

    def save(self):
        """Mevcut ayarları diske kaydeder."""
        with self._lock:
            try:
                os.makedirs(_CONFIG_DIR, exist_ok=True)
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
                logger.info("Ayarlar diske kaydedildi.")
                return True
            except Exception as e:
                logger.error(f"Ayarlar diske kaydedilemedi: {e}")
                return False

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key, value, auto_save=True):
        with self._lock:
            self._data[key] = value
        if auto_save:
            self.save()

    def get_all(self):
        with self._lock:
            return dict(self._data)
