from fastapi.templating import Jinja2Templates
from app.database import SessionLocal

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
