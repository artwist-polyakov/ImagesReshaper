import errno
import os
import shutil
import time
from pathlib import Path


class StorageFullError(Exception):
    """На диске временных файлов не осталось места даже после очистки."""


class ImageStorage:
    def __init__(self):
        self.temp_dir = Path(os.getenv("TEMP_DIR", "/app/temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _user_dir(self, user_id: int) -> Path:
        return self.temp_dir / str(user_id)

    def save_image(self, user_id: int, image_data: dict):
        """Сохраняет изображение во временную директорию."""
        payload = image_data["bytes"]
        width, height = image_data["original_size"]
        # Запас на каталог, metadata и служебные блоки ФС.
        needed = len(payload) + 1024 * 1024
        self._prepare_space(needed, user_id)
        try:
            self._write_pending(user_id, payload, width, height)
        except OSError as exc:
            if exc.errno != errno.ENOSPC:
                raise
            print(
                f"Недостаточно места при записи в {self._user_dir(user_id)}, "
                "повторяю после очистки"
            )
            self._prepare_space(needed, user_id)
            try:
                self._write_pending(user_id, payload, width, height)
            except OSError as retry_exc:
                if retry_exc.errno == errno.ENOSPC:
                    raise StorageFullError(
                        "Недостаточно места для временного файла"
                    ) from retry_exc
                raise

    def _write_pending(self, user_id: int, payload: bytes, width: int, height: int):
        user_dir = self._user_dir(user_id)
        if user_dir.exists():
            shutil.rmtree(user_dir)
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / "pending_image.jpg").write_bytes(payload)
        (user_dir / "metadata.txt").write_text(f"{width},{height}")

    def _free_bytes(self) -> int:
        return shutil.disk_usage(self.temp_dir).free

    def _prepare_space(self, needed: int, user_id: int):
        """Удаляет старые загрузки, если под новый файл не хватает места.

        Не бросает ошибку само по себе: у root ещё может быть резерв блоков,
        поэтому окончательное решение остаётся за реальной записью.
        """
        if self._free_bytes() >= needed:
            self.cleanup_old_files()
            return

        free = self._free_bytes()
        print(
            f"Мало места в {self.temp_dir}: свободно {free}, нужно {needed}. "
            "Удаляю старые загрузки."
        )
        self._delete_oldest_until(needed, keep_user_id=user_id)
        if self._free_bytes() < needed:
            self.cleanup_user_files(user_id)

    def _delete_oldest_until(self, needed: int, keep_user_id: int | None):
        keep_name = None if keep_user_id is None else str(keep_user_id)
        entries = []
        for entry in self.temp_dir.iterdir():
            if entry.name == keep_name:
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            entries.append((mtime, entry))
        entries.sort()
        for _, entry in entries:
            self._remove_entry(entry)
            if self._free_bytes() >= needed:
                return

    def _remove_entry(self, entry: Path):
        try:
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink(missing_ok=True)
        except OSError as exc:
            print(f"Не удалось удалить {entry}: {exc}")

    def get_image(self, user_id: int):
        """Получает изображение из временной директории."""
        user_dir = self._user_dir(user_id)
        image_path = user_dir / "pending_image.jpg"
        meta_path = user_dir / "metadata.txt"

        if not image_path.exists() or not meta_path.exists():
            return None

        image_bytes = image_path.read_bytes()
        width, height = map(int, meta_path.read_text().split(","))

        return {
            "bytes": image_bytes,
            "original_size": (width, height),
        }

    def delete_image(self, user_id: int):
        """Удаляет все файлы пользователя."""
        self.cleanup_user_files(user_id)

    def cleanup_user_files(self, user_id: int):
        """Очищает все файлы пользователя."""
        user_dir = self._user_dir(user_id)
        if user_dir.exists():
            self._remove_entry(user_dir)

    def cleanup_old_files(self, max_age_hours: int = 1):
        """Очищает файлы старше max_age_hours."""
        cutoff = time.time() - max_age_hours * 3600
        for entry in list(self.temp_dir.iterdir()):
            try:
                if entry.stat().st_mtime > cutoff:
                    continue
            except OSError:
                continue
            self._remove_entry(entry)


# Создаем глобальный экземпляр хранилища
storage = ImageStorage()
