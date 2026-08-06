"""Локальные live-тесты: реальный aiohttp-сервер + реальный ClientSession."""

from __future__ import annotations

import pytest
from aiohttp import web
from PIL import Image
import io

import aiohttp

from src.utils.image_processor import (
    get_image_dimensions,
    process_image_bytes,
    process_image_from_url,
)


@pytest.fixture
async def live_image_server(make_jpeg_bytes):
    """Поднимает локальный aiohttp HTTP-сервер с JPEG и 404."""
    image_bytes = make_jpeg_bytes(800, 600)
    oversized = make_jpeg_bytes(400, 400, quality=95)

    async def ok_handler(_request: web.Request) -> web.Response:
        return web.Response(body=image_bytes, content_type="image/jpeg")

    async def missing_handler(_request: web.Request) -> web.Response:
        return web.Response(status=404, text="not found")

    async def big_handler(_request: web.Request) -> web.Response:
        return web.Response(body=oversized, content_type="image/jpeg")

    app = web.Application()
    app.router.add_get("/photo.jpg", ok_handler)
    app.router.add_get("/missing.jpg", missing_handler)
    app.router.add_get("/big.jpg", big_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    host, port = runner.addresses[0][:2]
    base_url = f"http://{host}:{port}"
    try:
        yield {
            "base_url": base_url,
            "photo_url": f"{base_url}/photo.jpg",
            "missing_url": f"{base_url}/missing.jpg",
            "big_url": f"{base_url}/big.jpg",
            "image_bytes": image_bytes,
        }
    finally:
        await runner.cleanup()


@pytest.mark.live_http
@pytest.mark.asyncio
async def test_live_aiohttp_downloads_image(live_image_server):
    async with aiohttp.ClientSession() as session:
        async with session.get(live_image_server["photo_url"]) as response:
            assert response.status == 200
            body = await response.read()

    assert body == live_image_server["image_bytes"]
    assert get_image_dimensions(body) == (800, 600)


@pytest.mark.live_http
@pytest.mark.asyncio
async def test_live_process_image_from_url(live_image_server, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()

    path, result = await process_image_from_url(live_image_server["photo_url"])
    assert result.original_size == len(live_image_server["image_bytes"])
    assert (tmp_path / path).exists()
    with Image.open(io.BytesIO(result.bytes)) as img:
        assert img.size == (800, 600)


@pytest.mark.live_http
@pytest.mark.asyncio
async def test_live_process_image_from_url_404(live_image_server, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()

    with pytest.raises(ValueError, match="Не удалось загрузить"):
        await process_image_from_url(live_image_server["missing_url"])


@pytest.mark.live_http
@pytest.mark.asyncio
async def test_live_download_then_compress(live_image_server, monkeypatch):
    monkeypatch.setenv("MAX_PROCESSED_FILE_SIZE", "1500")

    async with aiohttp.ClientSession() as session:
        async with session.get(live_image_server["big_url"]) as response:
            assert response.status == 200
            raw = await response.read()

    assert len(raw) > 1500
    result = await process_image_bytes(raw, target_width=200, target_height=150)
    assert result.final_size <= 1500
    with Image.open(io.BytesIO(result.bytes)) as img:
        assert img.size == (200, 150)


@pytest.mark.live_http
@pytest.mark.asyncio
async def test_live_aiohttp_client_session_headers(live_image_server):
    """Проверяет, что клиент 3.14.x нормально ходит по HTTP с заголовками."""
    headers = {"User-Agent": "ImagesReshaper-LiveTest/1.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(live_image_server["photo_url"]) as response:
            assert response.status == 200
            assert response.content_type.startswith("image/")
            chunk = await response.content.read(16)
            assert chunk[:2] == b"\xff\xd8"  # JPEG SOI
