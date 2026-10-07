from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
async def home(req: Request):
    return templates.TemplateResponse(req, "home.html", {"posts": posts})


# response_class=HTMLResponse mean tells fastapi what type of http response will be provide
# @app.get("/about", response_class=HTMLResponse, include_in_schema=False)
# @app.get("/contact", response_class=HTMLResponse, include_in_schema=False)
# async def about() -> str:
#     return "<h1>Welcome to our app!</h1>"
