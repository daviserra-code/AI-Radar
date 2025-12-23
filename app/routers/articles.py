from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, Response, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import models, auth, crud, rag
from app.dependencies import templates, get_db

router = APIRouter(tags=["articles"])

@router.get("/", response_class=HTMLResponse)
async def read_home(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    articles = crud.get_latest_articles(db, limit=20)
    category_stats = crud.get_category_stats(db)
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "articles": articles,
            "category_stats": category_stats,
            "user": current_user,
        },
    )

@router.get("/article/{slug}", response_class=HTMLResponse)
async def read_article(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    article = crud.get_article_by_slug(db, slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    comments = crud.get_comments_by_article(db, article.id)
    related_articles = rag.get_related_articles(db, article_id=article.id)
    
    return templates.TemplateResponse(
        "article_detail.html",
        {
            "request": request,
            "article": article,
            "user": current_user,
            "comments": comments,
            "related_articles": related_articles,
            "credibility_badge": crud.get_credibility_badge(article.credibility_score),
            "category_icon": crud.CATEGORY_ICONS.get(article.category.slug, "📁") if article.category else "📁"
        },
    )

@router.get("/category/{slug}", response_class=HTMLResponse)
async def read_category(slug: str, request: Request, db: Session = Depends(get_db)):
    category = crud.get_category_by_slug(db, slug)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    articles = db.query(models.Article).filter(models.Article.category_id == category.id).order_by(models.Article.created_at.desc()).all()
    
    return templates.TemplateResponse(
        "category.html",
        {"request": request, "category": category, "articles": articles},
    )

@router.get("/new", response_class=HTMLResponse)
async def new_article_form(request: Request):
    return templates.TemplateResponse("new_article.html", {"request": request})

@router.post("/new", response_class=HTMLResponse)
async def create_article(
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
        source_url=source_url,
        editor_comment=editor_comment,
        ai_generated=False
    )
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

@router.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    q: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    if not q and not category and not source and not from_date and not to_date:
        return RedirectResponse(url="/")
        
    if q:
        # Use RAG for text search
        rag_results = rag.get_relevant_articles(db, question=q)
        # Fallback to DB search if RAG fails or returns empty (optional, here we rely on RAG)
        results = rag_results if rag_results else crud.search_articles(db, q)
    else:
        # Use advanced filter
        results = crud.search_articles_filtered(
            db, 
            query=q if q else "", 
            category_slug=category,
            source=source,
            from_date=from_date,
            to_date=to_date
        )
        
    return templates.TemplateResponse(
        "search_results.html",
        {
            "request": request, 
            "query": q, 
            "articles": results,
            "user": current_user
        },
    )

@router.get("/ask", response_class=HTMLResponse)
async def ask_observer_get(request: Request):
    return templates.TemplateResponse("ask.html", {"request": request})

@router.post("/ask", response_class=HTMLResponse)
async def ask_observer_post(
    request: Request,
    question: str = Form(...),
    db: Session = Depends(get_db),
):
    relevant_articles = rag.get_relevant_articles(db, question)
    answer = rag.build_answer(question, relevant_articles)
    
    return templates.TemplateResponse(
        "ask.html",
        {
            "request": request,
            "question": question,
            "answer": answer,
            "sources": relevant_articles
        },
    )
