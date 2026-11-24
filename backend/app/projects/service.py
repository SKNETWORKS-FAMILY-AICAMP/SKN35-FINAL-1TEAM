from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.organizations import repository as user_repo
from app.organizations.models import User, UserLevel
from app.projects import repository as project_repo
from app.projects.models import Project, ProjectMember, ProjectMemberRole
from app.projects.schemas import (
    ProjectDetailResponse,
    ProjectListItem,
    ProjectMemberDetail,
    ProjectMembersCreateRequest,
)
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_CREATOR_LEVELS = {UserLevel.MANAGER, UserLevel.ADMIN}
PROJECT_MEMBER_MANAGER_ROLES = {ProjectMemberRole.OWNER, ProjectMemberRole.LEADER}


# 로그인 사용자의 회사에 프로젝트를 만들고 생성자를 OWNER로 등록
async def create_project(db: AsyncSession, current_user: User, name: str) -> Project:
    if current_user.user_type not in PROJECT_CREATOR_LEVELS:
        raise ForbiddenError("프로젝트 생성 권한이 없습니다.")

    if current_user.company_id is None:
        raise AppError("소속 회사가 없는 사용자입니다.")

    project = await project_repo.create_project(db, current_user.company_id, name)
    await project_repo.create_project_members(
        db,
        [
            ProjectMember(
                project_id=project.project_id,
                user_id=current_user.user_id,
                role=ProjectMemberRole.OWNER,
            )
        ],
    )

    return project


# 프로젝트 OWNER, LEADER가 같은 회사 직원 여러 명을 멤버로 추가 (전부 성공 또는 전부 실패)
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

    requester = await project_repo.get_project_member(
        db, project_id, current_user.user_id
    )

    if requester is None or requester.role not in PROJECT_MEMBER_MANAGER_ROLES:
        raise ForbiddenError("프로젝트 멤버를 추가할 권한이 없습니다.")

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
            user_id=member.user_id,
            role=member.role,
            is_approval=member.is_approval,
        )
        for member in body.members
    ]

    return await project_repo.create_project_members(db, members)


# 내가 멤버인 프로젝트와 내 멤버 정보 조회, 아니면 404
async def _get_my_project(
    db: AsyncSession, current_user: User, project_id: int
) -> tuple[Project, ProjectMember]:
    if current_user.company_id is None:
        raise NotFoundError("프로젝트를 찾을 수 없습니다.")

    project = await project_repo.get_company_project(
        db, project_id, current_user.company_id
    )
    if project is None:
        raise NotFoundError("프로젝트를 찾을 수 없습니다.")

    member = await project_repo.get_project_member(db, project_id, current_user.user_id)
    if member is None:
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
            my_role=role,
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
        my_role=member.role,
        my_is_approval=member.is_approval,
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
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            role=member.role,
            is_approval=member.is_approval,
        )
        for member, user in rows
    ]
