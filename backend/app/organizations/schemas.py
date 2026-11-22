from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.organizations.models import UserLevel


class CompanyRegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    company_code: str = Field(description="사업자등록번호 10자리 (하이픈 허용)")
    representative_name: str = Field(min_length=1, max_length=30)
    start_date: date = Field(description="개업일자 (YYYY-MM-DD)")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("회사 이름을 입력해 주세요.")
        return v

    @field_validator("company_code")
    @classmethod
    def normalize_company_code(cls, v: str) -> str:
        # 123-45-67890 처럼 들어와도 숫자 10자리로 맞춤
        v = v.replace("-", "").strip()
        if len(v) != 10 or not v.isdigit():
            raise ValueError("사업자등록번호는 숫자 10자리여야 합니다.")
        return v

    @field_validator("start_date")
    @classmethod
    def not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("개업일자는 오늘 이후일 수 없습니다.")

        return v


class CompanyRegisterResponse(BaseModel):
    """관리자 계정 정보는 이 응답에서 한 번만 보여 줌. 다시 조회할 방법 없음."""

    company_id: int
    name: str
    invite_code: str
    admin_email: str
    admin_password: str


# 내 회사 조회 응답 (초대 코드는 ADMIN에게만 제공)
class CompanyResponse(BaseModel):
    company_id: int
    name: str | None
    invite_code: str | None


# 회사 직원 1명 응답
class CompanyUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    dept_id: int | None
    name: str
    email: str
    user_type: UserLevel


# 회사 직원 목록 응답
class CompanyUsersResponse(BaseModel):
    users: list[CompanyUserResponse]
