from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.organizations.models import UserLevel


# 내 회사 조회 응답
class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    name: str | None
    email_domain: str


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


# 부서 생성 api request
class DepartmentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()

        if not v:
            raise ValueError("부서 이름을 입력해주세요.")

        return v

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: str) -> str:
        v = v.strip()

        if not v:
            raise ValueError("부서 설명을 입력해주세요.")

        return v


# 부서 생성 api response
class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dept_id: int
    name: str
    description: str | None


class DepartmentListResponse(BaseModel):
    departments: list[DepartmentResponse]
