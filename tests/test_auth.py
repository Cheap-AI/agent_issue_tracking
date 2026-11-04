"""Unit tests for backend/core/auth.py token verification (no DB or network needed)."""
import time

import jwt
import pytest

from backend.core import auth

SECRET = "x" * 32


def _token(**overrides) -> str:
    claims = {"sub": "u1", "aud": "authenticated", "email": "a@b.c", "exp": int(time.time()) + 60}
    claims.update(overrides)
    return jwt.encode(claims, SECRET, algorithm="HS256")


def test_decode_valid_hs256_token(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    assert auth.decode_token(_token())["sub"] == "u1"


def test_decode_rejects_expired_token(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    with pytest.raises(jwt.PyJWTError):
        auth.decode_token(_token(exp=int(time.time()) - 10))


def test_decode_rejects_wrong_audience(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    with pytest.raises(jwt.PyJWTError):
        auth.decode_token(_token(aud="anon"))


def test_decode_rejects_bad_signature(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "y" * 32)
    with pytest.raises(jwt.PyJWTError):
        auth.decode_token(_token())
