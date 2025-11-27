from typing import Optional
import os
import subprocess
import logging

from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .database import Base, engine, get_db, SessionLocal
from . import crud, models, rag

# ---------------------------------------------------------------------------
# DB INIT
# ---------------------------------------------------------------------------

Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# APP & STATIC / TEMPLATES
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Observer")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# ---------------------------------------------------------------------------
# LOGGER & SCHEDULER
# ---------------------------------------------------------------------------

logger = logging.getLogger("ai_observer")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)

scheduler = AsyncIOScheduler()


def run_ingest_job():
    """
    Job schedulato: lancia lo script di ingest delle news.
    Usa lo stesso script che avviavi a mano: scripts/fetch_and_generate.py
    e, se va bene, ricostruisce l'indice RAG.
    """
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
            # Dopo un ingest riuscito, ricostruiamo l'indice RAG
            try:
                db = SessionLocal()
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
def read_home(request: Request, db: Session = Depends(get_db)):
    articles = crud.get_latest_articles(db, limit=20)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "articles": articles,
            "page_title": "AI Observer - Home",
        },
    )


@app.get("/article/{slug}", response_class=HTMLResponse)
def read_article(slug: str, request: Request, db: Session = Depends(get_db)):
    article = crud.get_article_by_slug(db, slug)
    if not article:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "article_detail.html",
        {
            "request": request,
            "article": article,
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
    db: Session = Depends(get_db),
):
    query = (q or "").strip()
    articles = []
    if query:
        articles = crud.search_articles(db, query=query, limit=50)

    return templates.TemplateResponse(
        "search_results.html",
        {
            "request": request,
            "articles": articles,
            "query": query,
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
