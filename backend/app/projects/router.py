from app.auth.dependencies import CurrentUser
from app.db.session import SessionDep
from app.projects import service
from app.projects.schemas import (
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectMemberListResponse,
    ProjectMembersCreateRequest,
    ProjectMembersCreateResponse,
    ProjectTeamCreateRequest,
    ProjectTeamLeaderUpdateRequest,
    ProjectTeamListResponse,
    ProjectTeamResponse,
)
from fastapi import APIRouter, status

router = APIRouter(prefix="/projects", tags=["projects"])


# 프로젝트 생성: 로그인 사용자의 회사에 만들고 생성자를 OWNER로 등록
@router.post(
    "",
    response_model=ProjectCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    body: ProjectCreateRequest, db: SessionDep, current_user: CurrentUser
):
    return await service.create_project(db, current_user, body.name)


# 프로젝트 멤버 일괄 추가: 프로젝트 OWNER, LEADER만 가능
@router.post(
    "/{project_id}/members",
    response_model=ProjectMembersCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_members(
    project_id: int,
    body: ProjectMembersCreateRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    members = await service.add_project_members(db, current_user, project_id, body)
    return {"members": members}


# 내 프로젝트 목록 조회
@router.get("", response_model=ProjectListResponse)
async def get_my_projects(db: SessionDep, current_user: CurrentUser):
    projects = await service.get_my_projects(db, current_user)
    return {"projects": projects}


# 프로젝트 상세 조회: 프로젝트 멤버만 가능
@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project_detail(
    project_id: int, db: SessionDep, current_user: CurrentUser
):
    return await service.get_project_detail(db, current_user, project_id)


# 프로젝트 멤버 목록 조회: 프로젝트 멤버만 가능
@router.get("/{project_id}/members", response_model=ProjectMemberListResponse)
async def get_project_members(
    project_id: int, db: SessionDep, current_user: CurrentUser
):
    members = await service.get_project_members(db, current_user, project_id)
    return {"members": members}


# 프로젝트 팀 생성: OWNER만 가능, 대표 팀장을 LEADER 멤버로 함께 등록
@router.post(
    "/{project_id}/teams",
    response_model=ProjectTeamResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_team(
    project_id: int,
    body: ProjectTeamCreateRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    return await service.create_project_team(db, current_user, project_id, body)


# 프로젝트 팀 목록 조회: 프로젝트 멤버·OWNER만 가능
@router.get("/{project_id}/teams", response_model=ProjectTeamListResponse)
async def get_project_teams(
    project_id: int, db: SessionDep, current_user: CurrentUser
):
    teams = await service.get_project_teams(db, current_user, project_id)
    return {"teams": teams}


# 대표 팀장 변경: OWNER만 가능, 그 팀의 LEADER 중에서만 선택
@router.patch(
    "/{project_id}/teams/{project_team_id}/leader",
    response_model=ProjectTeamResponse,
)
async def update_team_leader(
    project_id: int,
    project_team_id: int,
    body: ProjectTeamLeaderUpdateRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    return await service.update_team_leader(
        db, current_user, project_id, project_team_id, body.team_leader
    )
