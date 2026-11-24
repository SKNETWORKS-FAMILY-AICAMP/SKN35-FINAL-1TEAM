from fastapi import APIRouter, status
from typing import Annotated
from fastapi import APIRouter, File, Form, UploadFile, Depends
from fastapi.responses import FileResponse

from app.db.session import SessionDep
from app.documents import service
from app.documents.schemas import DocumentUploadRequest, DocumentUploadResponse, DocumentDownloadRequest

router = APIRouter(prefix="/documents", tags=["documents"])

# 파일 업로드
@router.post(
    "/upload-document",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_document(db: SessionDep, request: DocumentUploadRequest = Depends(DocumentUploadRequest.as_form)):
    file = request.file
    user_id = request.user_id
    project_id = request.project_id

    result = await service.upload_document(db, file, user_id, project_id)

    return result

# 파일 다운로드 : 승인 대기 파일
@router.get(
    "/download-document",
    response_class=FileResponse,
    status_code=status.HTTP_201_CREATED
)
async def download_document(request: DocumentDownloadRequest = Depends()):
    file_name = request.filename
    return await service.download_document(file_name)
