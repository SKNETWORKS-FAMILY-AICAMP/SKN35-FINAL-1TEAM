from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.exceptions import AppError, app_error_handler
from app.db.redis import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await redis_client.aclose()


app = FastAPI(title="Company Brain API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,  # refresh 쿠키
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AppError, app_error_handler)

app.include_router(api_router)
