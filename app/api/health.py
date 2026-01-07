"""Health check endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.chat import HealthResponse
from app.db.session import get_db, test_connection
from openai import OpenAI
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint

    Checks:
    - API is running
    - Database connection
    - OpenAI API access
    """

    # Check database
    db_status = "healthy" if test_connection() else "unhealthy"

    # Check OpenAI
    openai_status = "healthy"
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        # Quick test call
        client.models.list()
    except Exception as e:
        openai_status = f"unhealthy: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "healthy" and openai_status == "healthy" else "degraded",
        database=db_status,
        openai=openai_status
    )
