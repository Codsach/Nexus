"""
Nexus — FastAPI application entry point.
Mounts all module routers, initializes DB, seeds knowledge base.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.exceptions import NexusException, nexus_exception_handler
from app.shared.db.database import create_tables
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("🚀 Nexus starting up...")

    # Initialize database tables
    await create_tables()
    logger.info("✅ Database tables ready")

    # Seed knowledge base
    try:
        from app.modules.knowledge_engine.retriever import seed_knowledge_base
        count = await seed_knowledge_base()
        logger.info(f"✅ Knowledge base seeded: {count} documents")
    except Exception as e:
        logger.warning(f"⚠️ Knowledge base seed failed (non-fatal): {e}")

    logger.info("✅ Nexus ready — http://localhost:8000")
    yield
    logger.info("👋 Nexus shutting down")


app = FastAPI(
    title="Nexus — Autonomous Multi-Agent Customer Support",
    version=settings.app_version,
    description="Resolves support tickets autonomously using multi-agent AI orchestration.",
    lifespan=lifespan,
)

# CORS — allow frontend origins
cors_origins_list = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(NexusException, nexus_exception_handler)
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}
