"""
SalesPilot AI — FastAPI Application Entry Point
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.database import Base, engine
from app.rag.engine import RAGEngine
from app.routers import auth, chat, conversations, rag, voice

settings = get_settings()

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level)
    )
)
logger = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SalesPilot AI starting up...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    RAGEngine.get()
    logger.info("SalesPilot AI ready")
    yield
    await engine.dispose()
    logger.info("SalesPilot AI shut down")


app = FastAPI(
    title="SalesPilot AI",
    description="Autonomous AI Sales Voice Agent API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(rag.router)
app.include_router(voice.router)


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "rag_chunks": RAGEngine.get().index.ntotal,
    }


@app.get("/", tags=["system"])
async def root():
    return {"message": "SalesPilot AI API — visit /docs for API reference"}
