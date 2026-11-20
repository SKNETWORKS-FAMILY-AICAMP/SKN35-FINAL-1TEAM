import secrets
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError
from app.core.security import hash_password
from app.organizations import nts
from app.organizations import repository as org_repo
from app.organizations.models import UserLevel

# 사람이 읽고 입력하기 쉽게 헷갈리는 문자(0/O, 1/I/L) 제외
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
INVITE_CODE_LENGTH = 8
ADMIN_ID_LENGTH = 8
MAX_GENERATE_ATTEMPTS = 5

BIZ_NO_WEIGHTS = (1, 3, 7, 1, 3, 7, 1, 3, 5)


# 사업자등록번호 마지막 자리(체크섬) 검증
def is_valid_business_number(biz_no: str) -> bool:
    """사업자등록번호 체크섬 검증. 형식만 확인하며 실제 영업 중인지는 알 수 없음."""
    digits = [int(c) for c in biz_no]
    total = sum(d * w for d, w in zip(digits[:9], BIZ_NO_WEIGHTS))
    total += (digits[8] * 5) // 10
    return (10 - total % 10) % 10 == digits[9]


# 헷갈리는 문자를 뺀 알파벳으로 랜덤 코드 생성
def _random_code(length: int) -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


# DB에 없는 8자리 초대 코드 생성 (겹치면 재시도)
async def _generate_invite_code(db: AsyncSession) -> str:
    for _ in range(MAX_GENERATE_ATTEMPTS):
        code = _random_code(INVITE_CODE_LENGTH)
        if not await org_repo.invite_code_exists(db, code):
            return code
    raise AppError("초대 코드 생성에 실패했습니다. 다시 시도해 주세요.")


# DB에 없는 관리자 로그인용 이메일 생성 (겹치면 재시도)
async def _generate_admin_email(db: AsyncSession, company_code: str) -> str:
    # 로그인이 이메일 기준이라 관리자 ID도 이메일 형식으로 만듦
    for _ in range(MAX_GENERATE_ATTEMPTS):
        email = f"admin-{_random_code(ADMIN_ID_LENGTH).lower()}@c{company_code}.brain"
        if not await org_repo.email_exists(db, email):
            return email
    raise AppError("관리자 계정 생성에 실패했습니다. 다시 시도해 주세요.")


# 회사 등록 전체 흐름: 번호 검증 → 중복 확인 → 회사·ADMIN 계정 생성
async def register_company(
    db: AsyncSession,
    name: str,
    company_code: str,
    representative_name: str,
    start_date: date,
) -> tuple[int, str, str, str]:
    """회사 + ADMIN 계정 생성. (company_id, invite_code, admin_email, admin_password) 반환."""
    if not is_valid_business_number(company_code):
        raise AppError("유효하지 않은 사업자등록번호입니다.")

    if await org_repo.company_code_exists(db, company_code):
        raise ConflictError("이미 등록된 회사입니다.")

    await nts.verify_business(
        company_code, representative_name.strip(), start_date.strftime("%Y%m%d")
    )

    invite_code = await _generate_invite_code(db)
    admin_email = await _generate_admin_email(db, company_code)
    admin_password = secrets.token_urlsafe(12)

    try:
        company = await org_repo.create_company(db, company_code, name, invite_code)
        await org_repo.create_user(
            db,
            company_id=company.company_id,
            name=f"{name} 관리자",
            email=admin_email,
            password_hash=hash_password(admin_password),
            user_type=UserLevel.ADMIN,
        )
    except IntegrityError:
        # 같은 사업자번호로 동시에 두 요청이 들어온 경우 UNIQUE 제약에서 걸림
        raise ConflictError("이미 등록된 회사입니다.") from None

    return company.company_id, invite_code, admin_email, admin_password
