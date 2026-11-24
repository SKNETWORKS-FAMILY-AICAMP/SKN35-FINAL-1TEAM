from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import EmailVerification
from app.core.enums import VerificationPurpose


# 이메일의 인증번호 행을 잠그고 조회 (시도 횟수를 정확히 세기 위해)
async def get_email_verification_for_update(
    db: AsyncSession, email: str
) -> EmailVerification | None:
    return await db.scalar(
        select(EmailVerification)
        .where(EmailVerification.email == email)
        .with_for_update()
    )


# 인증번호 행 생성 또는 새 번호로 교체
async def save_email_verification(
    db: AsyncSession,
    verification: EmailVerification | None,
    *,
    email: str,
    purpose: VerificationPurpose,
    company_name: str | None,
    code_hash: str,
    expires_at: datetime,
    last_sent_at: datetime,
) -> EmailVerification:
    if verification is None:
        verification = EmailVerification(email=email)
        db.add(verification)

    verification.purpose = purpose
    verification.company_name = company_name
    verification.code_hash = code_hash
    verification.attempt_count = 0
    verification.expires_at = expires_at
    verification.last_sent_at = last_sent_at
    await db.flush()
    return verification


# 사용이 끝난 인증번호 행 삭제
async def delete_email_verification(
    db: AsyncSession, verification: EmailVerification
) -> None:
    await db.delete(verification)
    await db.flush()
