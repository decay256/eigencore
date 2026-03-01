from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.db.database import init_db
from app.api.routes import auth, oauth, game_state, rooms, pinder
from app.middleware.validation import RequestValidationMiddleware, register_validation_handlers

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    description="Game backend API for indie games - accounts, saves, matchmaking",
    version="0.1.0",
    lifespan=lifespan,
)

# Request validation (exception handlers + middleware)
register_validation_handlers(app)
app.add_middleware(RequestValidationMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
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
    """Liveness probe — confirms the process is running."""
    return {"status": "healthy"}


@app.get("/ready")
async def readiness():
    """Readiness probe — confirms the app can serve traffic (DB reachable)."""
    import logging
    logger = logging.getLogger(__name__)
    from sqlalchemy import text
    from app.db.database import async_session

    checks = {"database": "ok"}
    status = "ready"

    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Readiness check failed: database unreachable: %s", e)
        checks["database"] = f"error: {e}"
        status = "not_ready"

    from fastapi.responses import JSONResponse
    code = 200 if status == "ready" else 503
    return JSONResponse(status_code=code, content={"status": status, "checks": checks})
