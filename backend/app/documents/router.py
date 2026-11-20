from fastapi import APIRouter, status

from app.db.session import SessionDep
from app.documents import service
from app.organizations.schemas import CompanyRegisterRequest, CompanyRegisterResponse

router = APIRouter(prefix="/documents", tags=["documents"])


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
