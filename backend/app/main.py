from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

from app.api.v1.auth import router as auth_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.include_router(
    auth_router,
    prefix="/api/v1",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "application": settings.APP_NAME,
    }

