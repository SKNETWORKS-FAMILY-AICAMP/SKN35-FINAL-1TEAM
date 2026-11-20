import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import YN
from app.db.base import Base


class UserLevel(str, enum.Enum):
    LIMITED = "LIMITED"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class Company(Base):
    __tablename__ = "company"

    company_id: Mapped[int] = mapped_column(primary_key=True)
    company_code: Mapped[str] = mapped_column(String(10), unique=True)  # 사업자등록번호
    name: Mapped[str | None] = mapped_column(String(50))
    invite_code: Mapped[str] = mapped_column(String(16), unique=True)


class Department(Base):
    __tablename__ = "department"

    dept_id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("company.company_id"))
    name: Mapped[str | None] = mapped_column(String(50))


class User(Base):
    __tablename__ = "user"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("company.company_id"))
    dept_id: Mapped[int | None] = mapped_column(ForeignKey("department.dept_id"))
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    refresh_token: Mapped[str | None] = mapped_column(String(255))
    user_type: Mapped[UserLevel] = mapped_column(
        Enum(UserLevel, name="user_level"),
        default=UserLevel.LIMITED,
        server_default=UserLevel.LIMITED.value,
    )
    is_deleted: Mapped[YN] = mapped_column(
        Enum(YN, name="yn"), default=YN.N, server_default=YN.N.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
