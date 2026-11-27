from app.core.enums import YN
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.organizations import repository as user_repo
from app.organizations.models import User, UserLevel
from app.projects import repository as project_repo
from app.projects.models import Project, ProjectMember, ProjectMemberRole, ProjectTeam
from app.projects.schemas import (
    ProjectDetailResponse,
    ProjectListItem,
    ProjectMemberDetail,
    ProjectMembersCreateRequest,
    ProjectTeamCreateRequest,
    ProjectTeamResponse,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_CREATOR_LEVELS = {UserLevel.MANAGER, UserLevel.ADMIN}


# 로그인 사용자의 회사에 프로젝트를 만들고 생성자를 project_owner(OWNER)로 기록
async def create_project(db: AsyncSession, current_user: User, name: str) -> Project:
    if current_user.user_type not in PROJECT_CREATOR_LEVELS:
        raise ForbiddenError("프로젝트 생성 권한이 없습니다.")

    if current_user.company_id is None:
        raise AppError("소속 회사가 없는 사용자입니다.")

    return await project_repo.create_project(
        db, current_user.company_id, name, current_user.user_id
    )


# 같은 회사 직원 여러 명을 프로젝트 팀에 추가 (전부 성공 또는 전부 실패)
# OWNER: 모든 팀에 LEADER·MEMBER 추가 / LEADER: 자기 팀에 MEMBER만 추가
async def add_project_members(
    db: AsyncSession,
    current_user: User,
    project_id: int,
    body: ProjectMembersCreateRequest,
) -> list[ProjectMember]:
    project = await project_repo.get_company_project(
        db, project_id, current_user.company_id
    )
    if project is None:
        raise NotFoundError("프로젝트를 찾을 수 없습니다.")

    is_owner = project.project_owner == current_user.user_id
    requester = (
        None
        if is_owner
        else await project_repo.get_project_member(db, project_id, current_user.user_id)
    )

    if not is_owner and (
        requester is None or requester.role != ProjectMemberRole.LEADER
    ):
        raise ForbiddenError("프로젝트 멤버를 추가할 권한이 없습니다.")

    team_ids = list({member.project_team_id for member in body.members})
    teams = await project_repo.get_project_teams_by_ids(db, project_id, team_ids)

    if len(teams) != len(team_ids):
        raise NotFoundError("프로젝트 팀을 찾을 수 없습니다.")

    if requester is not None:
        for member in body.members:
            if member.project_team_id != requester.project_team_id:
                raise ForbiddenError("자기 팀에만 멤버를 추가할 수 있습니다.")

            if member.role != ProjectMemberRole.MEMBER:
                raise ForbiddenError("팀장은 MEMBER만 추가할 수 있습니다.")

    user_ids = [member.user_id for member in body.members]
    targets = await user_repo.get_active_users_by_ids(db, user_ids)

    if len(targets) != len(user_ids) or any(
        target.company_id != current_user.company_id for target in targets
    ):
        raise NotFoundError("사용자를 찾을 수 없습니다.")

    if await project_repo.get_existing_member_user_ids(db, project_id, user_ids):
        raise ConflictError("이미 프로젝트 멤버인 사용자가 포함되어 있습니다.")

    members = [
        ProjectMember(
            project_id=project_id,
            project_team_id=member.project_team_id,
            user_id=member.user_id,
            role=(
                ProjectMemberRole.OWNER
                if member.user_id == project.project_owner
                else member.role
            ),
            is_approval=member.is_approval,
        )
        for member in body.members
    ]

    try:
        return await project_repo.create_project_members(db, members)
    except IntegrityError:
        raise ConflictError(
            "이미 프로젝트 멤버인 사용자가 포함되어 있습니다."
        ) from None


# 내가 OWNER이거나 멤버인 프로젝트와 내 멤버 정보 조회, 아니면 404
async def _get_my_project(
    db: AsyncSession, current_user: User, project_id: int
) -> tuple[Project, ProjectMember | None]:
    if current_user.company_id is None:
        raise NotFoundError("프로젝트를 찾을 수 없습니다.")

    project = await project_repo.get_company_project(
        db, project_id, current_user.company_id
    )
    if project is None:
        raise NotFoundError("프로젝트를 찾을 수 없습니다.")

    member = await project_repo.get_project_member(db, project_id, current_user.user_id)
    if member is None and project.project_owner != current_user.user_id:
        raise NotFoundError("프로젝트를 찾을 수 없습니다.")

    return project, member


# 내가 속한 프로젝트 목록 조회
async def get_my_projects(
    db: AsyncSession, current_user: User
) -> list[ProjectListItem]:
    if current_user.company_id is None:
        return []

    rows = await project_repo.get_user_projects(
        db, current_user.user_id, current_user.company_id
    )

    return [
        ProjectListItem(
            project_id=project.project_id,
            name=project.name,
            status=project.status,
            created_at=project.created_at,
            my_role=(
                ProjectMemberRole.OWNER
                if project.project_owner == current_user.user_id
                else role
            ),
        )
        for project, role in rows
    ]


# 프로젝트 상세 조회: 프로젝트 멤버만 가능
async def get_project_detail(
    db: AsyncSession, current_user: User, project_id: int
) -> ProjectDetailResponse:
    project, member = await _get_my_project(db, current_user, project_id)

    return ProjectDetailResponse(
        project_id=project.project_id,
        name=project.name,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        my_role=(
            ProjectMemberRole.OWNER
            if project.project_owner == current_user.user_id
            else member.role
        ),
        my_is_approval=member.is_approval if member else YN.N,
        my_project_team_id=member.project_team_id if member else None,
    )


# 프로젝트 멤버 목록 조회: 프로젝트 멤버만 가능
async def get_project_members(
    db: AsyncSession, current_user: User, project_id: int
) -> list[ProjectMemberDetail]:
    await _get_my_project(db, current_user, project_id)
    rows = await project_repo.get_project_members_with_users(db, project_id)

    return [
        ProjectMemberDetail(
            project_member_id=member.project_member_id,
            project_team_id=member.project_team_id,
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            role=member.role,
            is_approval=member.is_approval,
        )
        for member, user in rows
    ]


# 프로젝트 OWNER 확인: 회사 프로젝트가 아니면 404, OWNER가 아니면 403
async def _get_owner_project(
    db: AsyncSession, current_user: User, project_id: int
) -> Project:
    project, _ = await _get_my_project(db, current_user, project_id)

    if project.project_owner != current_user.user_id:
        raise ForbiddenError("프로젝트 OWNER만 할 수 있습니다.")

    return project


# 프로젝트 팀 생성: OWNER만 가능. 대표 팀장을 이 팀의 LEADER 멤버로 함께 등록
async def create_project_team(
    db: AsyncSession,
    current_user: User,
    project_id: int,
    body: ProjectTeamCreateRequest,
) -> ProjectTeamResponse:
    project = await _get_owner_project(db, current_user, project_id)

    if await project_repo.team_name_exists(db, project_id, body.name):
        raise ConflictError("이미 존재하는 팀 이름입니다.")

    leader = await user_repo.get_active_user_by_id(db, body.team_leader)

    if leader is None or leader.company_id != current_user.company_id:
        raise NotFoundError("사용자를 찾을 수 없습니다.")

    if await project_repo.get_project_member(db, project_id, leader.user_id):
        raise ConflictError("이미 이 프로젝트의 다른 팀에 속한 사용자입니다.")

    team = await project_repo.create_project_team(
        db, project_id, body.name, leader.user_id
    )

    try:
        await project_repo.create_project_members(
            db,
            [
                ProjectMember(
                    project_id=project_id,
                    project_team_id=team.project_team_id,
                    user_id=leader.user_id,
                    # OWNER가 본인을 팀장으로 지정하면 역할은 OWNER로 저장
                    role=(
                        ProjectMemberRole.OWNER
                        if leader.user_id == project.project_owner
                        else ProjectMemberRole.LEADER
                    ),
                    is_approval=body.is_approval,
                )
            ],
        )
    except IntegrityError:
        raise ConflictError("이미 이 프로젝트의 다른 팀에 속한 사용자입니다.") from None

    return ProjectTeamResponse(
        project_team_id=team.project_team_id,
        project_id=project_id,
        name=team.name,
        team_leader=leader.user_id,
        team_leader_name=leader.name,
        member_count=1,
    )


# 프로젝트 팀 목록 조회: 프로젝트 멤버·OWNER만 가능
async def get_project_teams(
    db: AsyncSession, current_user: User, project_id: int
) -> list[ProjectTeamResponse]:
    await _get_my_project(db, current_user, project_id)
    rows = await project_repo.get_project_teams_with_leaders(db, project_id)

    return [_to_team_response(*row) for row in rows]


# 대표 팀장 변경: OWNER만 가능. 그 팀의 LEADER(또는 OWNER) 멤버 중에서만 선택
async def update_team_leader(
    db: AsyncSession,
    current_user: User,
    project_id: int,
    project_team_id: int,
    team_leader: int,
) -> ProjectTeamResponse:
    await _get_owner_project(db, current_user, project_id)

    team = await project_repo.get_project_team(db, project_id, project_team_id)
    if team is None:
        raise NotFoundError("프로젝트 팀을 찾을 수 없습니다.")

    member = await project_repo.get_project_member(db, project_id, team_leader)

    if (
        member is None
        or member.project_team_id != project_team_id
        or member.role == ProjectMemberRole.MEMBER
    ):
        raise AppError("이 팀의 LEADER만 대표 팀장으로 지정할 수 있습니다.")

    team.team_leader = team_leader
    await db.flush()

    rows = await project_repo.get_project_teams_with_leaders(
        db, project_id, project_team_id
    )
    return _to_team_response(*rows[0])


def _to_team_response(
    team: ProjectTeam, leader_name: str | None, member_count: int
) -> ProjectTeamResponse:
    return ProjectTeamResponse(
        project_team_id=team.project_team_id,
        project_id=team.project_id,
        name=team.name,
        team_leader=team.team_leader,
        team_leader_name=leader_name,
        member_count=member_count,
    )
