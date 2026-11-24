import secrets
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import mailer
from app.auth import repository as auth_repo
from app.auth.schemas import EmailVerificationConfirmResponse
from app.core.config import settings
from app.core.enums import VerificationPurpose
from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    create_email_verification_token,
    create_refresh_token,
    decode_email_verification_token,
    decode_token,
    hash_password,
    hash_token,
    hash_verification_code,
    verify_password,
)
from app.organizations import repository as user_repo
from app.organizations.models import Company, User, UserLevel
from app.organizations.schemas import DepartmentResponse

VERIFICATION_CODE_EXPIRE_MINUTES = 10
VERIFICATION_RESEND_SECONDS = 60
MAX_VERIFICATION_ATTEMPTS = 5

# 회사 메일이 아닌 공용 메일 도메인
PUBLIC_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "naver.com",
    "daum.net",
    "hanmail.net",
    "kakao.com",
    "nate.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "yahoo.com",
    "icloud.com",
    "me.com",
    "proton.me",
    "protonmail.com",
}


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


# 이메일에서 도메인 추출
def get_email_domain(email: str) -> str:
    return email.rsplit("@", 1)[1].lower()


# 메일 인증 토큰의 용도까지 검증하고 (이메일, 회사 이름) 반환
def get_verified_email(
    verification_token: str, purpose: VerificationPurpose
) -> tuple[str, str | None]:
    try:
        email, token_purpose, company_name = decode_email_verification_token(
            verification_token
        )
    except jwt.InvalidTokenError:
        raise AppError("메일 인증이 만료되었습니다. 다시 인증해 주세요.") from None

    if token_purpose != purpose.value:
        raise AppError("메일 인증이 만료되었습니다. 다시 인증해 주세요.")

    return email, company_name


# 회사 메일 확인 후 6자리 인증번호 발송 (회사 등록·직원 가입 공용)
async def send_email_verification(
    db: AsyncSession,
    email: str,
    purpose: VerificationPurpose,
    company_name: str | None = None,
) -> None:
    email_domain = get_email_domain(email)
    allowed_domains = {domain.lower() for domain in settings.ALLOWED_EMAIL_DOMAINS}

    if email_domain in PUBLIC_EMAIL_DOMAINS and email_domain not in allowed_domains:
        raise AppError("회사 메일로만 가입할 수 있습니다.")

    if await user_repo.email_exists(db, email):
        raise ConflictError("이미 가입된 이메일입니다.")

    verification = await auth_repo.get_email_verification_for_update(db, email)
    now = datetime.now(UTC)

    if verification is not None and now < verification.last_sent_at + timedelta(
        seconds=VERIFICATION_RESEND_SECONDS
    ):
        raise AppError("인증번호는 60초 후에 다시 요청할 수 있습니다.")

    code = f"{secrets.randbelow(1_000_000):06d}"

    try:
        await auth_repo.save_email_verification(
            db,
            verification,
            email=email,
            purpose=purpose,
            company_name=company_name,
            code_hash=hash_verification_code(email, code),
            expires_at=now + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES),
            last_sent_at=now,
        )
    except IntegrityError:
        # 같은 이메일로 동시에 첫 요청이 들어온 경우 UNIQUE 제약에서 걸림
        raise AppError("인증번호는 60초 후에 다시 요청할 수 있습니다.") from None

    # 발송에 실패하면 get_db가 rollback해서 재발송 대기시간이 남지 않음
    await mailer.send_verification_code(email, code, VERIFICATION_CODE_EXPIRE_MINUTES)


# 직원 가입: 메일 도메인의 회사와 부서를 확인한 뒤 인증번호 발송
async def send_employee_verification(db: AsyncSession, email: str) -> None:
    company = await user_repo.get_company_by_email_domain(db, get_email_domain(email))

    if company is None:
        raise NotFoundError("등록되지 않은 회사입니다. 회사 메일을 확인해 주세요.")

    if not await user_repo.get_company_departments(db, company.company_id):
        raise AppError("등록된 부서가 없습니다. 회사 관리자에게 문의해 주세요.")

    await send_email_verification(db, email, VerificationPurpose.EMPLOYEE_SIGNUP)


# 인증번호 확인 후 회원가입 화면에 필요한 인증 토큰과 정보 반환
async def confirm_email_verification(
    db: AsyncSession, email: str, code: str
) -> EmailVerificationConfirmResponse:
    verification = await auth_repo.get_email_verification_for_update(db, email)

    if (
        verification is None
        or verification.expires_at <= datetime.now(UTC)
        or verification.attempt_count >= MAX_VERIFICATION_ATTEMPTS
    ):
        raise AppError("인증번호가 올바르지 않거나 만료되었습니다.")

    if not secrets.compare_digest(
        verification.code_hash, hash_verification_code(email, code)
    ):
        verification.attempt_count += 1
        # 에러를 던지면 get_db가 rollback하므로 틀린 횟수는 여기서 먼저 저장
        await db.commit()
        raise AppError("인증번호가 올바르지 않거나 만료되었습니다.")

    purpose = verification.purpose
    company_name = verification.company_name
    departments = []

    if purpose == VerificationPurpose.EMPLOYEE_SIGNUP:
        company = await user_repo.get_company_by_email_domain(
            db, get_email_domain(email)
        )

        if company is None:
            raise NotFoundError("등록되지 않은 회사입니다. 회사 메일을 확인해 주세요.")

        company_name = company.name
        departments = await user_repo.get_company_departments(db, company.company_id)

    await auth_repo.delete_email_verification(db, verification)

    return EmailVerificationConfirmResponse(
        verification_token=create_email_verification_token(
            email, purpose.value, company_name
        ),
        email=email,
        purpose=purpose,
        company_name=company_name,
        departments=[
            DepartmentResponse.model_validate(department) for department in departments
        ],
    )


# 직원 회원가입: 인증된 메일 도메인의 회사에 LIMITED 권한으로 계정 생성
async def signup(
    db: AsyncSession, verification_token: str, password: str, name: str, dept_id: int
) -> tuple[User, Company]:
    email, _ = get_verified_email(
        verification_token, VerificationPurpose.EMPLOYEE_SIGNUP
    )
    company = await user_repo.get_company_by_email_domain(db, get_email_domain(email))

    if company is None:
        raise NotFoundError("등록되지 않은 회사입니다. 회사 메일을 확인해 주세요.")

    if await user_repo.get_company_department(db, company.company_id, dept_id) is None:
        raise NotFoundError("부서를 찾을 수 없습니다.")

    if await user_repo.email_exists(db, email):
        raise ConflictError("이미 가입된 이메일입니다.")

    try:
        user = await user_repo.create_user(
            db,
            company_id=company.company_id,
            dept_id=dept_id,
            name=name,
            email=email,
            password_hash=hash_password(password),
            user_type=UserLevel.LIMITED,
        )

    except IntegrityError:
        raise ConflictError("이미 가입된 이메일입니다.") from None

    return user, company
