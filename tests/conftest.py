import io
import os
from pathlib import Path

import pytest
from PIL import Image

# TEMP_DIR должен быть задан до первого импорта src.utils.storage
_TEST_TEMP = Path(__file__).resolve().parent / "_tmp_storage"
_TEST_TEMP.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("TEMP_DIR", str(_TEST_TEMP))


@pytest.fixture
def make_jpeg_bytes():
    """Фабрика JPEG-байтов заданного размера и примерного объёма."""

    def _make(width: int = 100, height: int = 100, quality: int = 95) -> bytes:
        img = Image.new("RGB", (width, height), color=(30, 140, 220))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    return _make


@pytest.fixture
def large_jpeg_bytes(make_jpeg_bytes, monkeypatch):
    """JPEG больше тестового лимита сжатия (лимит снижен под solid-color JPEG)."""
    limit = 1500
    monkeypatch.setenv("MAX_PROCESSED_FILE_SIZE", str(limit))
    data = make_jpeg_bytes(width=400, height=400, quality=95)
    assert len(data) > limit
    return data


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    """Изолируем лимиты и хранилище между тестами."""
    monkeypatch.setenv("MAX_PROCESSED_FILE_SIZE", str(400 * 1024))
    monkeypatch.setenv(
        "TOKEN_SECRET_KEY",
        "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
    )
    monkeypatch.setenv("BOT_TOKEN", "0000000000:TESTTOKENFORUNITTESTS")
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    monkeypatch.setenv("TEMP_DIR", str(storage_dir))

    # Перенаправляем уже созданный singleton, если модуль уже импортирован
    try:
        import src.utils.storage as storage_mod

        monkeypatch.setattr(storage_mod.storage, "temp_dir", storage_dir)
    except Exception:
        pass
