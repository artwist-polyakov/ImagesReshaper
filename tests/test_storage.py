"""Тесты хранилища изображений."""
from src.utils.storage import ImageStorage


def test_save_and_get_image(tmp_path, monkeypatch):
    storage_dir = tmp_path / "s"
    monkeypatch.setenv("TEMP_DIR", str(storage_dir))
    storage = ImageStorage()

    payload = {"bytes": b"fake-jpeg", "original_size": (640, 480)}
    storage.save_image(1, payload)
    loaded = storage.get_image(1)

    assert loaded is not None
    assert loaded["bytes"] == b"fake-jpeg"
    assert loaded["original_size"] == (640, 480)


def test_get_missing_image_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("TEMP_DIR", str(tmp_path / "empty"))
    storage = ImageStorage()
    assert storage.get_image(999) is None
