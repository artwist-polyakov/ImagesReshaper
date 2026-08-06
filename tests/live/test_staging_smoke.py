"""Smoke-тесты против живого staging/prod webapp.

Запуск:
  RUN_LIVE=1 LIVE_BASE_URL=http://195.2.78.87:8000 pytest -m live -q
"""

from __future__ import annotations

import io
import os

import httpx
import pytest
from PIL import Image


def _live_enabled() -> bool:
    return os.getenv("RUN_LIVE", "").strip() in {"1", "true", "yes"}


@pytest.fixture(scope="module")
def live_base_url() -> str:
    if not _live_enabled():
        pytest.skip("Live-тесты отключены (задайте RUN_LIVE=1)")
    return os.getenv("LIVE_BASE_URL", "http://195.2.78.87:8000").rstrip("/")


@pytest.fixture(scope="module")
def live_client(live_base_url: str):
    with httpx.Client(base_url=live_base_url, timeout=20.0) as client:
        yield client


@pytest.mark.live
def test_live_root_returns_html(live_client: httpx.Client):
    response = live_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert len(response.text) > 50


@pytest.mark.live
def test_live_static_upload_js(live_client: httpx.Client):
    response = live_client.get("/static/js/upload.js")
    assert response.status_code == 200
    assert "dropZone" in response.text or "fileInput" in response.text


@pytest.mark.live
def test_live_upload_rejects_bad_token(live_client: httpx.Client):
    img = Image.new("RGB", (64, 64), color=(1, 2, 3))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    response = live_client.post(
        "/upload",
        params={"token": "definitely-invalid-token"},
        files={"file": ("live.jpg", buf.getvalue(), "image/jpeg")},
    )
    # После фикса HTTPException больше не маскируется в 500
    assert response.status_code == 401


@pytest.mark.live
def test_live_upload_with_valid_token_if_provided(live_client: httpx.Client):
    """Опционально: LIVE_UPLOAD_TOKEN=... для полного upload-smoke."""
    token = os.getenv("LIVE_UPLOAD_TOKEN", "").strip()
    if not token:
        pytest.skip("LIVE_UPLOAD_TOKEN не задан")

    img = Image.new("RGB", (320, 240), color=(40, 80, 120))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)

    response = live_client.post(
        "/upload",
        params={"token": token},
        files={"file": ("live.jpg", buf.getvalue(), "image/jpeg")},
    )

    if response.status_code == 200:
        body = response.json()
        assert body.get("status") == "success"
        return

    # Изображение могло сохраниться, а нотификация в Telegram — нет (сеть/API).
    assert response.status_code == 502, response.text
    detail = str(response.json().get("detail", ""))
    assert detail.startswith("telegram_notify_failed:"), detail
