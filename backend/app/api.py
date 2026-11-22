from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.organizations.router import router as organizations_router
from app.projects.router import router as projects_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(organizations_router)
api_router.include_router(projects_router)
