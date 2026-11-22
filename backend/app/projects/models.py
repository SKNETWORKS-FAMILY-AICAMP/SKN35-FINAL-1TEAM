import enum
from datetime import datetime

from app.core.enums import YN
from app.db.base import Base
from sqlalchemy import DateTime, Enum, FetchedValue, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column


class ProjectStatus(str, enum.Enum):
    START = "START"
    END = "END"


class ProjectMemberRole(str, enum.Enum):
    OWNER = "OWNER"
    LEADER = "LEADER"
    MEMBER = "MEMBER"


class Project(Base):
    __tablename__ = "project"
    __mapper_args__ = {"eager_defaults": True}

    project_id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("company.company_id"))
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"),
        default=ProjectStatus.START,
        server_default=ProjectStatus.START.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=FetchedValue(),
    )


class ProjectMember(Base):
    __tablename__ = "project_member"

    project_member_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.project_id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"))
    role: Mapped[ProjectMemberRole] = mapped_column(
        Enum(ProjectMemberRole, name="project_member_role"),
        default=ProjectMemberRole.MEMBER,
        server_default=ProjectMemberRole.MEMBER.value,
    )
    is_approval: Mapped[YN] = mapped_column(
        Enum(YN, name="yn"), default=YN.N, server_default=YN.N.value
    )
