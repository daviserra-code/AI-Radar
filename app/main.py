from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from . import crud, models

# Crea le tabelle al primo avvio
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LLM Observatory")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def read_home(request: Request, db: Session = Depends(get_db)):
    articles = crud.get_latest_articles(db, limit=20)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "articles": articles,
            "page_title": "LLM Observatory - Home",
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
