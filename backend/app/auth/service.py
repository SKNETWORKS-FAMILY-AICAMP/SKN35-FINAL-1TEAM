import secrets

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, UnauthorizedError
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.organizations import repository as user_repo
from app.organizations.models import Company, User, UserLevel


# 이메일·비밀번호로 사용자 인증, 실패 시 401
async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await user_repo.get_active_user_by_email(db, email)

    if user is None:
        # 없는 이메일이어도 해시 검증을 한 번 돌려 응답 시간으로 계정 존재를 알 수 없게 함
        verify_password(password, DUMMY_HASH)
        raise UnauthorizedError("이메일 또는 비밀번호가 올바르지 않습니다.")

    if not verify_password(password, user.password_hash):
        raise UnauthorizedError("이메일 또는 비밀번호가 올바르지 않습니다.")

    return user


# 인증 후 access·refresh 토큰 생성, refresh 해시는 DB에 저장
async def login(db: AsyncSession, email: str, password: str) -> tuple[str, str]:
    """(access_token, refresh_token) 반환. refresh는 해시만 DB에 저장."""
    user = await authenticate(db, email, password)

    access_token = create_access_token(user.user_id)
    refresh_token = create_refresh_token(user.user_id)

    # 컬럼이 하나라 새로 로그인하면 이전 기기의 refresh는 무효가 됨
    await user_repo.update_refresh_token(db, user, hash_token(refresh_token))

    return access_token, refresh_token


# refresh 토큰의 서명·만료·DB 해시 일치를 확인하고 토큰 주인 반환
async def _get_user_by_refresh_token(db: AsyncSession, refresh_token: str) -> User:
    """refresh token 검증 후 반환. 실패하면 401"""

    try:
        user_id = decode_token(refresh_token, "refresh")
    except jwt.InvalidTokenError:
        raise UnauthorizedError("다시 로그인 해주세요.") from None

    user = await user_repo.get_active_user_by_id(db, user_id)

    if user is None or user.refresh_token is None:
        raise UnauthorizedError("다시 로그인 해주세요.")

    if not secrets.compare_digest(user.refresh_token, hash_token(refresh_token)):
        raise UnauthorizedError("다시 로그인 해주세요.")

    return user


# refresh 토큰으로 새 access·refresh 토큰 발급 (rotation)
async def refresh(db: AsyncSession, refresh_token: str | None) -> tuple[str, str]:
    """새 (access_token, refresh_token) 반환. refresh도 매번 새로 바꿈(rotation)"""

    if refresh_token is None:
        raise UnauthorizedError("로그인이 필요합니다.")

    user = await _get_user_by_refresh_token(db, refresh_token)

    access_token = create_access_token(user.user_id)
    new_refresh_token = create_refresh_token(user.user_id)

    await user_repo.update_refresh_token(db, user, hash_token(new_refresh_token))

    return access_token, new_refresh_token


# DB의 refresh 해시를 지워 로그아웃 처리, 토큰이 이상해도 에러 없이 종료
async def logout(db: AsyncSession, refresh_token: str | None) -> None:
    """DB의 refresh 해쉬를 지움. 토큰이 없거나 이상해도 에러 없이 끝남"""

    if refresh_token is None:
        return

    try:
        user = await _get_user_by_refresh_token(db, refresh_token)
    except UnauthorizedError:
        return

    await user_repo.update_refresh_token(db, user, None)


# 초대 코드로 회사를 찾아 그 회사의 LIMITED 권한 직원으로 가입
async def signup(
    db: AsyncSession, invite_code: str, email: str, password: str, name: str
) -> tuple[User, Company]:
    company = await user_repo.get_company_by_invite_code(db, invite_code)

    if company is None:
        raise AppError("유요하지 않은 초대 코드입니다.")

    if await user_repo.email_exists(db, email):
        raise ConflictError("이미 가입된 이메일입니다.")

    try:
        user = await user_repo.create_user(
            db,
            company_id=company.company_id,
            name=name,
            email=email,
            password_hash=hash_password(password),
            user_type=UserLevel.LIMITED,
        )

    except IntegrityError:
        raise ConflictError("이미 가입된 이메일입니다.") from None

    return user, company
