from fastapi import APIRouter, status

from app.auth.dependencies import CurrentUser
from app.db.session import SessionDep
from app.organizations import service
from app.organizations.schemas import (
    CompanyRegisterRequest,
    CompanyRegisterResponse,
    CompanyResponse,
    CompanyUsersResponse,
    CompanyVerificationRequest,
    DepartmentCreateRequest,
    DepartmentResponse,
)

router = APIRouter(prefix="/companies", tags=["companies"])


# 회사 첫 등록 인증번호 발송: 회사명과 회사 메일을 받아 전송
@router.post("/email-verifications", status_code=status.HTTP_204_NO_CONTENT)
async def send_company_verification(body: CompanyVerificationRequest, db: SessionDep):
    await service.send_company_verification(db, body.company_name, body.email)


# 회사 등록: 메일 인증을 마친 사람을 ADMIN으로 회사 생성
@router.post(
    "",
    response_model=CompanyRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_company(body: CompanyRegisterRequest, db: SessionDep):
    company, user = await service.register_company(
        db, body.verification_token, body.name, body.password
    )
    return CompanyRegisterResponse(
        company_id=company.company_id,
        company_name=company.name,
        user_id=user.user_id,
        email=user.email,
        name=user.name,
    )


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
