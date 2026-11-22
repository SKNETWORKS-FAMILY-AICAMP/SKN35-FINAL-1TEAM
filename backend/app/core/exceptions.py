from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """service에서 raise하는 공통 에러. main의 핸들러가 HTTP 응답으로 바꾼다."""

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "잘못된 요청입니다."

    def __init__(self, detail: str | None = None):
        if detail is not None:
            self.detail = detail


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "인증에 실패했습니다."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    detail = "이미 존재하는 데이터입니다."


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "외부 서비스에 연결할 수 없습니다."


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    headers = (
        {"WWW-Authenticate": "Bearer"}
        if exc.status_code == status.HTTP_401_UNAUTHORIZED
        else None
    )
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail}, headers=headers
    )
