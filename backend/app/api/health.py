from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from sqlalchemy import text
import redis.asyncio as redis
from app.config import settings

router = APIRouter()


@router.get("/")
async def health_check():
    return {"status": "ok"}


@router.get("/db")
def health_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/cache")
async def health_cache():
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        return {"status": "ok", "cache": "connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
