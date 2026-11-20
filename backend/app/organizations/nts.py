import httpx

from app.core.config import settings
from app.core.exceptions import AppError, ServiceUnavailableError

NTS_VALIDATE_URL = "https://api.odcloud.kr/api/nts-businessman/v1/validate"
VALID_MATCH = "01"
STATUS_ACTIVE = "01"


# 국세청 진위확인 API로 사업자번호, 대표자명, 개업일자 일치 여부와 영업상태 확인
async def verify_business(
    company_code: str, representative_name: str, start_date: str
) -> None:
    if not settings.NTS_SERVICE_KEY:
        return

    body = {
        "businesses": [
            {"b_no": company_code, "start_dt": start_date, "p_nm": representative_name}
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(
                NTS_VALIDATE_URL,
                params={"serviceKey": settings.NTS_SERVICE_KEY},
                json=body,
            )

        res.raise_for_status()
        result = res.json()["data"][0]
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        raise ServiceUnavailableError(
            "사업자 정보 확인 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요."
        ) from None

    if result.get("valid") != VALID_MATCH:
        raise AppError("입력한 정보가 국세청에 등록된 사업자 정보와 일치하지 않습니다.")

    status_code = (result.get("status") or {}).get("b_stt_cd")

    if status_code != STATUS_ACTIVE:
        raise AppError("휴업 또는 폐업 상태인 사업자는 등록할 수 없습니다.")
