from app.core.enums import YN
from app.organizations.models import User
from app.projects.models import Project, ProjectMember, ProjectMemberRole, ProjectTeam
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


# 프로젝트 행 생성 후 반환
async def create_project(
    db: AsyncSession, company_id: int, name: str, owner_id: int
) -> Project:
    project = Project(company_id=company_id, name=name, project_owner=owner_id)
    db.add(project)
    await db.flush()
    return project


# 프로젝트 멤버 여러 행 생성 후 반환
async def create_project_members(
    db: AsyncSession, members: list[ProjectMember]
) -> list[ProjectMember]:
    db.add_all(members)
    await db.flush()
    return members


# 해당 회사에 속한 프로젝트 조회
async def get_company_project(
    db: AsyncSession, project_id: int, company_id: int
) -> Project | None:
    return await db.scalar(
        select(Project).where(
            Project.project_id == project_id, Project.company_id == company_id
        )
    )


# 프로젝트에 속한 멤버 조회
async def get_project_member(
    db: AsyncSession, project_id: int, user_id: int
) -> ProjectMember | None:
    return await db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
    )


# 전달한 사용자 중 이미 프로젝트 멤버인 user_id 조회
async def get_existing_member_user_ids(
    db: AsyncSession, project_id: int, user_ids: list[int]
) -> set[int]:
    result = await db.scalars(
        select(ProjectMember.user_id).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id.in_(user_ids),
        )
    )
    return set(result)


# 사용자가 OWNER이거나 멤버인 회사 프로젝트와 멤버 역할 조회 (최신순)
async def get_user_projects(
    db: AsyncSession, user_id: int, company_id: int
) -> list[tuple[Project, ProjectMemberRole | None]]:
    result = await db.execute(
        select(Project, ProjectMember.role)
        .outerjoin(
            ProjectMember,
            (ProjectMember.project_id == Project.project_id)
            & (ProjectMember.user_id == user_id),
        )
        .where(
            Project.company_id == company_id,
            or_(Project.project_owner == user_id, ProjectMember.user_id == user_id),
        )
        .order_by(Project.created_at.desc(), Project.project_id.desc())
    )
    return [(project, role) for project, role in result.all()]


# 전달한 팀 중 해당 프로젝트에 속한 팀 조회
async def get_project_teams_by_ids(
    db: AsyncSession, project_id: int, project_team_ids: list[int]
) -> list[ProjectTeam]:
    result = await db.scalars(
        select(ProjectTeam).where(
            ProjectTeam.project_id == project_id,
            ProjectTeam.project_team_id.in_(project_team_ids),
        )
    )
    return list(result)


# 프로젝트 팀 행 생성 후 반환
async def create_project_team(
    db: AsyncSession, project_id: int, name: str, team_leader: int
) -> ProjectTeam:
    team = ProjectTeam(project_id=project_id, name=name, team_leader=team_leader)
    db.add(team)
    await db.flush()  # project_team_id를 받아오기 위해
    return team


# 프로젝트에 같은 이름의 팀이 있는지 확인
async def team_name_exists(db: AsyncSession, project_id: int, name: str) -> bool:
    return await db.scalar(
        select(
            exists().where(ProjectTeam.project_id == project_id, ProjectTeam.name == name)
        )
    )


# 해당 프로젝트에 속한 팀 조회
async def get_project_team(
    db: AsyncSession, project_id: int, project_team_id: int
) -> ProjectTeam | None:
    return await db.scalar(
        select(ProjectTeam).where(
            ProjectTeam.project_id == project_id,
            ProjectTeam.project_team_id == project_team_id,
        )
    )


# 프로젝트 팀과 대표 팀장 이름, 팀원 수 조회 (project_team_id를 주면 그 팀만)
async def get_project_teams_with_leaders(
    db: AsyncSession, project_id: int, project_team_id: int | None = None
) -> list[tuple[ProjectTeam, str | None, int]]:
    member_count = (
        select(func.count(ProjectMember.project_member_id))
        .where(ProjectMember.project_team_id == ProjectTeam.project_team_id)
        .correlate(ProjectTeam)
        .scalar_subquery()
    )
    query = (
        select(ProjectTeam, User.name, member_count)
        .outerjoin(User, User.user_id == ProjectTeam.team_leader)
        .where(ProjectTeam.project_id == project_id)
    )

    if project_team_id is not None:
        query = query.where(ProjectTeam.project_team_id == project_team_id)

    result = await db.execute(query.order_by(ProjectTeam.project_team_id))
    return [(team, leader_name, count) for team, leader_name, count in result.all()]


# 프로젝트의 재직 멤버와 사용자 정보 조회
async def get_project_members_with_users(
    db: AsyncSession, project_id: int
) -> list[tuple[ProjectMember, User]]:
    result = await db.execute(
        select(ProjectMember, User)
        .join(User, User.user_id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id, User.is_deleted == YN.N)
        .order_by(ProjectMember.project_member_id)
    )
    return [(member, user) for member, user in result.all()]
