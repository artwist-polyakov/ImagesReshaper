import io
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture
def client(monkeypatch, tmp_path):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("TOKEN_SECRET_KEY", key)
    monkeypatch.setenv("MAX_UPLOAD_SIZE", str(5 * 1024 * 1024))

    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    import importlib
    import src.utils.storage as storage_mod
    import src.webapp.main as webapp_main

    importlib.reload(storage_mod)
    importlib.reload(webapp_main)
    return TestClient(webapp_main.app), webapp_main


def _jpeg_bytes(width=120, height=80) -> bytes:
    img = Image.new("RGB", (width, height), color=(10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_root_serves_html(client):
    test_client, _ = client
    response = test_client.get("/")
    assert response.status_code == 200
    assert "ok" in response.text


def test_upload_rejects_invalid_token(client):
    test_client, _ = client
    response = test_client.post(
        "/upload",
        params={"token": "bad-token"},
        files={"file": ("img.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 401


def test_upload_success_stores_image_and_notifies(client):
    test_client, webapp_main = client
    token = webapp_main.token_manager.create_token(user_id=7)

    with patch(
        "src.webapp.main.send_resize_options_to_telegram",
        new_callable=AsyncMock,
    ) as send_mock:
        response = test_client.post(
            "/upload",
            params={"token": token},
            files={"file": ("img.jpg", _jpeg_bytes(800, 600), "image/jpeg")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    send_mock.assert_awaited_once()
    stored = webapp_main.storage.get_image(7)
    assert stored is not None
    assert stored["original_size"] == (800, 600)


def test_upload_returns_502_when_telegram_fails(client):
    from telegram.error import TimedOut

    test_client, webapp_main = client
    token = webapp_main.token_manager.create_token(user_id=8)

    with patch(
        "src.webapp.main.send_resize_options_to_telegram",
        new_callable=AsyncMock,
        side_effect=TimedOut("Timed out"),
    ):
        response = test_client.post(
            "/upload",
            params={"token": token},
            files={"file": ("img.jpg", _jpeg_bytes(100, 80), "image/jpeg")},
        )

    assert response.status_code == 502
    assert response.json()["detail"].startswith("telegram_notify_failed:")
    # Картинка уже должна быть сохранена до нотификации
    assert webapp_main.storage.get_image(8) is not None
