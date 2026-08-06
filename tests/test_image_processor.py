import aiohttp
import pytest
from PIL import Image, __version__ as pillow_version
import io

from src.utils.image_processor import (
    calculate_resize_options,
    get_image_dimensions,
    process_image_bytes,
    process_image_from_url,
)


def test_aiohttp_patched_version():
    """CVE-2026-69244 исправлен в aiohttp >= 3.14.3."""
    parts = tuple(int(p) for p in aiohttp.__version__.split(".")[:3])
    assert parts >= (3, 14, 3)


def test_pillow_patched_version():
    """Pillow CVE bundle (JPEG2000/PDF/TGA/CMS/…) исправлен в >= 12.3.0."""
    parts = tuple(int(p) for p in pillow_version.split(".")[:3])
    assert parts >= (12, 3, 0)


def test_get_image_dimensions(make_jpeg_bytes):
    data = make_jpeg_bytes(320, 240)
    assert get_image_dimensions(data) == (320, 240)


def test_calculate_resize_options_small_image():
    options = calculate_resize_options(400, 300)
    assert len(options) == 1
    assert options[0]["width"] == 400
    assert options[0]["height"] == 300


def test_calculate_resize_options_wide_image():
    options = calculate_resize_options(3000, 1500)
    widths = {opt["width"] for opt in options}
    assert 3000 in widths
    assert 640 in widths
    assert 1280 in widths
    assert 2560 in widths


@pytest.mark.asyncio
async def test_process_image_bytes_passthrough_when_small(make_jpeg_bytes):
    data = make_jpeg_bytes(100, 100)
    result = await process_image_bytes(data)
    assert result.bytes == data
    assert result.final_size == len(data)
    assert result.quality == 100


@pytest.mark.asyncio
async def test_process_image_bytes_compresses_large(large_jpeg_bytes):
    limit = int(__import__("os").getenv("MAX_PROCESSED_FILE_SIZE", "1500"))
    result = await process_image_bytes(large_jpeg_bytes)
    assert result.original_size == len(large_jpeg_bytes)
    assert result.final_size <= limit
    assert result.final_size > 0
    # Результат должен открываться как изображение
    with Image.open(io.BytesIO(result.bytes)) as img:
        assert img.size[0] > 0


@pytest.mark.asyncio
async def test_process_image_bytes_with_resize(large_jpeg_bytes):
    limit = int(__import__("os").getenv("MAX_PROCESSED_FILE_SIZE", "1500"))
    result = await process_image_bytes(
        large_jpeg_bytes, target_width=200, target_height=200
    )
    with Image.open(io.BytesIO(result.bytes)) as img:
        assert img.size == (200, 200)
    assert result.final_size <= limit


@pytest.mark.asyncio
async def test_process_image_from_url_success(make_jpeg_bytes, tmp_path, monkeypatch):
    data = make_jpeg_bytes(200, 150)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()

    class FakeResponse:
        status = 200

        async def read(self):
            return data

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class FakeSession:
        def get(self, url):
            return FakeResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(aiohttp, "ClientSession", lambda: FakeSession())

    path, result = await process_image_from_url("https://example.com/img.jpg")
    assert result.original_size == len(data)
    assert (tmp_path / path).exists()


@pytest.mark.asyncio
async def test_process_image_from_url_http_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()

    class FakeResponse:
        status = 404

        async def read(self):
            return b""

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class FakeSession:
        def get(self, url):
            return FakeResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(aiohttp, "ClientSession", lambda: FakeSession())

    with pytest.raises(ValueError, match="Не удалось загрузить"):
        await process_image_from_url("https://example.com/missing.jpg")
