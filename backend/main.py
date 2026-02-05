"""
FastAPI Main Application for MailMind AI
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings

# Import routers
from routers.emails_router import emails_router
from routers.skills_router import skills_router
from routers.replies_router import replies_router
from routers.status_router import status_router
from routers.oauth_router import oauth_router
from routers.agents_router import agents_router
from routers.agents_router import agents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    # Startup
    from models.database import init_db
    await init_db()
    print("🚀 MailMind AI Backend Started!")
    print(f"📧 Zoho Email: {settings.ZOHO_EMAIL}")
    yield
    # Shutdown
    print("👋 MailMind AI Backend Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="MailMind AI Backend",
    description="AI-powered email assistant using Claude Agent SDK",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(emails_router, prefix="/api/emails", tags=["emails"])
app.include_router(skills_router, prefix="/api/skills", tags=["skills"])
app.include_router(replies_router, prefix="/api/replies", tags=["replies"])
app.include_router(status_router, prefix="/api/status", tags=["status"])
app.include_router(oauth_router, prefix="/api/oauth", tags=["oauth"])
app.include_router(agents_router, prefix="/api/agents", tags=["agents"])
app.include_router(agents_router, prefix="/api/agents", tags=["agents"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Email Assistant Demo API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
