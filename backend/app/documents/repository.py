from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import YN
from app.documents.models import WaitApproval, Document, DocumentVersions


# 사용자 행 생성 후 반환
async def create_wait_approval(
    db: AsyncSession,
    user_id: int,
    project_id: int,
    created_date: datetime,
    s3_path: str,
    document_name: str
) -> WaitApproval:
    document = WaitApproval(
        user_id=user_id,
        project_id=project_id,
        created_date=created_date,
        s3_path=s3_path,
        document_name=document_name,
    )

    db.add(document)
    await db.flush()

    return document
