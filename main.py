from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Request, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException as StarletteHTTPException

import models
from database import Base, engine, get_db
from schemas import (
    PostCreate,
    PostResponse,
    PostUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)


# Lifespan here for app startup and shut down
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    # Startup
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

# Mount the static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

# Initialize the Jinja2Templates object with the directory containing your HTML templates
templates = Jinja2Templates(directory="templates")


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def root(req: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    # We also get author of the post from relationship
    # But in async we have to told sqlalchemy to load author as well
    result = await db.execute(
        select(models.Post)
        .order_by(models.Post.date_posted.desc())
        .options(selectinload(models.Post.author))
    )
    posts = result.scalars().all()

    return templates.TemplateResponse(req, "home.html", {"posts": posts})


@app.get("/posts/{post_id}", include_in_schema=False)
async def post(
    req: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    post_id: int = Path(..., gt=0, desPcription="Get individual post by post id"),
):
    result = await db.execute(
        select(models.Post)
        .where(models.Post.id == post_id)
        .options(selectinload(models.Post.author))
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    return templates.TemplateResponse(
        req, "post.html", {"post": post, "title": post.title}
    )


@app.get("/posts/{user_id}/posts", include_in_schema=False, name="user-posts")
async def user_posts(
    req: Request, user_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    result = await db.execute(
        select(models.Post)
        .where(models.Post.user_id == user.id)
        .options(selectinload(models.Post.author))
    )
    posts = result.scalars().all()

    return templates.TemplateResponse(
        req, "user_posts.html", {"posts": posts, "user": user, "title": user.username}
    )


@app.post(
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.username == user.username)
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exist!"
        )

    result = await db.execute(
        select(models.User).where(models.User.email == user.email)
    )
    existing_email = result.scalars().first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exist!"
        )

    new_user = models.User(**user.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    return user


@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    result = await db.execute(
        select(models.Post)
        .where(models.Post.user_id == user.id)
        .options(selectinload(models.Post.author))
    )
    posts = result.scalars().all()

    return posts


@app.patch("/api/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, post_update: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    if post_update.username is not None and post_update.username != user.username:
        result = await db.execute(
            select(models.User).where(models.User.username == post_update.username)
        )
        existing_username = result.scalars().first()

        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already exist!",
            )

    if post_update.email is not None and post_update.email != user.email:
        result = await db.execute(
            select(models.User).where(models.User.email == post_update.email)
        )
        existing_email = result.scalars().first()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already exist!",
            )

    update_data = post_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return user


@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    await db.delete(user)
    await db.commit()


@app.post(
    "/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED
)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == post.user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    new_post = models.Post(**post.model_dump())
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])

    return new_post


@app.get("/api/posts", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post)
        .order_by(models.Post.date_posted.desc())
        .options(selectinload(models.Post.author))
    )
    posts = result.scalars().all()
    return posts


@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(
    db: Annotated[AsyncSession, Depends(get_db)],
    post_id: int = Path(..., gt=0, description="Get individual post by post id"),
):
    result = await db.execute(
        select(models.Post)
        .where(models.Post.id == post_id)
        .options(selectinload(models.Post.author))
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    return post


@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int, post_update: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        select(models.Post)
        .where(models.Post.id == post_id)
        .options(selectinload(models.Post.author))
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    post.title = post_update.title
    post.content = post_update.content

    await db.commit()
    await db.refresh(post, attribute_names=["author"])

    return post


@app.patch("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_partial(
    post_id: int, post_update: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    if not post_update.title and not post_update.content:
        return {"success": True, "message": "post updated!"}

    result = await db.execute(
        select(models.Post)
        .where(models.Post.id == post_id)
        .options(selectinload(models.Post.author))
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    update_data = post_update.model_dump(exclude_unset=True)
    for filed, value in update_data.items():
        setattr(post, filed, value)

    await db.commit()
    await db.refresh(post, attribute_names=["author"])

    return post


@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    await db.delete(post)
    await db.commit()


# response_class=HTMLResponse mean tells fastapi what type of http response will be provide
# @app.get("/about", response_class=HTMLResponse, include_in_schema=False)
# @app.get("/contact", response_class=HTMLResponse, include_in_schema=False)
# async def about() -> str:
#     return "<h1>Welcome to our app!</h1>"


# Handle all HTTP exceptions starlette raises,
# including 404 errors, and return a JSON response for API requests and an HTML response for web requests.
@app.exception_handler(StarletteHTTPException)
async def general_exception_handler(req: Request, exc: StarletteHTTPException):
    # If the request path starts with "/api", return a JSON response with the error details.
    if req.url.path.startswith("/api"):
        return await http_exception_handler(req, exc)

    message = (
        exc.detail
        if exc.detail
        else "An error occurred. Please check your request and try again!"
    )

    # Otherwise, return an HTML response with the error details.
    return templates.TemplateResponse(
        req,
        "error.html",
        {"status_code": exc.status_code, "title": exc.status_code, "message": message},
        status_code=exc.status_code,
    )


# Handle request validation errors raised by FastAPI and return a JSON response for API requests and an HTML response for web requests.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(req: Request, exc: RequestValidationError):
    # If the request path starts with "/api", return a JSON response with the validation error details.
    if req.url.path.startswith("/api"):
        return await request_validation_exception_handler(req, exc)

    # Otherwise, return an HTML response with the validation error details.
    return templates.TemplateResponse(
        req,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "title": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": exc.errors()[0]["msg"]
            if exc.errors()
            else "Validation error occurred.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
