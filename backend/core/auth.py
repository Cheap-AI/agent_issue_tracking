"""Supabase Auth JWT verification + role lookup for FastAPI.

The frontend logs in via Supabase and sends the access token as `Authorization: Bearer <jwt>`.
We verify it here, then load (or lazily create) the matching row in `profiles`, which is where
the app-level role lives. Roles are 'admin' and 'member'; use `require_role("admin")` to gate routes.

Env:
- SUPABASE_URL: project URL, e.g. https://abcd.supabase.co (used for the JWKS endpoint + issuer check)
- SUPABASE_JWT_SECRET: only for legacy projects that still sign with the shared HS256 secret
- ADMIN_EMAILS: comma-separated emails that get role 'admin' when their profile is first created
"""
import os
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy.exc import IntegrityError

from backend.core.db import get_session
from backend.models.db_models import Profile

ROLES = ("admin", "member")

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None
    role: str


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL is not set")
    return PyJWKClient(f"{supabase_url}/auth/v1/.well-known/jwks.json")


def decode_token(token: str) -> dict:
    """Verify a Supabase access token and return its claims. Raises jwt.PyJWTError if invalid."""
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        secret = os.environ.get("SUPABASE_JWT_SECRET")
        if not secret:
            raise jwt.InvalidTokenError("HS256 token but SUPABASE_JWT_SECRET is not set")
        key: object = secret
    else:
        key = _jwks_client().get_signing_key_from_jwt(token).key
    return jwt.decode(token, key, algorithms=[alg], audience="authenticated")


def _admin_emails() -> set[str]:
    return {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}


def _load_or_create_profile(user_id: str, email: str | None) -> CurrentUser:
    with get_session() as db:
        profile = db.get(Profile, user_id)
        if profile is None:
            role = "admin" if email and email.lower() in _admin_emails() else "member"
            profile = Profile(id=user_id, email=email, role=role)
            db.add(profile)
            try:
                db.flush()
            except IntegrityError:  # concurrent first requests raced to create it
                db.rollback()
                profile = db.get(Profile, user_id)
        return CurrentUser(id=str(profile.id), email=profile.email, role=profile.role)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    """FastAPI dependency: require a valid Supabase session and return the user with their role."""
    if credentials is None:
        raise _unauthorized()
    try:
        claims = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _unauthorized("Invalid or expired token")
    user_id = claims.get("sub")
    if not user_id:
        raise _unauthorized("Invalid token")
    return _load_or_create_profile(user_id, claims.get("email"))


def require_role(*allowed: str):
    """Dependency factory: `Depends(require_role("admin"))` rejects users without one of these roles."""
    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _check
