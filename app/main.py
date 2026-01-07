"""Main FastAPI application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, health
from app.config import get_settings

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="AI Data Chatbot",
    description="Chatbot that answers questions about your PostgreSQL database",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Data Chatbot API",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
