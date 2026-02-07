"""
Main FastAPI Application for Message Service
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.api import routes
from app.infrastructure.persistence.database import init_db, get_db, AsyncSession
from app.infrastructure.persistence.conversation_repository_impl import ConversationRepositoryImpl
from app.infrastructure.persistence.message_repository_impl import MessageRepositoryImpl
from app.domain.repositories.conversation_repository import IConversationRepository
from app.domain.repositories.message_repository import IMessageRepository

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    logger.info(f"Database URL: {settings.DATABASE_URL.split('@')[-1]}")  # Hide password

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


# Create FastAPI app
app = FastAPI(
    title="ModAI Message Service",
    description="Manages conversations and messages for ModAI platform",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency Injection

def get_conversation_repository(session: AsyncSession = Depends(get_db)) -> IConversationRepository:
    """Get conversation repository instance"""
    return ConversationRepositoryImpl(session)


def get_message_repository(session: AsyncSession = Depends(get_db)) -> IMessageRepository:
    """Get message repository instance"""
    return MessageRepositoryImpl(session)


# Override route dependencies
routes.get_conversation_repository = get_conversation_repository
routes.get_message_repository = get_message_repository

# Include routes
app.include_router(routes.router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=True,
    )
