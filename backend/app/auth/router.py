from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status

from app.auth import service
from app.auth.schemas import (
    CompanyRegisterRequest,
    CompanyRegisterResponse,
    CompanyVerificationRequest,
    EmailVerificationConfirmRequest,
    EmailVerificationConfirmResponse,
    EmailVerificationRequest,
    LoginRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)
from app.core.config import settings
from app.db.redis import RedisDep
from app.db.session import SessionDep
from app.organizations import service as org_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)]


# refresh 토큰을 HttpOnly 쿠키로 응답에 심음 (login·refresh 공용)
def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    # refresh는 JS가 못 읽는 HttpOnly 쿠키로, 재발급·로그아웃 경로에만 실려 가게 함
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


# 회사 등록 인증번호 발송: 회사명과 회사 메일을 받아 전송
@router.post("/company-email-verifications", status_code=status.HTTP_204_NO_CONTENT)
async def send_company_verification(
    body: CompanyVerificationRequest, db: SessionDep, redis: RedisDep
):
    await org_service.send_company_verification(
        db, redis, body.company_name, body.email
    )


# 직원 가입 인증번호 발송: 메일 도메인으로 등록된 회사를 확인한 뒤 전송
@router.post("/email-verifications", status_code=status.HTTP_204_NO_CONTENT)
async def send_employee_verification(
    body: EmailVerificationRequest, db: SessionDep, redis: RedisDep
):
    await service.send_employee_verification(db, redis, body.email)


# 인증번호 확인: 맞으면 회원가입 화면에 필요한 인증 토큰과 정보 반환
@router.post(
    "/email-verifications/confirm", response_model=EmailVerificationConfirmResponse
)
async def confirm_email_verification(
    body: EmailVerificationConfirmRequest, db: SessionDep, redis: RedisDep
):
    return await service.confirm_email_verification(db, redis, body.email, body.code)


# 직원 회원가입: 인증된 메일 도메인의 회사에 LIMITED 권한으로 계정 생성
@router.post(
    "/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED
)
async def signup(body: SignupRequest, db: SessionDep):
    user, company = await service.signup(
        db, body.verification_token, body.password, body.name, body.dept_id
    )

    return SignupResponse(
        user_id=user.user_id,
        email=user.email,
        name=user.name,
        company_name=company.name,
    )


# 회사 등록 회원가입: 메일 인증을 마친 사람을 ADMIN으로 회사와 계정 생성
@router.post(
    "/company-signup",
    response_model=CompanyRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def company_signup(body: CompanyRegisterRequest, db: SessionDep):
    company, user = await org_service.register_company(
        db, body.verification_token, body.name, body.password
    )
    return CompanyRegisterResponse(
        company_id=company.company_id,
        company_name=company.name,
        user_id=user.user_id,
        email=user.email,
        name=user.name,
    )


# 로그인: 이메일·비밀번호 확인 후 access 토큰은 본문, refresh 토큰은 쿠키로 발급
@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: SessionDep):
    access_token, refresh_token = await service.login(db, body.email, body.password)

    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(access_token=access_token)


# 토큰 재발급: refresh 쿠키 검증 후 새 access 토큰 + 새 refresh 쿠키 발급
@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response, db: SessionDep, refresh_token: RefreshCookie = None
):
    access_token, new_refresh_token = await service.refresh(db, refresh_token)

    _set_refresh_cookie(response, new_refresh_token)

    return TokenResponse(access_token=access_token)


# 로그아웃: DB의 refresh 토큰 해시를 지우고 쿠키 삭제 (204, 본문 없음)
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response, db: SessionDep, refresh_token: RefreshCookie = None
):
    await service.logout(db, refresh_token)
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
