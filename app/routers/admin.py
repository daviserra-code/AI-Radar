from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import models, crud, auth
from app.dependencies import templates, get_db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_current_admin_user)]
)

@router.get("/users", response_class=HTMLResponse)
async def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    users = crud.get_all_users(db)
    return templates.TemplateResponse(
        "admin_users.html", 
        {"request": request, "users": users, "current_user": current_user}
    )

@router.post("/users/{user_id}/toggle-active")
async def toggle_active(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = crud.toggle_user_active(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)

@router.post("/users/{user_id}/toggle-admin")
async def toggle_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    # Prevent self-demotion to avoid locking oneself out
    if user_id == current_user.id:
        # Flash message capability would be nice here, but for now just redirect
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
        
    user = crud.toggle_user_admin(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)

@router.post("/users/{user_id}/toggle-subscription")
async def toggle_subscription(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = crud.toggle_user_subscription(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)

@router.get("/articles", response_class=HTMLResponse)
async def list_articles(
    request: Request,
    db: Session = Depends(get_db),
    page: int = 1,
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    limit = 50
    offset = (page - 1) * limit
    articles = db.query(models.Article).order_by(models.Article.created_at.desc()).offset(offset).limit(limit).all()
    total_articles = crud.get_total_articles_count(db)
    
    return templates.TemplateResponse(
        "admin_articles.html",
        {
            "request": request, 
            "articles": articles, 
            "current_user": current_user,
            "page": page,
            "total_pages": (total_articles + limit - 1) // limit
        }
    )

@router.get("/articles/{article_id}/edit", response_class=HTMLResponse)
async def edit_article_form(
    article_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    article = crud.get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    return templates.TemplateResponse(
        "admin_article_edit.html",
        {
            "request": request,
            "article": article,
            "current_user": current_user
        }
    )

from fastapi import Form
from typing import Optional

@router.post("/articles/{article_id}/edit", response_class=HTMLResponse)
async def edit_article_submit(
    article_id: int,
    request: Request,
    title: str = Form(...),
    summary: Optional[str] = Form(None),
    content: str = Form(...),
    title_en: Optional[str] = Form(None),
    summary_en: Optional[str] = Form(None),
    content_en: Optional[str] = Form(None),
    category_name: str = Form(...),
    source_url: Optional[str] = Form(None),
    source_name: Optional[str] = Form(None),
    credibility_score: int = Form(...),
    image_url: Optional[str] = Form(None),
    editor_comment: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    article = crud.update_article(
        db=db,
        article_id=article_id,
        title=title,
        summary=summary,
        content=content,
        title_en=title_en,
        summary_en=summary_en,
        content_en=content_en,
        category_name=category_name,
        source_url=source_url,
        source_name=source_name,
        credibility_score=credibility_score,
        image_url=image_url,
        editor_comment=editor_comment
    )
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    return RedirectResponse(url="/admin/articles", status_code=status.HTTP_302_FOUND)

@router.get("/new", response_class=HTMLResponse)
async def new_article_form(
    request: Request,
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    return templates.TemplateResponse("admin_new.html", {"request": request, "current_user": current_user})

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
    current_user: models.User = Depends(auth.get_current_admin_user)
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


@router.get("/glossary", response_class=HTMLResponse)
async def list_glossary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    terms = crud.get_all_glossary_terms(db)
    return templates.TemplateResponse(
        "admin_glossary.html",
        {"request": request, "terms": terms, "current_user": current_user}
    )

@router.post("/glossary", response_class=HTMLResponse)
async def add_glossary_term(
    request: Request,
    term_it: str = Form(...),
    banned_term: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    crud.create_glossary_term(db, term_it, banned_term)
    return RedirectResponse(url="/admin/glossary", status_code=status.HTTP_302_FOUND)

@router.post("/glossary/{term_id}/delete")
async def delete_glossary_term(
    term_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    crud.delete_glossary_term(db, term_id)
    return RedirectResponse(url="/admin/glossary", status_code=status.HTTP_302_FOUND)


