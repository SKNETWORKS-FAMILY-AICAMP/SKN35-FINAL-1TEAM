from datetime import date
from pydantic import BaseModel, Field, field_validator
from fastapi import File, Form, UploadFile


class DocumentUploadRequest(BaseModel):
    file: UploadFile
    user_id: int = Field(gt=0)
    project_id: int = Field(gt=0)

    @classmethod
    def as_form(
        cls,
        file: UploadFile = File(...),
        user_id: int = Form(...),
        project_id: int = Form(...),
    ) -> "DocumentUploadRequest":
        return cls(
            file=file,
            user_id=user_id,
            project_id=project_id,
        )

class DocumentDownloadRequest(BaseModel):
    filename: str = Field(min_length=1)

class DocumentUploadResponse(BaseModel):
    original_filename: str
    stored_filename: str
    file_path: str
    file_size: int
    user_id: int
    project_id: int
