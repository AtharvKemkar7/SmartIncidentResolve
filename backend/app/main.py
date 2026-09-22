from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.clusters import router as clusters_router
from app.api.routes.health import router as health_router
from app.api.routes.history import router as history_router
from app.api.routes.investigate import router as investigate_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="AI Kubernetes Agent",
    description="On-demand Kubernetes troubleshooting orchestrator",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.monkeycode-ai\.live",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(clusters_router)
app.include_router(history_router)
app.include_router(investigate_router)
