from fastapi import APIRouter
from app.modules.coordinator.router import router as coordinator_router
from app.modules.specialist_agents.router import router as specialist_router
from app.modules.knowledge_engine.router import router as knowledge_router
from app.modules.escalation.router import router as escalation_router
from app.modules.analytics.router import router as analytics_router
from app.modules.mock_systems.router import router as mock_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(coordinator_router)
api_router.include_router(specialist_router)
api_router.include_router(knowledge_router)
api_router.include_router(escalation_router)
api_router.include_router(analytics_router)
api_router.include_router(mock_router)
