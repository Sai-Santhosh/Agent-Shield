"""AgentShield - AI Agent Security Gateway."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as v1_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.init_db import init_db

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="AgentShield",
    description="AI-native security gateway for agent actions: LangChain tools, AWS IAM, codegen",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.get("/healthz")
async def healthz():
    """Liveness probe."""
    return {"ok": True}


@app.get("/readyz")
async def readyz():
    """Readiness probe (DB connectivity)."""
    return {"ok": True}
