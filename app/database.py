# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Default: sqlite locale, ma se c'è DATABASE_URL usiamo quello (es. Postgres)
# Se usi Postgres in Docker, la URL sarà tipo:
# postgresql+psycopg2://llmobs_user:llmobs_pass@db:5432/llmobs_db
# Se usi Postgres in local e la app in Docker, la URL sarà tipo:
# postgresql+psycopg2://user:pass@host.docker.internal:5432/db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./llm_observatory.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL, connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
