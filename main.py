from fastapi import FastAPI, HTTPException, Path, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from schemas import PostCreate, PostResponse

app = FastAPI()

# Mount the static files directory to serve CSS, JS, and image files
app.mount("/static", StaticFiles(directory="static"), name="static")
# Initialize the Jinja2Templates object with the directory containing your HTML templates
templates = Jinja2Templates(directory="templates")


posts = [
    {
        "id": 1,
        "author": "John Doe",
        "title": "First Post",
        "content": "This is the content of the first post.",
        "date_posted": "2023-08-01",
    },
    {
        "id": 2,
        "author": "Jane Smith",
        "title": "Second Post",
        "content": "This is the content of the second post.",
        "date_posted": "2023-08-02",
    },
    {
        "id": 3,
        "author": "Alice Johnson",
        "title": "Third Post",
        "content": "This is the content of the third post.",
        "date_posted": "2023-08-03",
    },
]


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def root(req: Request):
    return templates.TemplateResponse(req, "home.html", {"posts": posts})


@app.get("/posts/{post_id}", include_in_schema=False)
def post(
    req: Request,
    post_id: int = Path(..., gt=0, desPcription="Get individual post by post id"),
):
    data = [post for post in posts if post["id"] == post_id]
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )
    title = data[0]["title"]
    return templates.TemplateResponse(
        req, "post.html", {"post": data[0], "title": title}
    )


@app.post(
    "/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED
)
async def create_post(post: PostCreate):
    new_post_id = max(post["id"] for post in posts) + 1 if posts else 1
    new_post = {
        "id": new_post_id,
        "title": post.title,
        "content": post.content,
        "author": post.author,
        "date_posted": "Octobor 12, 2026",
    }
    posts.append(new_post)
    return new_post


@app.get("/api/posts", response_model=list[PostResponse])
async def get_posts():
    return posts


@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int = Path(..., gt=0, description="Get individual post by post id"),
):
    post = [post for post in posts if post["id"] == post_id]
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )
    return post[0]


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
