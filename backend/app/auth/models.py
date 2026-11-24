from datetime import datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import VerificationPurpose
from app.db.base import Base


class EmailVerification(Base):
    __tablename__ = "email_verification"

    email_verification_id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    purpose: Mapped[VerificationPurpose] = mapped_column(
        Enum(VerificationPurpose, name="verification_purpose")
    )
    company_name: Mapped[str | None] = mapped_column(String(50))  # 회사 첫 등록 때만
    code_hash: Mapped[str] = mapped_column(String(64))
    attempt_count: Mapped[int] = mapped_column(default=0, server_default="0")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
