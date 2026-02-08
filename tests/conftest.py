# =============================================================================
# Pytest Fixtures
# =============================================================================
# Fixtures are reusable test setup/teardown helpers.
# Any test can request a fixture by adding it as a parameter.
#
# Example:
#   async def test_something(client, test_user):
#       response = await client.get("/auth/me", headers=auth_headers(test_user))
# =============================================================================

import pytest
import asyncio
import warnings
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import Base, get_db
from app.models.user import User
from app.core.security import hash_password, create_access_token

# Suppress passlib bcrypt version warning (it works fine)
warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")


# =============================================================================
# Database Fixtures
# =============================================================================

# Use in-memory SQLite for tests (fast, isolated, no cleanup needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_engine():
    """Create a fresh database engine for each test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite specific
        poolclass=StaticPool,  # Share connection across threads
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    """Create a database session for a test."""
    async_session = async_sessionmaker(
        db_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session):
    """Create an HTTP client that uses the test database."""
    
    # Override the get_db dependency to use our test session
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create async HTTP client with API version prefix
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test/api/v1"
    ) as ac:
        yield ac
    
    # Reset overrides
    app.dependency_overrides.clear()


# =============================================================================
# User Fixtures
# =============================================================================

@pytest.fixture
async def test_user(db_session) -> User:
    """Create a test user in the database."""
    user = User(
        email="test@example.com",
        display_name="Test User",
        password_hash=hash_password("testpassword123"),
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_user_2(db_session) -> User:
    """Create a second test user (for multiplayer tests)."""
    user = User(
        email="test2@example.com",
        display_name="Test User 2",
        password_hash=hash_password("testpassword123"),
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user) -> str:
    """Create a valid JWT token for test_user."""
    return create_access_token({"sub": str(test_user.id)})


@pytest.fixture
def auth_token_2(test_user_2) -> str:
    """Create a valid JWT token for test_user_2."""
    return create_access_token({"sub": str(test_user_2.id)})


def auth_headers(token: str) -> dict:
    """Helper to create Authorization headers."""
    return {"Authorization": f"Bearer {token}"}
