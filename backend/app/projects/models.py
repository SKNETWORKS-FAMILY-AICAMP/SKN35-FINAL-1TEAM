import enum
from datetime import datetime

from app.core.enums import YN
from app.db.base import Base
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    FetchedValue,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
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
    company_id: Mapped[int] = mapped_column(ForeignKey("company.company_id"))
    name: Mapped[str] = mapped_column(String(100))
    project_owner: Mapped[int] = mapped_column(ForeignKey("user.user_id"))
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


class ProjectTeam(Base):
    __tablename__ = "project_team"
    __table_args__ = (UniqueConstraint("project_id", "name"),)

    project_team_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.project_id"))
    name: Mapped[str] = mapped_column(String(50))
    # 대표 팀장 1명 (LLM 영향 판정 피드백 수집 대상). LEADER 역할은 여러 명 가능
    team_leader: Mapped[int] = mapped_column(ForeignKey("user.user_id"))
    description: Mapped[str | None] = mapped_column(Text)


class ProjectMember(Base):
    __tablename__ = "project_member"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id"),
        # 팀 없는 멤버는 OWNER만
        CheckConstraint(
            "role = 'OWNER' OR project_team_id IS NOT NULL",
            name="ck_project_member_team_required",
        ),
        # 승인권자는 LEADER만
        CheckConstraint(
            "is_approval = 'N' OR role = 'LEADER'",
            name="ck_project_member_approver_leader",
        ),
    )

    project_member_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.project_id"))
    project_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_team.project_team_id")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"))
    role: Mapped[ProjectMemberRole] = mapped_column(
        Enum(ProjectMemberRole, name="project_member_role"),
        default=ProjectMemberRole.MEMBER,
        server_default=ProjectMemberRole.MEMBER.value,
    )
    is_approval: Mapped[YN] = mapped_column(
        Enum(YN, name="yn"), default=YN.N, server_default=YN.N.value
    )
