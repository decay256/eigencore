import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.database import init_db
from app.api.routes import auth, oauth, game_state, rooms, pinder
from app.middleware.request_id import RequestIDMiddleware

settings = get_settings()
setup_logging(level="DEBUG" if settings.debug else "INFO")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("EigenCore starting up")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("EigenCore shutting down")


app = FastAPI(
    title=settings.app_name,
    description="Game backend API for indie games - accounts, saves, matchmaking",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (order matters — RequestID outermost so every request gets traced)
app.add_middleware(RequestIDMiddleware)
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with API version prefix
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(oauth.router, prefix=API_PREFIX)
app.include_router(game_state.router, prefix=API_PREFIX)
app.include_router(rooms.router, prefix=API_PREFIX)
app.include_router(pinder.router, prefix=API_PREFIX)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
