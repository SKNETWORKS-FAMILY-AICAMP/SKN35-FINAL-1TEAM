from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service as auth_service
from app.core.enums import VerificationPurpose
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.organizations import repository as org_repo
from app.organizations.models import Company, Department, User, UserLevel


# 회사 첫 등록: 도메인 중복을 확인하고 회사명과 함께 인증번호 발송
async def send_company_verification(
    db: AsyncSession, company_name: str, email: str
) -> None:
    email_domain = auth_service.get_email_domain(email)

    if await org_repo.get_company_by_email_domain(db, email_domain):
        raise ConflictError("이미 등록된 회사입니다. 직원 회원가입을 이용해 주세요.")

    await auth_service.send_email_verification(
        db, email, VerificationPurpose.COMPANY_REGISTER, company_name
    )


# 회사 등록 전체 흐름: 메일 인증 확인 → 도메인 중복 확인 → 회사·ADMIN 계정 생성
async def register_company(
    db: AsyncSession,
    verification_token: str,
    name: str,
    password: str,
) -> tuple[Company, User]:
    email, company_name = auth_service.get_verified_email(
        verification_token, VerificationPurpose.COMPANY_REGISTER
    )
    email_domain = auth_service.get_email_domain(email)

    if await org_repo.get_company_by_email_domain(db, email_domain):
        raise ConflictError("이미 등록된 회사입니다.")

    if await org_repo.email_exists(db, email):
        raise ConflictError("이미 가입된 이메일입니다.")

    try:
        company = await org_repo.create_company(db, company_name, email_domain)
        user = await org_repo.create_user(
            db,
            company_id=company.company_id,
            name=name,
            email=email,
            password_hash=hash_password(password),
            user_type=UserLevel.ADMIN,
        )
    except IntegrityError:
        # 같은 도메인으로 동시에 두 요청이 들어온 경우 UNIQUE 제약에서 걸림
        raise ConflictError("이미 등록된 회사입니다.") from None

    return company, user


# 내 회사 조회
async def get_my_company(db: AsyncSession, current_user: User) -> Company:
    if current_user.company_id is None:
        raise NotFoundError("소속 회사를 찾을 수 없습니다.")

    company = await org_repo.get_company_by_id(db, current_user.company_id)

    if company is None:
        raise NotFoundError("소속 회사를 찾을 수 없습니다.")

    return company


# 내 회사의 재직 직원 목록 조회
async def get_company_users(db: AsyncSession, current_user: User) -> list[User]:
    if current_user.company_id is None:
        raise NotFoundError("소속 회사를 찾을 수 없습니다.")

    return await org_repo.get_active_company_users(db, current_user.company_id)


# 회사 내의 부서 생성
async def create_department(
    db: AsyncSession, current_user: User, name: str, description: str
) -> Department:
    if current_user.user_type != UserLevel.ADMIN:
        raise ForbiddenError("부서 생성 권한이 없습니다.")

    if current_user.company_id is None:
        raise NotFoundError("소속 회사를 찾을 수 없습니다.")

    company = await org_repo.get_company_for_update(db, current_user.company_id)

    if company is None:
        raise NotFoundError("소속 회사를 찾을 수 없습니다.")

    if await org_repo.department_name_exists(db, company.company_id, name):
        raise ConflictError("이미 존재하는 부서입니다.")

    return await org_repo.create_department(db, company.company_id, name, description)
