from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.enums import VerificationPurpose
from app.organizations.models import UserLevel
from app.organizations.schemas import DepartmentResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# 직원 가입 인증번호 발송 api request
class EmailVerificationRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()


# 인증번호 확인 api request
class EmailVerificationConfirmRequest(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^[0-9]{6}$")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()


# 인증번호 확인 api response (purpose로 회원가입 화면을 구분, 직원 가입은 부서 목록 포함)
class EmailVerificationConfirmResponse(BaseModel):
    verification_token: str
    email: str
    purpose: VerificationPurpose
    company_name: str | None
    departments: list[DepartmentResponse]


class SignupRequest(BaseModel):
    verification_token: str
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=50)
    dept_id: int = Field(gt=0)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("이름을 입력해주세요.")

        return v


class SignupResponse(BaseModel):
    user_id: int
    email: str
    name: str
    company_name: str | None


# 로그인 사용자 정보 응답
class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    company_id: int | None
    dept_id: int | None
    name: str
    email: str
    user_type: UserLevel
