import hashlib
import hmac
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
def _create_token(
    subject: int | str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, str | None] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": secrets.token_hex(16),
        **(extra_claims or {}),
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


# 메일 인증 완료 토큰 생성 (용도와 회사 이름을 함께 담아 회원가입에 사용)
def create_email_verification_token(
    email: str, purpose: str, company_name: str | None
) -> str:
    return _create_token(
        email,
        "email_verification",
        timedelta(minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES),
        {"purpose": purpose, "company_name": company_name},
    )


# 토큰의 서명·만료·종류를 검증하고 payload 반환
def _decode_payload(token: str, expected_type: str) -> dict:
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub"]},
    )

    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("토큰 종류가 올바르지 않습니다.")
    return payload


# 토큰의 서명·만료·종류를 검증하고 user_id 반환
def decode_token(token: str, expected_type: str) -> int:
    return int(_decode_payload(token, expected_type)["sub"])


# 메일 인증 완료 토큰을 검증하고 (이메일, 용도, 회사 이름) 반환
def decode_email_verification_token(token: str) -> tuple[str, str | None, str | None]:
    payload = _decode_payload(token, "email_verification")
    return payload["sub"], payload.get("purpose"), payload.get("company_name")


# 토큰을 DB에 저장할 SHA-256 해시로 변환
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# 인증번호를 DB에 저장할 HMAC 해시로 변환 (6자리라 비밀키 없이는 대입할 수 없게 함)
def hash_verification_code(email: str, code: str) -> str:
    message = f"{email}:{code}".encode()
    return hmac.new(
        settings.JWT_SECRET_KEY.encode(), message, hashlib.sha256
    ).hexdigest()
