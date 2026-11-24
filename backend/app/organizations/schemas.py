from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.organizations.models import UserLevel


# 회사 첫 등록 인증번호 발송 api request
class CompanyVerificationRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=50)
    email: EmailStr

    @field_validator("company_name")
    @classmethod
    def strip_company_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("회사 이름을 입력해 주세요.")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()


# 회사 등록 api request: 메일 인증을 마친 사람이 회사와 ADMIN 계정을 만듦
class CompanyRegisterRequest(BaseModel):
    verification_token: str
    name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("이름을 입력해주세요.")
        return v


# 회사 등록 api response
class CompanyRegisterResponse(BaseModel):
    company_id: int
    company_name: str
    user_id: int
    email: str
    name: str


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
