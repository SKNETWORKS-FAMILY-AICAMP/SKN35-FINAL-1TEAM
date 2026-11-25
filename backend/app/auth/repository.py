from redis.asyncio import Redis

from app.core.enums import VerificationPurpose

# 존재 확인 → 시도 횟수 증가 → 비교 → 성공 시 삭제를 한 번에 처리
# (나눠서 호출하면 동시 요청 두 개가 모두 성공하거나, 만료 직후 HINCRBY가 TTL 없는 키를 만들 수 있음)
_CONSUME_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 0 then return {'missing'} end
local attempts = redis.call('HINCRBY', KEYS[1], 'attempts', 1)
if attempts > tonumber(ARGV[2]) then return {'locked'} end
if redis.call('HGET', KEYS[1], 'code_hash') ~= ARGV[1] then return {'wrong'} end
local purpose = redis.call('HGET', KEYS[1], 'purpose')
local company_name = redis.call('HGET', KEYS[1], 'company_name') or ''
redis.call('DEL', KEYS[1])
return {'ok', purpose, company_name}
"""


def _code_key(email: str) -> str:
    return f"email_verif:code:{email}"


def _cooldown_key(email: str) -> str:
    return f"email_verif:cooldown:{email}"


# 재발송 대기시간 시작, 이미 대기 중이면 False
async def acquire_resend_cooldown(redis: Redis, email: str, seconds: int) -> bool:
    return bool(await redis.set(_cooldown_key(email), "1", nx=True, ex=seconds))


# 메일 발송 실패 시 바로 다시 요청할 수 있도록 대기시간 해제
async def release_resend_cooldown(redis: Redis, email: str) -> None:
    await redis.delete(_cooldown_key(email))


# 인증번호 저장, 기존 번호가 있으면 새 번호로 교체 (시도 횟수도 0부터)
async def save_email_verification(
    redis: Redis,
    *,
    email: str,
    purpose: VerificationPurpose,
    company_name: str | None,
    code_hash: str,
    expire_seconds: int,
) -> None:
    fields = {"purpose": purpose.value, "code_hash": code_hash, "attempts": 0}

    # HSET은 None 값을 저장할 수 없어서 회사 등록일 때만 넣음
    if company_name is not None:
        fields["company_name"] = company_name

    key = _code_key(email)

    async with redis.pipeline(transaction=True) as pipe:
        pipe.delete(key)
        pipe.hset(key, mapping=fields)
        pipe.expire(key, expire_seconds)
        await pipe.execute()


# 인증번호가 맞으면 삭제하고 (용도, 회사 이름) 반환, 틀리거나 만료·잠금이면 None
async def consume_email_verification(
    redis: Redis, email: str, code_hash: str, max_attempts: int
) -> tuple[VerificationPurpose, str | None] | None:
    result = await redis.eval(
        _CONSUME_SCRIPT, 1, _code_key(email), code_hash, max_attempts
    )

    if result[0] != "ok":
        return None

    return VerificationPurpose(result[1]), result[2] or None
