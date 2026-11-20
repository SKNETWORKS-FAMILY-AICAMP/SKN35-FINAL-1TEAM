import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummy-password")


# 비밀번호를 argon2 해시로 변환
def hash_password(password: str) -> str:
    return password_hash.hash(password)


# 입력 비밀번호와 저장된 해시가 일치하는지 확인
def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


# JWT 공통 생성 (sub·type·iat·exp·jti 포함)
def _create_token(user_id: int, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": secrets.token_hex(16),
    }

    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


# access 토큰 생성 (30분)
def create_access_token(user_id: int) -> str:
    return _create_token(
        user_id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


# refresh 토큰 생성 (14일)
def create_refresh_token(user_id: int) -> str:
    return _create_token(
        user_id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


# 토큰의 서명·만료·종류를 검증하고 user_id 반환
def decode_token(token: str, expected_type: str) -> int:
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub"]},
    )

    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("토큰 종류가 올바르지 않습니다.")
    return int(payload["sub"])


# 토큰을 DB에 저장할 SHA-256 해시로 변환
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
