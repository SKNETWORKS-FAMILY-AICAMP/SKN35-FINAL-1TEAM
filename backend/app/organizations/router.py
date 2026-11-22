from fastapi import APIRouter, status

from app.auth.dependencies import CurrentUser
from app.db.session import SessionDep
from app.organizations import service
from app.organizations.schemas import (
    CompanyRegisterRequest,
    CompanyRegisterResponse,
    CompanyResponse,
    CompanyUsersResponse,
)

router = APIRouter(prefix="/companies", tags=["companies"])


# 회사 등록: 사업자번호 검증 후 회사 + ADMIN 계정 생성, 계정 정보는 이 응답에서만 제공
@router.post(
    "",
    response_model=CompanyRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_company(body: CompanyRegisterRequest, db: SessionDep):
    (
        company_id,
        invite_code,
        admin_email,
        admin_password,
    ) = await service.register_company(
        db, body.name, body.company_code, body.representative_name, body.start_date
    )
    return CompanyRegisterResponse(
        company_id=company_id,
        name=body.name,
        invite_code=invite_code,
        admin_email=admin_email,
        admin_password=admin_password,
    )


# 내 회사 조회: 초대 코드는 ADMIN에게만 제공
@router.get("", response_model=CompanyResponse)
async def get_my_company(db: SessionDep, current_user: CurrentUser):
    company, invite_code = await service.get_my_company(db, current_user)
    return CompanyResponse(
        company_id=company.company_id,
        name=company.name,
        invite_code=invite_code,
    )


# 내 회사 직원 목록 조회: 프로젝트 멤버 추가 시 대상 선택에 사용
@router.get("/users", response_model=CompanyUsersResponse)
async def get_company_users(db: SessionDep, current_user: CurrentUser):
    users = await service.get_company_users(db, current_user)
    return {"users": users}
