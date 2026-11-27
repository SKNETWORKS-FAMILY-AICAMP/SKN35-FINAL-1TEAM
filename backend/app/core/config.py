from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # 쿠키 및 CORS 관련

    # 로컬 개발에 경우 True이면 refresh 쿠키가 안실려감 배포 후 True로 변경 예정
    COOKIE_SECURE: bool = False
    # 프론트엔드 주소와 백엔드 서버 주소 불일치로 인해 다른 사이트 취급 허용 사이트 명시
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # 메일 인증 (MAIL_ENABLED=false면 인증번호를 서버 콘솔에 출력)
    MAIL_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    MAIL_FROM: str = ""
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 30
    # 개발·시연 때 공용 메일 차단에서 제외할 도메인
    ALLOWED_EMAIL_DOMAINS: list[str] = []

    @property
    def DATABASE_URL(self) -> str:
        password = quote_plus(self.POSTGRES_PASSWORD)

        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
