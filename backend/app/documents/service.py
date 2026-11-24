import anyio
from pathlib import Path
from datetime import date
from uuid import uuid4
from datetime import datetime

from fastapi import HTTPException, status, UploadFile
from fastapi.responses import FileResponse

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError
from app.core.security import hash_password

from app.documents.schemas import DocumentUploadResponse

from app.documents import repository as doc_repo

# backend 디렉터리
BASE_DIR = Path(__file__).resolve().parents[2]

# 파일 저장 루트
STORAGE_DIR = BASE_DIR / "storage" / "temp"

# 파일 크기 제한: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# 한 번에 읽을 크기: 1MB
CHUNK_SIZE = 1024 * 1024


async def upload_document(db: AsyncSession, file: UploadFile, user_id: int, project_id: int):

    # 1. 원본 파일명 확인
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일명이 존재하지 않습니다.",
        )

    # 2. 저장 경로 생성
    upload_dir = STORAGE_DIR

    await anyio.to_thread.run_sync(
        lambda: upload_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
    )

    # 3. 고유한 파일명 생성
    original_filename = file.filename

    extension = Path(original_filename).suffix.lower()  # 확장자
    file_name = original_filename.rstrip(extension)     # 확장자 이전까지의 파일 이름
    
    now = datetime.now()
    current_time = now.strftime('%Y%m%dT%H%M%S')

    stored_filename = f"{file_name}_{current_time}{extension}"
    stored_file_path = (upload_dir / stored_filename).relative_to(BASE_DIR).as_posix()

    # 4. 파일 저장
    file_size = 0

    try:
        async with await anyio.open_file(stored_file_path, "xb") as output:
            while chunk := await file.read(CHUNK_SIZE):
                file_size += len(chunk)

                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="파일 크기는 50MB를 초과할 수 없습니다.",
                    )

                await output.write(chunk)

    except Exception:
        # 저장 중 오류 발생 시 불완전한 파일 제거
        await anyio.to_thread.run_sync(
            stored_file_path.unlink,
            missing_ok=True,
        )
        raise

    finally:
        await file.close()

    # 5. DB 저장
    try:
        await doc_repo.create_wait_approval(db, user_id, project_id, now, stored_file_path.replace(stored_filename, ''), stored_filename)
    except Exception as e:
        raise e
    
    # 5. 결과 반환
    return DocumentUploadResponse(
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=stored_file_path,
        file_size=file_size,
        user_id=user_id,
        project_id=project_id,
    )

async def download_document(file_name: str):

    # 1. 프로젝트 및 사용자별 저장 디렉터리
    # upload_dir = (
    #     STORAGE_DIR
    #     / "projects"
    #     / str(request.project_id)
    #     / "users"
    #     / str(request.user_id)
    #     / "uploads"
    # )

    download_dir = STORAGE_DIR

    # 2. 파일 경로 검증
    # ../ 등을 이용한 다른 디렉터리 접근 방지
    if (file_name in {".", ".."} or Path(file_name).name != file_name or "\\" in file_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="올바르지 않은 파일명입니다.",
        )

    # 3. 다운로드할 파일 경로
    file_path = download_dir / file_name

    # 심볼릭 링크를 통한 경로 이탈도 방지
    if not file_path.resolve().is_relative_to(file_path.resolve()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="허용되지 않은 파일 경로입니다.",
        )

    # 4. 파일 존재 여부 확인
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="파일을 찾을 수 없습니다.",
        )

    # 5. 파일 다운로드 응답
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/octet-stream",
        content_disposition_type="attachment",
    )
