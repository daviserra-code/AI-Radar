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
