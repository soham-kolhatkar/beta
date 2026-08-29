"""Unit tests: pure logic, no DB, no HTTP. See docs/ARCHITECTURE.md §32
"Backend unit tests". Integration-level auth flow tests live in test_auth.py.
"""

from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)


def test_hash_password_roundtrip() -> None:
    password_hash = hash_password("correct-horse-battery-staple")

    assert verify_password("correct-horse-battery-staple", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_hash_password_is_salted() -> None:
    hash_a = hash_password("same-password")
    hash_b = hash_password("same-password")

    assert hash_a != hash_b
    assert verify_password("same-password", hash_a) is True
    assert verify_password("same-password", hash_b) is True


def test_generate_session_token_is_unique_and_high_entropy() -> None:
    tokens = {generate_session_token() for _ in range(100)}

    assert len(tokens) == 100
    assert all(len(token) >= 32 for token in tokens)


def test_hash_session_token_is_deterministic() -> None:
    token = generate_session_token()

    assert hash_session_token(token) == hash_session_token(token)
    assert hash_session_token(token) != hash_session_token(generate_session_token())
