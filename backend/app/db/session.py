from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """요청 하나 = 트랜잭션 하나. 정상 종료면 commit, 예외가 나면 rollback."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# scope="function": 응답을 보내기 전에 commit까지 끝내도록 함
# (기본값 "request"면 응답을 보낸 뒤에 commit해서, commit이 실패해도 클라이언트는 성공 응답을 받음)
SessionDep = Annotated[AsyncSession, Depends(get_db, scope="function")]
