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
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException as StarletteHTTPException

import models
from database import engine, get_db
from routers import posts, users


# Lifespan here for app startup and shut down
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    # Startup: verify database connectivity
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    # Shutdown: release pooled connections
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

# Mount the static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

# Initialize the Jinja2Templates object with the directory containing your HTML templates
templates = Jinja2Templates(directory="templates")


# Include routers
app.include_router(prefix="/api/users", router=users.router, tags=["users"])
app.include_router(prefix="/api/posts", router=posts.router, tags=["posts"])


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def root(
    req: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    count_result = await db.execute(select(func.count()).select_from(models.Post))
    total = count_result.scalar() or 0

    # We also get author of the post from relationship
    # But in async we have to told sqlalchemy to load author as well
    result = await db.execute(
        select(models.Post)
        .order_by(models.Post.date_posted.desc())
        .options(selectinload(models.Post.author))
        .limit(10)
    )
    posts = result.scalars().all()
    has_more = len(posts) < total

    return templates.TemplateResponse(
        req, "home.html", {"posts": posts, "limit": 10, "has_more": has_more}
    )


@app.get("/register", include_in_schema=False)
async def register_page(req: Request):
    return templates.TemplateResponse(req, "register.html", {"title": "Register"})


@app.get("/login", include_in_schema=False)
async def login_page(req: Request):
    return templates.TemplateResponse(req, "login.html", {"title": "Login"})


@app.get("/account", include_in_schema=False)
async def account_page(req: Request):
    return templates.TemplateResponse(req, "account.html", {"title": "Account"})


@app.get("/forgot-password", include_in_schema=False)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        {"title": "Forgot Password"},
    )


@app.get("/reset-password", include_in_schema=False)
async def reset_password_page(request: Request):
    response = templates.TemplateResponse(
        request,
        "reset_password.html",
        {"title": "Reset Password"},
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


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

    count_result = await db.execute(
        select(func.count())
        .select_from(models.Post)
        .where(models.Post.user_id == user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .where(models.Post.user_id == user.id)
        .options(selectinload(models.Post.author))
        .limit(5)
    )
    posts = result.scalars().all()
    has_more = len(posts) < total

    return templates.TemplateResponse(
        req,
        "user_posts.html",
        {
            "posts": posts,
            "user": user,
            "title": user.username,
            "limit": 10,
            "has_more": has_more,
        },
    )


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
