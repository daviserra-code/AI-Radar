from typing import Optional
import os
import subprocess
import logging
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app import models, crud, rag, auth, database
from app.database import engine, SessionLocal
from app.middleware import SecurityHeadersMiddleware, RateLimitMiddleware
from app.routers import auth as auth_router
from app.routers import articles as articles_router
from app.routers import comments as comments_router
from app.routers import admin as admin_router
from app.dependencies import templates


# Template filters/globals
templates.env.globals["get_credibility_badge"] = crud.get_credibility_badge
templates.env.globals["get_category_icon"] = crud.get_category_icon

import markdown
import bleach

def markdown_filter(text):
    if not text:
        return ""
    # Convert markdown to HTML
    html = markdown.markdown(text, extensions=['extra', 'nl2br'])
    # Sanitize HTML
    allowed_tags = bleach.sanitizer.ALLOWED_TAGS + ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'ul', 'ol', 'li', 'code', 'pre', 'blockquote']
    allowed_attrs = bleach.sanitizer.ALLOWED_ATTRIBUTES
    return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs)

templates.env.filters["markdown"] = markdown_filter



# Initialize DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Observer")

# Add security middleware (order matters!)
# 1. HTTPS redirect (if enabled)
# app.add_middleware(HTTPSRedirectMiddleware)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. Rate limiting
rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
rate_limit_per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
app.add_middleware(RateLimitMiddleware, per_minute=rate_limit_per_minute, per_hour=rate_limit_per_hour)

# 4. Language Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class LanguageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get language from cookie, default to 'it'
        lang = request.cookies.get("preferred_language", "it")
        request.state.lang = lang
        response = await call_next(request)
        return response

app.add_middleware(LanguageMiddleware)

# Make 'lang' available in all templates
@app.middleware("http")
async def add_lang_to_template_context(request: Request, call_next):
    response = await call_next(request)
    return response

# More robust way to add global context
# We can't easily inject into TemplateResponse here without overriding, so we'll rely on Request.state.lang
# and a context processor if needed, but 'request' is already in templates.
# Let's add a global function to help templates pick the right string.
def get_lang_content(obj, attr, lang='it'):
    """Helper to get attribute based on language, fallback to default."""
    if lang == 'en':
        val = getattr(obj, f"{attr}_en", None)
        if val:
            return val
    return getattr(obj, attr, None)

templates.env.globals["get_lang_content"] = get_lang_content



# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup structured logging with rotation
from app.logging_config import setup_logging, get_logger
setup_logging()
logger = get_logger("ai_observer")

scheduler = AsyncIOScheduler()

# Track last update time and stats
last_update_time = None
last_update_articles_count = 0


def run_ingest_job():
    global last_update_time, last_update_articles_count
    logger.info("Avvio job di ingest automatico...")
    try:
        # Esegui lo script come processo separato
        result = subprocess.run(
            ["python", "scripts/fetch_and_generate.py"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("Ingest completato. Output:\n%s", result.stdout)
        
        # Aggiorna statistiche
        last_update_time = datetime.now()
        
        # Ricostruisci indice RAG
        db = SessionLocal()
        try:
            rag.rebuild_index(db)
            last_update_articles_count = crud.get_total_articles_count(db)
        finally:
            db.close()
            
    except subprocess.CalledProcessError as e:
        logger.error("Errore durante l'ingest automatico (exit code %d):\n%s", e.returncode, e.stderr)
    except Exception as e:
        logger.error("Errore generico nel job di ingest: %s", e)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    
    # Configure scheduler
    ingest_interval = int(os.getenv("INGEST_INTERVAL_MINUTES", "5"))
    scheduler.add_job(run_ingest_job, 'interval', minutes=ingest_interval)
    scheduler.start()
    logger.info("Scheduler started with interval: %d minutes", ingest_interval)
    
    # Initial RAG index build
    db = SessionLocal()
    try:
        rag.rebuild_index(db)
        global last_update_articles_count
        last_update_articles_count = crud.get_total_articles_count(db)
    except Exception as e:
        logger.error("Failed to build initial RAG index: %s", e)
    finally:
        db.close()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    scheduler.shutdown()

# Custom error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error("Internal Server Error: %s", exc)
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc)
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error: %s", exc)
    return templates.TemplateResponse("400.html", {"request": request, "error": str(exc)}, status_code=400)


# Include Routers
app.include_router(auth_router.router)
app.include_router(articles_router.router)
app.include_router(comments_router.router)
app.include_router(admin_router.router)
