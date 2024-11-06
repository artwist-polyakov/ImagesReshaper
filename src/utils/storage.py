import os
import shutil
from pathlib import Path

class ImageStorage:
    def __init__(self):
        self.temp_dir = Path("/app/temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_dir(self, user_id: int) -> Path:
        """Получает путь к директории пользователя"""
        user_dir = self.temp_dir / str(user_id)
        user_dir.mkdir(exist_ok=True)
        return user_dir

    def save_image(self, user_id: int, image_data: dict):
        """Сохраняет изображение во временную директорию"""
        user_dir = self._get_user_dir(user_id)
        
        # Очищаем старые файлы пользователя
        self.cleanup_user_files(user_id)
        
        # Сохраняем новое изображение
        image_path = user_dir / "pending_image.jpg"
        with open(image_path, "wb") as f:
            f.write(image_data['bytes'])
            
        # Сохраняем метаданные
        meta_path = user_dir / "metadata.txt"
        with open(meta_path, "w") as f:
            f.write(f"{image_data['original_size'][0]},{image_data['original_size'][1]}")

    def get_image(self, user_id: int):
        """Получает изображение из временной директории"""
        user_dir = self._get_user_dir(user_id)
        image_path = user_dir / "pending_image.jpg"
        meta_path = user_dir / "metadata.txt"
        
        if not image_path.exists() or not meta_path.exists():
            return None
            
        # Читаем изображение
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            
        # Читаем метаданные
        with open(meta_path, "r") as f:
            width, height = map(int, f.read().split(","))
            
        return {
            'bytes': image_bytes,
            'original_size': (width, height)
        }

    def delete_image(self, user_id: int):
        """Удаляет все файлы пользователя"""
        self.cleanup_user_files(user_id)

    def cleanup_user_files(self, user_id: int):
        """Очищает все файлы пользователя"""
        user_dir = self._get_user_dir(user_id)
        if user_dir.exists():
            shutil.rmtree(user_dir)
            user_dir.mkdir(exist_ok=True)

    def cleanup_old_files(self, max_age_hours: int = 1):
        """Очищает старые файлы"""
        import time
        current_time = time.time()
        
        for user_dir in self.temp_dir.iterdir():
            if not user_dir.is_dir():
                continue
                
            # Проверяем время последнего изменения директории
            dir_time = user_dir.stat().st_mtime
            if current_time - dir_time > max_age_hours * 3600:
                shutil.rmtree(user_dir)

# Создаем глобальный экземпляр хранилища
storage = ImageStorage() 