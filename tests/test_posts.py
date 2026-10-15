import pytest
from httpx import AsyncClient

from .conftest import auth_header, login_test_user, register_test_user


@pytest.mark.anyio
async def test_get_posts_empty(client: AsyncClient):
    response = await client.get("/api/posts/")

    assert response.status_code == 200
    data = response.json()
    assert data["posts"] == []
    assert data["total"] == 0
    assert data["has_more"] is False


@pytest.mark.anyio
async def test_get_post_not_found(client: AsyncClient):
    response = await client.get("/api/posts/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found!"


@pytest.mark.anyio
async def test_create_post_success(client: AsyncClient):
    user = await register_test_user(client)
    token = await login_test_user(client)
    headers = auth_header(token)

    response = await client.post(
        "/api/posts/",
        json={
            "title": "My First Post",
            "content": "This is the content",
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My First Post"
    assert data["content"] == "This is the content"
    assert data["user_id"] == user["id"]
    assert "id" in data
    assert "date_posted" in data
    assert data["author"]["username"] == "testuser"


@pytest.mark.anyio
async def test_create_post_unauthorized(client: AsyncClient):
    response = await client.post(
        "/api/posts/",
        json={"title": "Test Post", "content": "Test content"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.anyio
async def test_update_post_success(client: AsyncClient):
    await register_test_user(client)
    token = await login_test_user(client)
    headers = auth_header(token)

    response = await client.post(
        "/api/posts/",
        json={
            "title": "Original Title",
            "content": "Original content",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    post_id = response.json()["id"]

    response = await client.patch(
        f"/api/posts/{post_id}",
        json={"title": "Updated Title"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["content"] == "Original content"
