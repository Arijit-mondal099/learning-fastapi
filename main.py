from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

import models
from database import Base, engine, get_db
from schemas import PostCreate, PostResponse, UserCreate, UserResponse

# Create all the tables if tables doesn't exits in the database
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Mount the static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

# Initialize the Jinja2Templates object with the directory containing your HTML templates
templates = Jinja2Templates(directory="templates")


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def root(req: Request, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).order_by(models.Post.date_posted.desc()))
    posts = result.scalars().all()

    return templates.TemplateResponse(req, "home.html", {"posts": posts})


@app.get("/posts/{post_id}", include_in_schema=False)
def post(
    req: Request,
    db: Annotated[Session, Depends(get_db)],
    post_id: int = Path(..., gt=0, desPcription="Get individual post by post id"),
):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    return templates.TemplateResponse(
        req, "post.html", {"post": post, "title": post.title}
    )


@app.get("/posts/{user_id}/posts", include_in_schema=False, name="user-posts")
def user_posts(req: Request, user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    result = db.execute(select(models.Post).where(models.Post.user_id == user.id))
    posts = result.scalars().all()

    return templates.TemplateResponse(
        req, "user_posts.html", {"posts": posts, "user": user, "title": user.username}
    )


@app.post(
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
        select(models.User).where(models.User.username == user.username)
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exist!"
        )

    result = db.execute(select(models.User).where(models.User.email == user.email))
    existing_email = result.scalars().first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exist!"
        )

    new_user = models.User(**user.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    return user


@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    result = db.execute(select(models.Post).where(models.Post.user_id == user.id))
    posts = result.scalars().all()

    return posts


@app.post(
    "/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED
)
async def create_post(post: PostCreate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == post.user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    new_post = models.Post(**post.model_dump())
    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return new_post


@app.get("/api/posts", response_model=list[PostResponse])
async def get_posts(db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).order_by(models.Post.date_posted.desc()))
    posts = result.scalars().all()
    return posts


@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(
    db: Annotated[Session, Depends(get_db)],
    post_id: int = Path(..., gt=0, description="Get individual post by post id"),
):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    return post


# response_class=HTMLResponse mean tells fastapi what type of http response will be provide
# @app.get("/about", response_class=HTMLResponse, include_in_schema=False)
# @app.get("/contact", response_class=HTMLResponse, include_in_schema=False)
# async def about() -> str:
#     return "<h1>Welcome to our app!</h1>"


# Handle all HTTP exceptions starlette raises,
# including 404 errors, and return a JSON response for API requests and an HTML response for web requests.
@app.exception_handler(StarletteHTTPException)
async def general_exception_handler(req: Request, exc: StarletteHTTPException):
    message = (
        exc.detail
        if exc.detail
        else "An error occurred. Please check your request and try again!"
    )

    # If the request path starts with "/api", return a JSON response with the error details.
    if req.url.path.startswith("/api"):
        return JSONResponse(status_code=exc.status_code, content={"detail": message})

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
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

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
