import cryptography

from src.utils.token_manager import TokenManager


def test_cryptography_patched_version():
    """CVE-2026-69248 / CVE-2026-69249 исправлены в cryptography >= 49.0.0."""
    parts = tuple(int(p) for p in cryptography.__version__.split(".")[:3])
    assert parts >= (49, 0, 0)


def test_create_and_validate_token():
    manager = TokenManager()
    token = manager.create_token(user_id=42)
    data = manager.validate_token(token)
    assert data is not None
    assert data["user_id"] == 42
    assert "expires_at" in data


def test_validate_invalid_token_returns_none():
    manager = TokenManager()
    assert manager.validate_token("not-a-valid-token") is None
