# FastAPI Blog App: Learning Journey

This repository is a hands-on path for learning FastAPI by building a blog API. Work through the stages in order, testing each feature in the interactive API docs as you go.

## Roadmap

1. **Create the app:** Set up a Python virtual environment, install FastAPI and Uvicorn, and create a `FastAPI` application.
2. **Add routes:** Build a health check and endpoints to list and retrieve blog posts. Try path and query parameters.
3. **Validate data:** Define Pydantic request and response models for posts. Experiment with valid and invalid requests.
4. **Implement CRUD:** Add create, read, update, and delete operations. Start with in-memory data, then add database persistence.
5. **Structure the project:** Split routers, schemas, models, and database logic into modules. Learn dependency injection.
6. **Test and handle errors:** Use appropriate HTTP status codes and write endpoint tests with `pytest` and FastAPI's `TestClient`.
7. **Add authentication:** When the core API works, add user accounts, password hashing, and protected endpoints.
8. **Prepare for deployment:** Move configuration to environment variables and deploy the application.

## Getting started

Use Python 3.10 or newer. Create and activate a virtual environment, then install the project's dependencies. If starting from scratch:

```bash
python -m venv .venv
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS/Linux
source .venv/bin/activate
```

```bash
pip install fastapi uvicorn
```

Once the app module exists, start the development server. Replace `main:app` with the module and application variable used in this project:

```bash
uvicorn main:app --reload
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to explore and try the API. FastAPI also provides [ReDoc](http://127.0.0.1:8000/redoc).

## Suggested API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check that the API is running |
| `GET` | `/posts` | List posts; later add filtering and pagination |
| `GET` | `/posts/{post_id}` | Retrieve one post |
| `POST` | `/posts` | Create a post |
| `PUT` | `/posts/{post_id}` | Update a post |
| `DELETE` | `/posts/{post_id}` | Delete a post |

## Tips for learning

- Build one feature at a time and verify it through `/docs`.
- Pay attention to type hints, validation errors, and HTTP status codes.
- Add tests as you introduce features, rather than waiting until the end.
- Keep notes on what you learn about Pydantic, dependencies, async functions, and database sessions.

## Resources

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Python tutorial](https://docs.python.org/3/tutorial/)
- [Pydantic documentation](https://docs.pydantic.dev/)
