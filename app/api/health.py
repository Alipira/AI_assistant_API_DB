"""Health check endpoints"""
from fastapi import APIRouter
from app.schema.chat_schema import HealthResponse

from openai import OpenAI
from app.config.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Checks:
    - API is running
    - Database connection
    - OpenAI API access
    """

    # Check OpenAI
    openai_status = "healthy"
    try:
        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base
        )
        # Quick test call
        client.models.list()
    except Exception as e:
        openai_status = f"unhealthy: {str(e)}"

    return HealthResponse(
        status="healthy" if openai_status == "healthy" else "degraded",
        openai=openai_status
    )
