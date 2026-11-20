from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SignupRequest(BaseModel):
    invite_code: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=50)

    @field_validator("invite_code")
    @classmethod
    # 초대코드는 대문자로만 생성되므로 소문자 및 공백으로 입력해도 여기서 맞춤
    def normalize_invite_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("invite_code")
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
