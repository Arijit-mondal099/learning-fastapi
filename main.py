from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "hello world"}


# response_class=HTMLResponse mean tells fastapi what type of http response will be provide
@app.get("/about", response_class=HTMLResponse, include_in_schema=False)
@app.get("/contact", response_class=HTMLResponse, include_in_schema=False)
async def about() -> str:
    return "<h1>Welcome to our app!</h1>"
