"""Тесты хранилища изображений."""
import errno
import os
import shutil
import time
from pathlib import Path

import pytest

from src.utils.storage import ImageStorage, StorageFullError


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
    root = tmp_path / "empty"
    monkeypatch.setenv("TEMP_DIR", str(root))
    storage = ImageStorage()
    assert storage.get_image(999) is None
    assert not (root / "999").exists()


def test_cleanup_old_files_removes_stale_user_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TEMP_DIR", str(tmp_path))
    storage = ImageStorage()
    stale = tmp_path / "5"
    stale.mkdir()
    (stale / "pending_image.jpg").write_bytes(b"x")
    old = time.time() - 7200
    os.utime(stale, (old, old))

    fresh = tmp_path / "6"
    fresh.mkdir()
    (fresh / "pending_image.jpg").write_bytes(b"y")

    storage.cleanup_old_files(max_age_hours=1)

    assert not stale.exists()
    assert fresh.exists()


def test_save_drops_other_user_when_reported_free_space_is_low(tmp_path, monkeypatch):
    monkeypatch.setenv("TEMP_DIR", str(tmp_path))
    storage = ImageStorage()
    other = tmp_path / "111"
    other.mkdir()
    (other / "pending_image.jpg").write_bytes(b"old")

    real_usage = shutil.disk_usage

    def usage(path):
        base = real_usage(path)
        has_other = any(entry.name != "7" for entry in Path(path).iterdir())
        free = 0 if has_other else base.free
        return type(base)(base.total, base.total - free, free)

    monkeypatch.setattr("src.utils.storage.shutil.disk_usage", usage)
    storage.save_image(7, {"bytes": b"new", "original_size": (2, 3)})

    assert not other.exists()
    loaded = storage.get_image(7)
    assert loaded is not None
    assert loaded["bytes"] == b"new"
    assert loaded["original_size"] == (2, 3)


def test_low_space_reclaims_own_image_before_other_users(tmp_path, monkeypatch):
    root = tmp_path / "temp"
    monkeypatch.setenv("TEMP_DIR", str(root))
    storage = ImageStorage()
    own = root / "7"
    own.mkdir()
    (own / "pending_image.jpg").write_bytes(b"x" * 3_000_000)
    other = root / "111"
    other.mkdir()
    (other / "pending_image.jpg").write_bytes(b"other")

    real_usage = shutil.disk_usage
    removed = []
    real_remove = storage._remove_entry

    def usage(path):
        base = real_usage(path)
        free = 0 if (root / "7").exists() else base.free
        return type(base)(base.total, base.total - free, free)

    def remove(entry):
        removed.append(entry.name)
        real_remove(entry)

    monkeypatch.setattr("src.utils.storage.shutil.disk_usage", usage)
    monkeypatch.setattr(storage, "_remove_entry", remove)
    storage.save_image(7, {"bytes": b"new", "original_size": (2, 3)})

    assert removed == ["7"]
    assert other.exists()
    loaded = storage.get_image(7)
    assert loaded is not None
    assert loaded["bytes"] == b"new"


def test_low_space_evicts_others_only_after_own_image(tmp_path, monkeypatch):
    root = tmp_path / "temp"
    monkeypatch.setenv("TEMP_DIR", str(root))
    storage = ImageStorage()
    own = root / "7"
    own.mkdir()
    (own / "pending_image.jpg").write_bytes(b"own")
    other = root / "111"
    other.mkdir()
    (other / "pending_image.jpg").write_bytes(b"other")

    real_usage = shutil.disk_usage
    removed = []
    real_remove = storage._remove_entry

    def usage(path):
        base = real_usage(path)
        free = 0 if (root / "111").exists() else base.free
        return type(base)(base.total, base.total - free, free)

    def remove(entry):
        removed.append(entry.name)
        real_remove(entry)

    monkeypatch.setattr("src.utils.storage.shutil.disk_usage", usage)
    monkeypatch.setattr(storage, "_remove_entry", remove)
    storage.save_image(7, {"bytes": b"new", "original_size": (2, 3)})

    assert removed == ["7", "111"]
    assert not other.exists()
    loaded = storage.get_image(7)
    assert loaded is not None
    assert loaded["bytes"] == b"new"


def test_enospc_evicts_oldest_other_when_df_still_looks_free(tmp_path, monkeypatch):
    root = tmp_path / "temp"
    monkeypatch.setenv("TEMP_DIR", str(root))
    storage = ImageStorage()
    oldest = root / "100"
    newest = root / "200"
    oldest.mkdir()
    newest.mkdir()
    (oldest / "pending_image.jpg").write_bytes(b"old")
    (newest / "pending_image.jpg").write_bytes(b"new")
    now = time.time()
    os.utime(oldest, (now - 30, now - 30))
    os.utime(newest, (now - 5, now - 5))

    real_write = storage._write_pending

    def write(user_id, payload, width, height):
        if oldest.exists():
            raise OSError(errno.ENOSPC, "No space left on device")
        real_write(user_id, payload, width, height)

    monkeypatch.setattr(storage, "_write_pending", write)
    storage.save_image(7, {"bytes": b"ok", "original_size": (4, 5)})

    assert not oldest.exists()
    assert newest.exists()
    loaded = storage.get_image(7)
    assert loaded is not None
    assert loaded["bytes"] == b"ok"


def test_save_retries_once_on_enospc_then_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("TEMP_DIR", str(tmp_path / "temp"))
    storage = ImageStorage()
    calls = {"n": 0}

    def write(user_id, payload, width, height):
        calls["n"] += 1
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(storage, "_write_pending", write)

    with pytest.raises(StorageFullError):
        storage.save_image(7, {"bytes": b"abc", "original_size": (1, 1)})
    assert calls["n"] == 2


def test_save_succeeds_on_second_attempt_after_enospc(tmp_path, monkeypatch):
    monkeypatch.setenv("TEMP_DIR", str(tmp_path))
    storage = ImageStorage()
    calls = {"n": 0}
    real_write = storage._write_pending

    def write(user_id, payload, width, height):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError(errno.ENOSPC, "No space left on device")
        real_write(user_id, payload, width, height)

    monkeypatch.setattr(storage, "_write_pending", write)
    storage.save_image(7, {"bytes": b"ok", "original_size": (4, 5)})

    loaded = storage.get_image(7)
    assert loaded is not None
    assert loaded["bytes"] == b"ok"
    assert calls["n"] == 2
