from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime
from slugify import slugify

from . import models


def create_category_if_not_exists(db: Session, name: str) -> models.Category:
    slug = slugify(name)
    category = db.query(models.Category).filter_by(slug=slug).first()
    if category:
        return category
    category = models.Category(name=name, slug=slug)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def create_article(
    db: Session,
    title: str,
    summary: str,
    content: str,
    category_name: str,
    source_url: Optional[str] = None,
    image_url: Optional[str] = None,
    editor_comment: Optional[str] = None,
    ai_generated: bool = True,
) -> models.Article:
    category = create_category_if_not_exists(db, category_name)
    slug = slugify(title)

    article = models.Article(
        title=title,
        slug=slug,
        summary=summary,
        content=content,
        category_id=category.id,
        source_url=source_url,
        image_url=image_url,
        editor_comment=editor_comment,
        ai_generated=ai_generated,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def get_latest_articles(db: Session, limit: int = 20) -> List[models.Article]:
    return (
        db.query(models.Article)
        .order_by(models.Article.created_at.desc())
        .limit(limit)
        .all()
    )


def get_article_by_slug(db: Session, slug: str) -> Optional[models.Article]:
    return db.query(models.Article).filter(models.Article.slug == slug).first()


def get_category_by_slug(db: Session, slug: str) -> Optional[models.Category]:
    return db.query(models.Category).filter(models.Category.slug == slug).first()


def search_articles(db: Session, query: str, limit: int = 50) -> List[models.Article]:
    """
    Ricerca semplice case-insensitive su titolo, summary e content.
    """
    q = f"%{query}%"
    return (
        db.query(models.Article)
        .filter(
            or_(
                models.Article.title.ilike(q),
                models.Article.summary.ilike(q),
                models.Article.content.ilike(q),
            )
        )
        .order_by(models.Article.created_at.desc())
        .limit(limit)
        .all()
    )


# ===== USER MANAGEMENT =====

def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    is_subscribed: bool = False,
) -> models.User:
    """Create a new user with hashed password."""
    hashed_password = models.User.hash_password(password)
    user = models.User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        is_subscribed=is_subscribed,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Get user by username."""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get user by email."""
    return db.query(models.User).filter(models.User.email == email).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """Authenticate user with username and password."""
    user = get_user_by_username(db, username)
    if not user or not user.verify_password(password):
        return None
    return user


# ===== COMMENT MANAGEMENT =====

def create_comment(
    db: Session,
    article_id: int,
    user_id: int,
    content: str,
) -> models.Comment:
    """Create a new comment on an article."""
    comment = models.Comment(
        content=content,
        article_id=article_id,
        user_id=user_id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comments_by_article(db: Session, article_id: int) -> List[models.Comment]:
    """Get all comments for an article, ordered by creation date."""
    return (
        db.query(models.Comment)
        .filter(models.Comment.article_id == article_id)
        .order_by(models.Comment.created_at.asc())
        .all()
    )


def delete_comment(db: Session, comment_id: int, user_id: int) -> bool:
    """Delete a comment if the user owns it."""
    comment = db.query(models.Comment).filter(
        models.Comment.id == comment_id,
        models.Comment.user_id == user_id
    ).first()
    if comment:
        db.delete(comment)
        db.commit()
        return True
    return False
