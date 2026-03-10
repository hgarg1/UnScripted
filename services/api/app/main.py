from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.app.api.routes.agents import router as agents_router
from services.api.app.api.routes.auth import router as auth_router
from services.api.app.api.routes.health import router as health_router
from services.api.app.api.routes.ml import router as ml_router
from services.api.app.api.routes.observability import router as observability_router
from services.api.app.api.routes.social import router as social_router
from services.api.app.api.routes.simulation import internal_router as internal_simulation_router
from services.api.app.api.routes.simulation import router as simulation_router
from services.api.app.core.config import get_settings
from services.api.app.db.base import Base
from services.api.app.db.session import engine


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.api_title, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(agents_router)
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(ml_router)
app.include_router(observability_router)
app.include_router(social_router)
app.include_router(simulation_router)
app.include_router(internal_simulation_router)
