"""Main FastAPI application"""
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()
from app.api import chat, health
from app.config.config import get_settings


settings = get_settings()


app = FastAPI(
    title="AI Data Chatbot",
    description="Chatbot that answers questions about your Transportation Fleet",
    version="1.0.0",
)

# CORS middleware
# List your actual frontend origin(s) here.
ALLOWED_ORIGINS = [
    "http://localhost:3000",       # local frontend dev
    "http://localhost:5173",       # Vite dev server
    # "https://your-production-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if not settings.debug else ["*"],
    allow_credentials=not settings.debug,   # credentials need explicit origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
        },
        "UserIdHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-User-Id",
        },
        "TenantIdHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Tenant-Id",
        },
    }
    # Apply security to all routes
    for path in schema.get("paths", {}).values():
        for method in path.values():
            method["security"] = [
                {"BearerAuth": [], "UserIdHeader": [], "TenantIdHeader": []}
            ]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "message": "AI Data Chatbot API",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
