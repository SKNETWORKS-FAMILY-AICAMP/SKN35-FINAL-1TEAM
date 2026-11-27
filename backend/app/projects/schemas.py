from datetime import datetime

from app.core.enums import YN
from app.projects.models import ProjectMemberRole, ProjectStatus
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_MEMBERS_PER_REQUEST = 50


# 프로젝트 생성 api request
class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()

        if not v:
            raise ValueError("프로젝트 이름을 입력해주세요.")

        return v


# 프로젝트 생성 api response
class ProjectCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: int
    name: str
    status: ProjectStatus
    created_at: datetime


# 프로젝트 팀 생성 api request: 팀을 만들면서 대표 팀장을 LEADER로 등록
class ProjectTeamCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    team_leader: int = Field(gt=0)
    is_approval: YN = YN.N
    description: str | None = Field(default=None, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()

        if not v:
            raise ValueError("팀 이름을 입력해주세요.")

        return v

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: str | None) -> str | None:
        if v is None:
            return None

        return v.strip() or None


# 대표 팀장 변경 api request
class ProjectTeamLeaderUpdateRequest(BaseModel):
    team_leader: int = Field(gt=0)


# 프로젝트 팀 1개 응답
class ProjectTeamResponse(BaseModel):
    project_team_id: int
    project_id: int
    name: str
    description: str | None
    team_leader: int
    team_leader_name: str | None
    member_count: int


# 프로젝트 팀 목록 api response
class ProjectTeamListResponse(BaseModel):
    teams: list[ProjectTeamResponse]


# 프로젝트 멤버 추가 대상 1명
class ProjectMemberCreateItem(BaseModel):
    user_id: int = Field(gt=0)
    project_team_id: int = Field(gt=0)
    role: ProjectMemberRole = ProjectMemberRole.MEMBER
    is_approval: YN = YN.N

    @field_validator("role")
    @classmethod
    def not_owner(cls, v: ProjectMemberRole) -> ProjectMemberRole:
        if v == ProjectMemberRole.OWNER:
            raise ValueError("OWNER 권한은 부여할 수 없습니다.")
        return v

    @model_validator(mode="after")
    def approval_only_leader(self) -> "ProjectMemberCreateItem":
        if self.is_approval == YN.Y and self.role != ProjectMemberRole.LEADER:
            raise ValueError("승인권자는 LEADER만 지정할 수 있습니다.")
        return self


# 프로젝트 멤버 일괄 추가 api request
class ProjectMembersCreateRequest(BaseModel):
    members: list[ProjectMemberCreateItem] = Field(
        min_length=1, max_length=MAX_MEMBERS_PER_REQUEST
    )

    @field_validator("members")
    @classmethod
    def unique_users(
        cls, v: list[ProjectMemberCreateItem]
    ) -> list[ProjectMemberCreateItem]:
        user_ids = [member.user_id for member in v]
        if len(user_ids) != len(set(user_ids)):
            raise ValueError("같은 사용자를 중복으로 추가할 수 없습니다.")
        return v


# 프로젝트 멤버 1명 응답
class ProjectMemberCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_member_id: int
    project_id: int
    project_team_id: int
    user_id: int
    role: ProjectMemberRole
    is_approval: YN


# 프로젝트 멤버 일괄 추가 api response
class ProjectMembersCreateResponse(BaseModel):
    members: list[ProjectMemberCreateResponse]


# 내 프로젝트 1개 응답
class ProjectListItem(BaseModel):
    project_id: int
    name: str
    status: ProjectStatus
    created_at: datetime
    my_role: ProjectMemberRole


# 내 프로젝트 목록 api response
class ProjectListResponse(BaseModel):
    projects: list[ProjectListItem]


# 프로젝트 상세 api response
class ProjectDetailResponse(BaseModel):
    project_id: int
    name: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    my_role: ProjectMemberRole
    my_is_approval: YN
    my_project_team_id: int | None


# 프로젝트 멤버 목록의 멤버 1명 응답 (팀 배정 전 OWNER는 project_team_id가 None)
class ProjectMemberDetail(BaseModel):
    project_member_id: int
    project_team_id: int | None
    user_id: int
    name: str
    email: str
    role: ProjectMemberRole
    is_approval: YN


# 프로젝트 멤버 목록 api response
class ProjectMemberListResponse(BaseModel):
    members: list[ProjectMemberDetail]
