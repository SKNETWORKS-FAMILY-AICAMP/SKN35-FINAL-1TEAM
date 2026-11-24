from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import YN, DocumentGrade
from app.db.base import Base


class WaitApproval(Base):
    __tablename__ = "wait_approval"

    wait_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.user_id'))
    project_id: Mapped[int] = mapped_column(ForeignKey('project.project_id'))
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    s3_path: Mapped[str] = mapped_column(String(50), unique=True)
    document_name: Mapped[str] = mapped_column(String(50), unique=True)

class Document(Base):
    __tablename__ = "document"

    document_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('project.project_id'))
    create_user: Mapped[int] = mapped_column(ForeignKey('user.user_id'))
    name: Mapped[str] = mapped_column(String(100))
    current_version_id: Mapped[int] = mapped_column()
    is_deleted: Mapped[YN] = mapped_column(
        Enum(YN, name="yn"),
        default=YN.N,
        server_default=YN.N.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class DocumentVersions(Base):
    __tablename__ = "document_versions"

    version_id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('document.document_id'))
    created_user: Mapped[int] = mapped_column(ForeignKey('user.user_id'))
    version_number: Mapped[int] = mapped_column()
    base_version_id: Mapped[int] = mapped_column()
    s3_path: Mapped[str] = mapped_column(String(500), unique=True)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True)
    change_note: Mapped[str] = mapped_column(Text)
    document_grade: Mapped[DocumentGrade] = mapped_column(
        Enum(DocumentGrade, name="document_grade"),
        default=DocumentGrade.PROJECT_PRIVATE,
        server_default=DocumentGrade.PROJECT_PRIVATE.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
