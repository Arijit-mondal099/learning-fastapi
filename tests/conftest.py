import asyncio
import os
import selectors
import sys
from collections.abc import AsyncGenerator

os.environ["DATABASE_URL"] = (
    "postgresql://neondb_owner:npg_IlRH1dvgtc2i@ep-dark-sun-aoz8vggr-pooler.c-2.ap-southeast-1.aws.neon.tech/test_fastapi_blog?sslmode=require&channel_binding=require"
)


import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from database import Base, get_db
from main import app

# Help us to use ansyc
pytest_plugins = ["anyio"]


@pytest.fixture(scope="session")
def anyio_backend():
    if sys.platform == "win32":
        return (
            "asyncio",
            {
                "loop_factory": lambda: asyncio.SelectorEventLoop(
                    selectors.SelectSelector()
                )
            },
        )
    else:
        return "asyncio"


@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
    return engine


@pytest.fixture(scope="session")
async def init_test_database(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def test_db_session(
    test_engine, init_test_database
) -> AsyncGenerator[AsyncSession]:
    conn = await test_engine.connect()
    trans = await conn.begin()

    test_asycn_session = async_sessionmaker(
        bind=conn,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async with test_asycn_session() as session:
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
            await conn.close()


@pytest.fixture
async def client(
    test_db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient]:
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


async def register_test_user(client: AsyncClient):
    response = await client.post(
        "/api/users/",
        json={
            "username": "testuser",
            "email": "test@gmail.com",
            "password": "12345678",
        },
    )

    assert response.status_code == 201, (
        f"Failed to create user: "
        f"status={response.status_code}, "
        f"location={response.headers.get('location')}, "
        f"body={response.text}"
    )

    return response.json()


async def login_test_user(client: AsyncClient):
    response = await client.post(
        "/api/users/token",
        data={
            "username": "test@gmail.com",
            "password": "12345678",
        },
    )

    assert response.status_code == 200, (
        f"Failed to login user: status={response.status_code}, body={response.text}"
    )

    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
