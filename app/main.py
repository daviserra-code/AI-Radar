from typing import Optional
import os
import subprocess
import logging
from datetime import datetime

from fastapi import FastAPI, Depends, Request, Form, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .database import Base, engine, get_db, SessionLocal
from . import crud, models, rag, auth
from .logging_config import setup_logging, get_logger
from .middleware import RateLimitMiddleware, SecurityHeadersMiddleware, HTTPSRedirectMiddleware

# ---------------------------------------------------------------------------
# DB INIT
# ---------------------------------------------------------------------------

Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# APP & STATIC / TEMPLATES
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Observer")

# Add security middleware (order matters!)
# 1. HTTPS redirect (if enabled)
app.add_middleware(HTTPSRedirectMiddleware)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. Rate limiting
rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
rate_limit_per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
app.add_middleware(RateLimitMiddleware, per_minute=rate_limit_per_minute, per_hour=rate_limit_per_hour)

# 4. CORS middleware for API access
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# ---------------------------------------------------------------------------
# LOGGER & SCHEDULER
# ---------------------------------------------------------------------------

# Setup structured logging with rotation
setup_logging()
logger = get_logger("ai_observer")

scheduler = AsyncIOScheduler()

# Track last update time and stats
last_update_time = None
last_update_articles_count = 0


def run_ingest_job():
    """
    Job schedulato: lancia lo script di ingest delle news.
    Usa lo stesso script che avviavi a mano: scripts/fetch_and_generate.py
    e, se va bene, ricostruisce l'indice RAG.
    """
    global last_update_time, last_update_articles_count
    
    logger.info("Inizio job di ingest news (scheduler APScheduler)...")
    try:
        completed = subprocess.run(
            ["python", "scripts/fetch_and_generate.py"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            logger.error(
                "Ingest job fallito (returncode=%s):\nSTDOUT:\n%s\nSTDERR:\n%s",
                completed.returncode,
                completed.stdout,
                completed.stderr,
            )
        else:
            logger.info(
                "Ingest job completato con successo.\nSTDOUT:\n%s",
                completed.stdout,
            )
            # Update last_update_time
            last_update_time = datetime.now()
            
            # Dopo un ingest riuscito, ricostruiamo l'indice RAG
            try:
                db = SessionLocal()
                last_update_articles_count = crud.get_total_articles_count(db)
                rag.rebuild_index(db)
            except Exception as e:
                logger.exception("Errore durante rebuild_index dopo ingest: %s", e)
            finally:
                db.close()
    except Exception as e:
        logger.exception("Eccezione durante l'esecuzione di fetch_and_generate.py: %s", e)


@app.on_event("startup")
async def startup_event():
    """
    All'avvio dell'app:
    - Configura APScheduler
    - Pianifica il job di ingest periodico
    - Ricostruisce l'indice RAG una prima volta
    """
    interval_minutes_str = os.getenv("INGEST_INTERVAL_MINUTES", "360")
    try:
        interval_minutes = int(interval_minutes_str)
    except ValueError:
        interval_minutes = 360

    if interval_minutes > 0:
        scheduler.add_job(
            run_ingest_job,
            "interval",
            minutes=interval_minutes,
            id="ingest_news_job",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler avviato: ingest ogni %s minuti", interval_minutes)
    else:
        logger.warning(
            "INGEST_INTERVAL_MINUTES <= 0: scheduler disabilitato. "
            "Imposta un valore > 0 per attivarlo."
        )

    # Ricostruzione iniziale dell'indice RAG all'avvio
    try:
        db = SessionLocal()
        rag.rebuild_index(db)
    except Exception as e:
        logger.exception("Errore durante rebuild_index iniziale: %s", e)
    finally:
        db.close()


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 error page."""
    logger.warning(f"404 Not Found: {request.url}")
    return templates.TemplateResponse(
        "404.html",
        {"request": request},
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 error page."""
    logger.error(f"500 Internal Error: {request.url}", exc_info=exc)
    return templates.TemplateResponse(
        "500.html",
        {"request": request},
        status_code=500
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler."""
    logger.error(f"Unhandled exception at {request.url}: {str(exc)}", exc_info=exc)
    return templates.TemplateResponse(
        "500.html",
        {"request": request},
        status_code=500
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.warning(f"Validation error at {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )


@app.on_event("shutdown")
def shutdown_event():
    """
    Alla chiusura dell'app:
    - Ferma lo scheduler in modo pulito
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler arrestato.")


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def read_home(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    articles = crud.get_latest_articles(db, limit=20)
    category_stats = crud.get_category_stats(db)
    total_articles = crud.get_total_articles_count(db)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "articles": articles,
            "category_stats": category_stats,
            "total_articles": total_articles,
            "page_title": "AI Observer - Home",
            "current_user": current_user,
        },
    )


@app.get("/article/{slug}", response_class=HTMLResponse)
def read_article(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    article = crud.get_article_by_slug(db, slug)
    if not article:
        return RedirectResponse(url="/", status_code=302)
    comments = crud.get_comments_by_article(db, article.id)
    related = rag.get_related_articles(db, article.id, top_k=4)
    return templates.TemplateResponse(
        "article_detail.html",
        {
            "request": request,
            "article": article,
            "comments": comments,
            "related_articles": related,
            "current_user": current_user,
            "page_title": article.title,
        },
    )


@app.get("/category/{slug}", response_class=HTMLResponse)
def read_category(slug: str, request: Request, db: Session = Depends(get_db)):
    category = crud.get_category_by_slug(db, slug)
    if not category:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "category.html",
        {
            "request": request,
            "category": category,
            "articles": category.articles,
            "page_title": f"Categoria: {category.name}",
        },
    )


@app.get("/admin/new", response_class=HTMLResponse)
def new_article_form(request: Request):
    return templates.TemplateResponse(
        "admin_new.html",
        {"request": request, "page_title": "Nuovo articolo"},
    )


@app.post("/admin/new", response_class=HTMLResponse)
def create_article(
    request: Request,
    title: str = Form(...),
    summary: str = Form(""),
    content: str = Form(...),
    category_name: str = Form("Generale"),
    source_url: str = Form(""),
    editor_comment: str = Form(""),
    db: Session = Depends(get_db),
):
    crud.create_article(
        db=db,
        title=title,
        summary=summary,
        content=content,
        category_name=category_name,
        source_url=source_url or None,
        editor_comment=editor_comment or None,
        ai_generated=False,
    )
    return RedirectResponse(url="/", status_code=302)


@app.get("/search", response_class=HTMLResponse)
def search(
    request: Request,
    q: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = (q or "").strip()
    articles = []
    result_count = 0
    
    if query:
        articles = crud.search_articles_filtered(
            db, 
            query=query, 
            category_slug=category,
            source=source,
            from_date=from_date,
            to_date=to_date,
            limit=50
        )
        result_count = len(articles)
    
    # Get all categories for filter dropdown
    categories = crud.get_all_categories(db)
    
    # Get unique sources for filter dropdown
    sources = db.query(Article.source_url).filter(Article.source_url.isnot(None)).distinct().limit(20).all()
    sources = [s[0] for s in sources if s[0]]

    return templates.TemplateResponse(
        "search_results.html",
        {
            "request": request,
            "articles": articles,
            "query": query,
            "result_count": result_count,
            "categories": categories,
            "sources": sources,
            "selected_category": category,
            "selected_source": source,
            "from_date": from_date,
            "to_date": to_date,
            "page_title": f"Search: {query}" if query else "Ricerca",
        },
    )


@app.get("/ask", response_class=HTMLResponse)
def ask_observer_get(request: Request):
    """
    Pagina Ask Observatory: mostra il form di domanda.
    """
    return templates.TemplateResponse(
        "ask.html",
        {
            "request": request,
            "page_title": "Ask Observatory",
            "question": "",
            "answer": None,
            "hits": [],
        },
    )


@app.post("/ask", response_class=HTMLResponse)
def ask_observer_post(
    request: Request,
    question: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Riceve la domanda, interroga il RAG e costruisce una risposta con fonti.
    """
    q_clean = (question or "").strip()
    answer: Optional[str] = None
    hits: list[models.Article] = []

    if q_clean:
        hits = rag.get_relevant_articles(db, q_clean, top_k=4)
        answer = rag.build_answer(q_clean, hits)
    else:
        answer = "Fammi almeno una domanda con un paio di parole chiave, non un campo vuoto 🙂"

    return templates.TemplateResponse(
        "ask.html",
        {
            "request": request,
            "page_title": "Ask Observatory",
            "question": q_clean,
            "answer": answer,
            "hits": hits,
        },
    )


# ===== AUTHENTICATION ROUTES =====

@app.get("/register", response_class=HTMLResponse)
def register_get(request: Request):
    """Show registration form."""
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "page_title": "Registrazione", "error": None},
    )


@app.post("/register", response_class=HTMLResponse)
def register_post(
    request: Request,
    response: Response,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    subscribe: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Handle user registration."""
    # Check if username or email already exists
    if crud.get_user_by_username(db, username):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "page_title": "Registrazione", "error": "Username già in uso"},
        )
    if crud.get_user_by_email(db, email):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "page_title": "Registrazione", "error": "Email già registrata"},
        )
    
    # Create user
    is_subscribed = subscribe == "true"
    user = crud.create_user(db, username, email, password, is_subscribed)
    
    # Create access token and set cookie
    token = auth.create_access_token(data={"sub": user.username})
    redirect = RedirectResponse(url="/", status_code=302)
    auth.set_auth_cookie(redirect, token)
    return redirect


@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    """Show login form."""
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "page_title": "Login", "error": None},
    )


@app.post("/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle user login."""
    user = crud.authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "page_title": "Login", "error": "Username o password non validi"},
        )
    
    # Create access token and set cookie
    token = auth.create_access_token(data={"sub": user.username})
    redirect = RedirectResponse(url="/", status_code=302)
    auth.set_auth_cookie(redirect, token)
    return redirect


@app.get("/logout")
def logout():
    """Logout user."""
    redirect = RedirectResponse(url="/", status_code=302)
    auth.clear_auth_cookie(redirect)
    return redirect


# ===== COMMENT ROUTES =====

@app.post("/article/{slug}/comment")
def add_comment(
    slug: str,
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_subscribed_user),
):
    """Add a comment to an article (subscribed users only)."""
    article = crud.get_article_by_slug(db, slug)
    if not article:
        return RedirectResponse(url="/", status_code=302)
    
    crud.create_comment(db, article.id, current_user.id, content)
    return RedirectResponse(url=f"/article/{slug}", status_code=302)


@app.post("/comment/{comment_id}/delete")
def delete_comment_route(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Delete a comment (owner only)."""
    success = crud.delete_comment(db, comment_id, current_user.id)
    # Redirect back to referer or home
    return RedirectResponse(url="/", status_code=302)


# ===== LLM ON PREMISE SECTION =====

@app.get("/llm-onpremise", response_class=HTMLResponse)
def llmonpremise_home(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    """LLMOnPremise homepage: hardware-focused articles."""
    # Filter articles by hardware/infrastructure categories
    hardware_categories = ["Hardware", "Infrastructure", "GPU", "Server"]
    articles = crud.get_articles_by_categories(db, hardware_categories, limit=12)
    
    return templates.TemplateResponse(
        "onpremise_index.html",
        {
            "request": request,
            "articles": articles,
            "page_title": "LLM OnPremise - Hardware & Infrastructure",
            "current_user": current_user,
        },
    )


@app.get("/llm-onpremise/hardware", response_class=HTMLResponse)
def llmonpremise_hardware(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    """Hardware section: GPUs, servers, benchmarks."""
    articles = crud.get_articles_by_categories(db, ["Hardware", "GPU"], limit=20)
    
    return templates.TemplateResponse(
        "onpremise_hardware.html",
        {
            "request": request,
            "articles": articles,
            "page_title": "Hardware - LLM OnPremise",
            "current_user": current_user,
        },
    )


@app.get("/llm-onpremise/infrastructure", response_class=HTMLResponse)
def llmonpremise_infrastructure(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    """Infrastructure section: Kubernetes, Docker, deployment."""
    articles = crud.get_articles_by_categories(db, ["Infrastructure", "Server"], limit=20)
    
    return templates.TemplateResponse(
        "onpremise_infrastructure.html",
        {
            "request": request,
            "articles": articles,
            "page_title": "Infrastructure - LLM OnPremise",
            "current_user": current_user,
        },
    )


@app.get("/llm-onpremise/guides", response_class=HTMLResponse)
def llmonpremise_guides(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    """Setup guides and tutorials."""
    # Filter for tutorial/guide articles
    articles = crud.get_articles_with_keyword(db, "guide", limit=20)
    
    return templates.TemplateResponse(
        "onpremise_guides.html",
        {
            "request": request,
            "articles": articles,
            "page_title": "Setup Guides - LLM OnPremise",
            "current_user": current_user,
        },
    )


@app.get("/llm-onpremise/search", response_class=HTMLResponse)
def llmonpremise_search(
    request: Request,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Search within LLMOnPremise section."""
    query = (q or "").strip()
    articles = []
    if query:
        # Search only in hardware-related categories
        hardware_categories = ["Hardware", "Infrastructure", "GPU", "Server"]
        articles = crud.search_articles_in_categories(db, query, hardware_categories, limit=50)

    return templates.TemplateResponse(
        "onpremise_search.html",
        {
            "request": request,
            "articles": articles,
            "query": query,
            "page_title": f"Search: {query}" if query else "Search Hardware",
        },
    )


# ===== RSS FEEDS =====

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint for Docker healthcheck and monitoring.
    Returns basic status information.
    """
    try:
        # Check database connectivity
        total_articles = crud.get_total_articles_count(db)
        category_stats = crud.get_category_stats(db)
        total_categories = len(category_stats)
        
        # Build response
        response = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "articles": total_articles,
            "categories": total_categories,
            "scheduler": "running" if scheduler.running else "stopped"
        }
        
        if last_update_time:
            response["last_update"] = last_update_time.isoformat()
            response["last_update_articles"] = last_update_articles_count
        
        return response
    except Exception as e:
        logger.exception("Health check failed: %s", e)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@app.get("/api/metrics")
def metrics(db: Session = Depends(get_db)):
    """
    Detailed metrics endpoint for monitoring and analytics.
    Provides comprehensive statistics about the system.
    """
    try:
        # Database stats
        total_articles = crud.get_total_articles_count(db)
        category_stats = crud.get_category_stats(db)
        popular_tags = crud.get_popular_tags(db, limit=10)
        
        # Calculate articles by day (last 7 days)
        from sqlalchemy import func, cast, Date
        articles_by_day = db.query(
            cast(models.Article.created_at, Date).label('date'),
            func.count(models.Article.id).label('count')
        ).group_by(
            cast(models.Article.created_at, Date)
        ).order_by(
            cast(models.Article.created_at, Date).desc()
        ).limit(7).all()
        
        # Build response
        response = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "database": {
                "status": "connected",
                "articles": {
                    "total": total_articles,
                    "ai_generated": db.query(models.Article).filter(models.Article.ai_generated == True).count(),
                    "by_day": [
                        {"date": str(row.date), "count": row.count}
                        for row in articles_by_day
                    ]
                },
                "categories": {
                    "total": len(category_stats),
                    "stats": category_stats
                },
                "tags": {
                    "total": db.query(models.Tag).count(),
                    "popular": popular_tags
                },
                "users": db.query(models.User).count() if hasattr(models, 'User') else 0,
                "comments": db.query(models.Comment).count() if hasattr(models, 'Comment') else 0,
                "newsletter_subscribers": db.query(models.NewsletterSubscriber).count() if hasattr(models, 'NewsletterSubscriber') else 0
            },
            "scheduler": {
                "status": "running" if scheduler.running else "stopped",
                "last_update": last_update_time.isoformat() if last_update_time else None,
                "last_update_articles": last_update_articles_count,
                "fetch_interval_minutes": int(os.getenv("FETCH_INTERVAL_MINUTES", "5"))
            },
            "ollama": {
                "host": os.getenv("OLLAMA_HOST", "http://ollama:11434"),
                "model": os.getenv("OLLAMA_MODEL", "llama3.2:latest")
            },
            "rate_limiting": {
                "enabled": os.getenv("RATE_LIMIT_ENABLED", "true") == "true",
                "per_minute": int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
                "per_hour": int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
            }
        }
        
        return response
    except Exception as e:
        logger.exception("Metrics collection failed: %s", e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@app.get("/rss", response_class=PlainTextResponse)
def rss_feed(db: Session = Depends(get_db)):
    """RSS feed for AI-Radar articles."""
    articles = crud.get_latest_articles(db, limit=50)
    
    items = []
    for article in articles:
        pub_date = article.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
        description = article.summary[:500] if article.summary else article.content[:500]
        
        items.append(f"""
    <item>
        <title><![CDATA[{article.title}]]></title>
        <link>http://ai-radar.it/article/{article.slug}</link>
        <guid>http://ai-radar.it/article/{article.slug}</guid>
        <pubDate>{pub_date}</pubDate>
        <description><![CDATA[{description}...]]></description>
        <category>{article.category.name}</category>
        {f'<enclosure url="{article.image_url}" type="image/jpeg" />' if article.image_url else ''}
    </item>""")
    
    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
        <title>AI-RADAR.it - AI News & Analysis</title>
        <link>http://ai-radar.it</link>
        <description>Latest news on LLMs, AI frameworks, and on-premise solutions</description>
        <language>it</language>
        <lastBuildDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</lastBuildDate>
        <atom:link href="http://ai-radar.it/rss" rel="self" type="application/rss+xml" />
        {''.join(items)}
    </channel>
</rss>"""
    
    return rss_xml


@app.get("/llm-onpremise/rss", response_class=PlainTextResponse)
def llmonpremise_rss_feed(db: Session = Depends(get_db)):
    """RSS feed for LLMOnPremise hardware articles."""
    hardware_categories = ["Hardware", "Infrastructure", "GPU", "Server"]
    articles = crud.get_articles_by_categories(db, hardware_categories, limit=50)
    
    items = []
    for article in articles:
        pub_date = article.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
        description = article.summary[:500] if article.summary else article.content[:500]
        
        items.append(f"""
    <item>
        <title><![CDATA[{article.title}]]></title>
        <link>http://llmonpremise.com/article/{article.slug}</link>
        <guid>http://llmonpremise.com/article/{article.slug}</guid>
        <pubDate>{pub_date}</pubDate>
        <description><![CDATA[{description}...]]></description>
        <category>{article.category.name}</category>
        {f'<enclosure url="{article.image_url}" type="image/jpeg" />' if article.image_url else ''}
    </item>""")
    
    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
        <title>LLMOnPremise - Hardware & Infrastructure</title>
        <link>http://llmonpremise.com</link>
        <description>On-premise LLM hardware, server configurations, and infrastructure guides</description>
        <language>it</language>
        <lastBuildDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</lastBuildDate>
        <atom:link href="http://llmonpremise.com/rss" rel="self" type="application/rss+xml" />
        {''.join(items)}
    </channel>
</rss>"""
    
    return rss_xml


@app.post("/newsletter/subscribe")
def newsletter_subscribe(
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """Subscribe to newsletter."""
    try:
        email = email.strip().lower()
        if not email or '@' not in email:
            return {"success": False, "message": "Email non valida"}
        
        subscriber = crud.subscribe_to_newsletter(db, email)
        logger.info(f"New newsletter subscription: {email}")
        
        return {
            "success": True,
            "message": "✅ Iscrizione completata! Riceverai aggiornamenti settimanali."
        }
    except Exception as e:
        logger.exception(f"Newsletter subscription error: {e}")
        return {"success": False, "message": "Errore durante l'iscrizione"}


@app.get("/newsletter/unsubscribe")
def newsletter_unsubscribe(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Unsubscribe from newsletter using token."""
    success = crud.unsubscribe_from_newsletter(db, token)
    
    return templates.TemplateResponse(
        "newsletter_unsubscribe.html",
        {
            "request": request,
            "success": success,
            "page_title": "Cancellazione Newsletter"
        }
    )


@app.get("/tags")
def list_tags(request: Request, db: Session = Depends(get_db)):
    """List all tags with article counts."""
    popular_tags = crud.get_popular_tags(db, limit=50)
    
    return templates.TemplateResponse(
        "tags.html",
        {
            "request": request,
            "tags": popular_tags,
            "page_title": "Tags"
        }
    )


@app.get("/tag/{tag_slug}", response_class=HTMLResponse)
def read_tag(
    tag_slug: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Display articles filtered by tag."""
    articles = crud.get_articles_by_tag(db, tag_slug, limit=50)
    tag = db.query(models.Tag).filter(models.Tag.slug == tag_slug).first()
    
    if not tag:
        return RedirectResponse("/tags", status_code=302)
    
    return templates.TemplateResponse(
        "tag_articles.html",
        {
            "request": request,
            "tag": tag,
            "articles": articles,
            "page_title": f"Tag: {tag.name}"
        }
    )


# ===== API ENDPOINTS =====

@app.get("/api/articles")
def api_get_articles(
    limit: int = 20,
    offset: int = 0,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """API endpoint to get articles with pagination."""
    query = db.query(models.Article)
    
    if category:
        query = query.join(models.Category).filter(models.Category.slug == category)
    
    total = query.count()
    articles = query.order_by(models.Article.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "slug": a.slug,
                "summary": a.summary,
                "category": a.category.name if a.category else None,
                "category_slug": a.category.slug if a.category else None,
                "created_at": a.created_at.isoformat(),
                "image_url": a.image_url,
                "source_url": a.source_url,
                "ai_generated": a.ai_generated,
                "tags": [{"name": t.name, "slug": t.slug} for t in a.tags]
            }
            for a in articles
        ]
    }


@app.get("/api/article/{slug}")
def api_get_article(slug: str, db: Session = Depends(get_db)):
    """API endpoint to get a single article by slug."""
    article = crud.get_article_by_slug(db, slug)
    
    if not article:
        return {"error": "Article not found"}, 404
    
    return {
        "id": article.id,
        "title": article.title,
        "title_en": article.title_en,
        "slug": article.slug,
        "summary": article.summary,
        "summary_en": article.summary_en,
        "content": article.content,
        "content_en": article.content_en,
        "category": article.category.name if article.category else None,
        "category_slug": article.category.slug if article.category else None,
        "created_at": article.created_at.isoformat(),
        "updated_at": article.updated_at.isoformat(),
        "image_url": article.image_url,
        "source_url": article.source_url,
        "ai_generated": article.ai_generated,
        "tags": [{"name": t.name, "slug": t.slug} for t in article.tags]
    }


@app.get("/api/search")
def api_search(
    q: str,
    limit: int = 20,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """API endpoint for article search."""
    if not q or not q.strip():
        return {"error": "Query parameter 'q' is required"}, 400
    
    articles = crud.search_articles_filtered(
        db,
        query=q.strip(),
        category_slug=category,
        limit=limit
    )
    
    return {
        "query": q,
        "total": len(articles),
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "slug": a.slug,
                "summary": a.summary,
                "category": a.category.name if a.category else None,
                "category_slug": a.category.slug if a.category else None,
                "created_at": a.created_at.isoformat(),
                "image_url": a.image_url,
                "tags": [{"name": t.name, "slug": t.slug} for t in a.tags]
            }
            for a in articles
        ]
    }


@app.get("/api/categories")
def api_get_categories(db: Session = Depends(get_db)):
    """API endpoint to get all categories with stats."""
    stats = crud.get_category_stats(db)
    return {
        "total": len(stats),
        "categories": stats
    }


@app.get("/api/tags")
def api_get_tags(limit: int = 50, db: Session = Depends(get_db)):
    """API endpoint to get popular tags."""
    tags = crud.get_popular_tags(db, limit=limit)
    return {
        "total": len(tags),
        "tags": tags
    }


@app.get("/api/docs", response_class=HTMLResponse)
def api_documentation(request: Request):
    """API documentation page."""
    return templates.TemplateResponse(
        "api_docs.html",
        {
            "request": request,
            "page_title": "API Documentation"
        }
    )
