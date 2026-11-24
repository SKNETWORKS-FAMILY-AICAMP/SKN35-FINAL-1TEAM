from fastapi import APIRouter, status

from app.auth.dependencies import CurrentUser
from app.db.session import SessionDep
from app.organizations import service
from app.organizations.schemas import (
    CompanyResponse,
    CompanyUsersResponse,
    DepartmentCreateRequest,
    DepartmentListResponse,
    DepartmentResponse,
)

router = APIRouter(prefix="/companies", tags=["companies"])


# 내 회사 조회
@router.get("", response_model=CompanyResponse)
async def get_my_company(db: SessionDep, current_user: CurrentUser):
    return await service.get_my_company(db, current_user)


# 내 회사 직원 목록 조회: 프로젝트 멤버 추가 시 대상 선택에 사용
@router.get("/users", response_model=CompanyUsersResponse)
async def get_company_users(db: SessionDep, current_user: CurrentUser):
    users = await service.get_company_users(db, current_user)
    return {"users": users}


@router.post(
    "/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    body: DepartmentCreateRequest, db: SessionDep, current_user: CurrentUser
):
    return await service.create_department(
        db, current_user, body.name, body.description
    )


# 내 회사 부서 목록 조회
@router.get("/departments", response_model=DepartmentListResponse)
async def get_departments(db: SessionDep, current_user: CurrentUser):
    departments = await service.get_company_departments(db, current_user)
    return {"departments": departments}
