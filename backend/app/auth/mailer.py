import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)


# 인증번호 메일 발송 (MAIL_ENABLED=false면 서버 콘솔에 출력)
async def send_verification_code(email: str, code: str, expire_minutes: int) -> None:
    if not settings.MAIL_ENABLED:
        logger.warning("[개발용 메일] %s 인증번호: %s", email, code)
        return

    message = EmailMessage()
    message["From"] = settings.MAIL_FROM or settings.SMTP_USERNAME
    message["To"] = email
    message["Subject"] = "[회사 공용 브레인] 이메일 인증번호"
    message.set_content(
        f"인증번호: {code}\n\n{expire_minutes}분 안에 입력해 주세요.\n"
        "본인이 요청하지 않았다면 이 메일을 무시해 주세요."
    )

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
            timeout=10,
        )
    except (aiosmtplib.SMTPException, OSError):
        raise ServiceUnavailableError(
            "인증 메일을 보낼 수 없습니다. 잠시 후 다시 시도해 주세요."
        ) from None
