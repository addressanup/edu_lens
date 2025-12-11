"""
EduLens Database Models

SQLAlchemy models for persistent storage of children profiles and sessions.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker as async_sessionmaker
from pydantic import BaseModel, Field
import os

Base = declarative_base()


# ============================================
# SQLAlchemy ORM Models (Database Tables)
# ============================================

class ChildDB(Base):
    """Child profile stored in database."""
    __tablename__ = "children"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_id = Column(String, nullable=True)  # For future parent auth
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    grade = Column(String, nullable=False)
    language = Column(String, default="en")

    # Privacy settings for parent monitoring
    allow_remote_monitoring = Column(Boolean, default=True)
    allow_parent_voice = Column(Boolean, default=True)
    notify_child_on_connect = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to sessions
    sessions = relationship("SessionDB", back_populates="child", cascade="all, delete-orphan")


class SessionDB(Base):
    """Tutoring session stored in database."""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    child_id = Column(String, ForeignKey("children.id"), nullable=True)
    device_id = Column(String, nullable=True)
    history = Column(JSON, default=list)
    context = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to child
    child = relationship("ChildDB", back_populates="sessions")


# ============================================
# Pydantic Models (API Request/Response)
# ============================================

class ChildCreate(BaseModel):
    """Request model for creating a child profile."""
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=3, le=18)
    grade: str = Field(..., min_length=1, max_length=20)
    language: str = Field(default="en", max_length=10)
    parent_id: Optional[str] = None
    # Privacy settings
    allow_remote_monitoring: bool = True
    allow_parent_voice: bool = True
    notify_child_on_connect: bool = True


class ChildUpdate(BaseModel):
    """Request model for updating a child profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=3, le=18)
    grade: Optional[str] = Field(None, min_length=1, max_length=20)
    language: Optional[str] = Field(None, max_length=10)
    # Privacy settings
    allow_remote_monitoring: Optional[bool] = None
    allow_parent_voice: Optional[bool] = None
    notify_child_on_connect: Optional[bool] = None


class ChildResponse(BaseModel):
    """Response model for child profile."""
    id: str
    name: str
    age: int
    grade: str
    language: str
    allow_remote_monitoring: bool
    allow_parent_voice: bool
    notify_child_on_connect: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """Response model for session."""
    id: str
    child_id: Optional[str]
    history: List[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Database Connection & Session Management
# ============================================

def get_database_url() -> str:
    """Get database URL from environment."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://edulens:edulens_dev@localhost:5432/edulens"
    )


def get_async_database_url() -> str:
    """Get async database URL (converts postgresql:// to postgresql+asyncpg://)."""
    url = get_database_url()
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# Sync engine (for migrations and simple operations)
def create_sync_engine():
    return create_engine(get_database_url(), echo=False)


# Async engine (for FastAPI async operations)
def create_async_db_engine():
    return create_async_engine(get_async_database_url(), echo=False)


# Session factories
def get_sync_session():
    engine = create_sync_engine()
    Session = sessionmaker(bind=engine)
    return Session()


async def get_async_session():
    engine = create_async_db_engine()
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


# ============================================
# Database Initialization
# ============================================

def init_db():
    """Initialize database tables."""
    engine = create_sync_engine()
    Base.metadata.create_all(engine)
    return engine


async def init_db_async():
    """Initialize database tables asynchronously."""
    engine = create_async_db_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine
