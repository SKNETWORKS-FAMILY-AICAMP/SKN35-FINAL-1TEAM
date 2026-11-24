from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import YN
from app.organizations.models import Company, Department, User, UserLevel


# 삭제되지 않은 사용자를 이메일로 조회
async def get_active_user_by_email(db: AsyncSession, email: str) -> User | None:
    """삭제되지 않은 사용자를 이메일로 조회."""
    return await db.scalar(
        select(User).where(User.email == email, User.is_deleted == YN.N)
    )


# 사용자의 refresh 토큰 해시 저장 (None이면 삭제)
async def update_refresh_token(
    db: AsyncSession, user: User, refresh_token_hash: str | None
) -> None:
    """refresh 토큰 해시 저장. None이면 지움(로그아웃). commit은 get_db가 함."""
    user.refresh_token = refresh_token_hash
    await db.flush()


# 해당 이메일의 사용자가 있는지 확인 (삭제된 사용자 포함)
async def email_exists(db: AsyncSession, email: str) -> bool:
    """삭제된 사용자도 포함. email 컬럼이 UNIQUE라서."""
    return await db.scalar(select(exists().where(User.email == email)))


# 회사 행 생성 후 company_id를 받아 반환
async def create_company(db: AsyncSession, name: str, email_domain: str) -> Company:
    company = Company(name=name, email_domain=email_domain)
    db.add(company)
    await db.flush()  # company_id를 받아오기 위해
    return company


# 사용자 행 생성 후 반환
async def create_user(
    db: AsyncSession,
    *,
    company_id: int,
    dept_id: int | None = None,
    name: str,
    email: str,
    password_hash: str,
    user_type: UserLevel,
) -> User:
    user = User(
        company_id=company_id,
        dept_id=dept_id,
        name=name,
        email=email,
        password_hash=password_hash,
        user_type=user_type,
    )
    db.add(user)
    await db.flush()
    return user


# 삭제되지 않은 사용자를 id로 조회
async def get_active_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """삭제되지 않은 사용자를 id로 조회."""
    return await db.scalar(
        select(User).where(User.user_id == user_id, User.is_deleted == YN.N)
    )


# 삭제되지 않은 사용자들을 id 목록으로 조회
async def get_active_users_by_ids(db: AsyncSession, user_ids: list[int]) -> list[User]:
    result = await db.scalars(
        select(User).where(User.user_id.in_(user_ids), User.is_deleted == YN.N)
    )
    return list(result)


# 회사 id로 회사 조회
async def get_company_by_id(db: AsyncSession, company_id: int) -> Company | None:
    return await db.scalar(select(Company).where(Company.company_id == company_id))


# 회사의 재직 직원 목록 조회
async def get_active_company_users(db: AsyncSession, company_id: int) -> list[User]:
    result = await db.scalars(
        select(User)
        .where(
            User.company_id == company_id,
            User.is_deleted == YN.N,
        )
        .order_by(User.name, User.user_id)
    )
    return list(result)


# 메일 도메인으로 회사 조회
async def get_company_by_email_domain(
    db: AsyncSession, email_domain: str
) -> Company | None:
    return await db.scalar(select(Company).where(Company.email_domain == email_domain))


# 회사의 부서 목록 조회
async def get_company_departments(
    db: AsyncSession, company_id: int
) -> list[Department]:
    result = await db.scalars(
        select(Department)
        .where(Department.company_id == company_id)
        .order_by(Department.name, Department.dept_id)
    )
    return list(result)


# 해당 회사에 속한 부서 조회
async def get_company_department(
    db: AsyncSession, company_id: int, dept_id: int
) -> Department | None:
    return await db.scalar(
        select(Department).where(
            Department.dept_id == dept_id, Department.company_id == company_id
        )
    )


# 회사 행을 잠구고 조회(같은 회사의 생성 요청을 순서대로 처리)
async def get_company_for_update(db: AsyncSession, company_id: int) -> Company | None:
    return await db.scalar(
        select(Company).where(Company.company_id == company_id).with_for_update()
    )


# 회사의 같은 이름의 부서가 있는지 확인
async def department_name_exists(db: AsyncSession, company_id: int, name: str) -> bool:
    return await db.scalar(
        select(
            exists().where(Department.company_id == company_id, Department.name == name)
        )
    )


# 부서 행 생서 후 반환
async def create_department(
    db: AsyncSession, company_id: int, name: str, description: str
) -> Department:
    department = Department(company_id=company_id, name=name, description=description)
    db.add(department)

    await db.flush()

    return department
