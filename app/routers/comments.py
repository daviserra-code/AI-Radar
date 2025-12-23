from fastapi import APIRouter, Depends, Form, status, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import models, auth, crud
from app.dependencies import get_db

router = APIRouter(tags=["comments"])

@router.post("/article/{slug}/comment")
async def add_comment(
    slug: str,
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_subscribed_user),
):
    article = db.query(models.Article).filter(models.Article.slug == slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    comment = models.Comment(
        content=content,
        user_id=current_user.id,
        article_id=article.id
    )
    db.add(comment)
    db.commit()
    
    return RedirectResponse(url=f"/article/{slug}#comments", status_code=status.HTTP_302_FOUND)

@router.post("/comment/{comment_id}/delete")
async def delete_comment_route(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
        
    # Check ownership
    if comment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    slug = comment.article.slug
    # Soft delete instead of hard delete
    crud.delete_comment(db, comment_id, current_user.id)
    
    return RedirectResponse(url=f"/article/{slug}#comments", status_code=status.HTTP_302_FOUND)


@router.post("/comment/{comment_id}/edit")
async def edit_comment_route(
    comment_id: int,
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
        
    # Check ownership
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    slug = comment.article.slug
    crud.update_comment(db, comment_id, current_user.id, content)
    
    return RedirectResponse(url=f"/article/{slug}#comments", status_code=status.HTTP_302_FOUND)
