from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.db.database import get_db
from app.modules.analytics.aggregator import get_overview, get_clusters, get_churn_risk

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def analytics_overview(db: AsyncSession = Depends(get_db)):
    return await get_overview(db)


@router.get("/clusters")
async def analytics_clusters(db: AsyncSession = Depends(get_db)):
    return await get_clusters(db)


@router.get("/churn-risk")
async def analytics_churn_risk(db: AsyncSession = Depends(get_db)):
    return await get_churn_risk(db)
