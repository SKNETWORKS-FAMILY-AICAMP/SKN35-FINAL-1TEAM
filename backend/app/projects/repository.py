from app.core.enums import YN
from app.organizations.models import User
from app.projects.models import Project, ProjectMember, ProjectMemberRole
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# 프로젝트 행 생성 후 반환
async def create_project(db: AsyncSession, company_id: int, name: str) -> Project:
    project = Project(company_id=company_id, name=name)
    db.add(project)
    await db.flush()  # project_id를 받아오기 위해
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


# 사용자가 속한 회사 프로젝트와 내 역할 조회 (최신순)
async def get_user_projects(
    db: AsyncSession, user_id: int, company_id: int
) -> list[tuple[Project, ProjectMemberRole]]:
    result = await db.execute(
        select(Project, ProjectMember.role)
        .join(ProjectMember, ProjectMember.project_id == Project.project_id)
        .where(ProjectMember.user_id == user_id, Project.company_id == company_id)
        .order_by(Project.created_at.desc(), Project.project_id.desc())
    )
    return [(project, role) for project, role in result.all()]


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
