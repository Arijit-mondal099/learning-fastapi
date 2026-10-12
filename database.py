from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URI = "sqlite:///./blog.db"


# SQLAlchemy engine that manages database connections
engine = create_engine(
    DATABASE_URI, 
    connect_args={"check_same_thread": False}
)

# Session factory to create session/db
SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False
)


# DeclarativeBase provides SQLAlchemy's declarative mapping system
class Base(DeclarativeBase):
    pass


# Dependency that provide db/session for each request
# and ensure that db/session is closed afterward
def get_db():
    with SessionLocal() as db:
        yield db
