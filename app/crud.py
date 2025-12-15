from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional, Dict
from datetime import datetime
from slugify import slugify

from . import models


# Source Credibility Badge Configuration
CREDIBILITY_BADGES = {
    5: {"badge": "🏆", "label": "Official AI Lab", "color": "#10b981", "class": "credibility-highest"},
    4: {"badge": "✅", "label": "Trusted Source", "color": "#3b82f6", "class": "credibility-high"},
    3: {"badge": "ℹ️", "label": "News Source", "color": "#8b5cf6", "class": "credibility-medium"},
    2: {"badge": "📝", "label": "Blog/Aggregator", "color": "#f59e0b", "class": "credibility-low"},
    1: {"badge": "⚠️", "label": "Unverified", "color": "#ef4444", "class": "credibility-lowest"},
}


def get_credibility_badge(score: int) -> Dict[str, str]:
    """Get badge information for a credibility score."""
    return CREDIBILITY_BADGES.get(score, CREDIBILITY_BADGES[3])


# Category icon mapping
CATEGORY_ICONS = {
    "llm": "🤖",
    "gpu": "⚡",
    "hardware": "💻",
    "infrastructure": "🔧",
    "server": "🖥️",
    "deployment": "🚀",
    "frameworks": "🏗️",
    "ai": "🧠",
    "ml": "📊",
    "rag": "🔍",
    "vector-db": "💾",
    "kubernetes": "☸️",
    "docker": "🐳",
    "generale": "📁",
}

CATEGORY_DESCRIPTIONS = {
    "llm": "Large Language Models e modelli generativi",
    "gpu": "Schede grafiche e acceleratori AI",
    "hardware": "Server, workstation e componenti",
    "infrastructure": "Infrastruttura e orchestrazione",
    "server": "Server e data center",
    "deployment": "Deploy e configurazione",
    "frameworks": "Framework AI/ML e tool",
    "ai": "Intelligenza Artificiale generale",
    "ml": "Machine Learning e data science",
    "rag": "Retrieval Augmented Generation",
    "vector-db": "Database vettoriali",
    "kubernetes": "Kubernetes e container orchestration",
    "docker": "Container e virtualizzazione",
    "generale": "Articoli generali",
}


def create_category_if_not_exists(db: Session, name: str) -> models.Category:
    slug = slugify(name)
    category = db.query(models.Category).filter_by(slug=slug).first()
    if category:
        return category
    
    # Assign icon and description based on name
    icon = CATEGORY_ICONS.get(slug.lower(), "📁")
    description = CATEGORY_DESCRIPTIONS.get(slug.lower(), f"Articoli su {name}")
    
    category = models.Category(name=name, slug=slug, icon=icon, description=description)
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
    source_name: Optional[str] = None,
    credibility_score: int = 3,
    image_url: Optional[str] = None,
    title_en: Optional[str] = None,
    summary_en: Optional[str] = None,
    content_en: Optional[str] = None,
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
        title_en=title_en,
        summary_en=summary_en,
        content_en=content_en,
        category_id=category.id,
        source_url=source_url,
        source_name=source_name,
        credibility_score=credibility_score,
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


def search_articles_filtered(
    db: Session,
    query: str,
    category_slug: Optional[str] = None,
    source: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 50
) -> List[models.Article]:
    """
    Advanced search with filters for category, source, and date range.
    """
    from datetime import datetime
    
    q = f"%{query}%"
    
    # Base query with text search
    query_builder = db.query(models.Article).filter(
        or_(
            models.Article.title.ilike(q),
            models.Article.summary.ilike(q),
            models.Article.content.ilike(q),
        )
    )
    
    # Apply category filter
    if category_slug:
        query_builder = query_builder.join(models.Category).filter(
            models.Category.slug == category_slug
        )
    
    # Apply source filter
    if source:
        query_builder = query_builder.filter(models.Article.source_url.ilike(f"%{source}%"))
    
    # Apply date range filters
    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            query_builder = query_builder.filter(models.Article.created_at >= from_dt)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
            to_dt = to_dt.replace(hour=23, minute=59, second=59)
            query_builder = query_builder.filter(models.Article.created_at <= to_dt)
        except ValueError:
            pass
    
    return query_builder.order_by(models.Article.created_at.desc()).limit(limit).all()


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


# ===== LLM ON PREMISE HELPERS =====

def get_articles_by_categories(
    db: Session, 
    category_names: List[str], 
    limit: int = 20
) -> List[models.Article]:
    """Get articles filtered by category names."""
    categories = db.query(models.Category).filter(
        models.Category.name.in_(category_names)
    ).all()
    category_ids = [c.id for c in categories]
    
    if not category_ids:
        return []
    
    return (
        db.query(models.Article)
        .filter(models.Article.category_id.in_(category_ids))
        .order_by(models.Article.created_at.desc())
        .limit(limit)
        .all()
    )


def get_articles_with_keyword(
    db: Session,
    keyword: str,
    limit: int = 20
) -> List[models.Article]:
    """Get articles containing a specific keyword."""
    q = f"%{keyword}%"
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


def search_articles_in_categories(
    db: Session,
    query: str,
    category_names: List[str],
    limit: int = 50
) -> List[models.Article]:
    """Search articles within specific categories."""
    categories = db.query(models.Category).filter(
        models.Category.name.in_(category_names)
    ).all()
    category_ids = [c.id for c in categories]
    
    if not category_ids:
        return []
    
    q = f"%{query}%"
    return (
        db.query(models.Article)
        .filter(
            models.Article.category_id.in_(category_ids),
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


def get_category_stats(db: Session) -> List[dict]:
    """Get article count for each category with icons."""
    from sqlalchemy import func
    
    stats = (
        db.query(
            models.Category.name,
            models.Category.slug,
            models.Category.icon,
            func.count(models.Article.id).label('count')
        )
        .join(models.Article)
        .group_by(models.Category.id, models.Category.name, models.Category.slug, models.Category.icon)
        .order_by(func.count(models.Article.id).desc())
        .all()
    )
    
    return [{"name": name, "slug": slug, "icon": icon, "count": count} for name, slug, icon, count in stats]


def get_total_articles_count(db: Session) -> int:
    """Get total number of articles."""
    return db.query(models.Article).count()


# ===== NEWSLETTER MANAGEMENT =====

def subscribe_to_newsletter(db: Session, email: str) -> models.Newsletter:
    """Subscribe an email to the newsletter."""
    import secrets
    
    # Check if already subscribed
    existing = db.query(models.Newsletter).filter(models.Newsletter.email == email).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.commit()
            db.refresh(existing)
        return existing
    
    # Create new subscription
    token = secrets.token_urlsafe(32)
    subscriber = models.Newsletter(
        email=email,
        unsubscribe_token=token
    )
    db.add(subscriber)
    db.commit()
    db.refresh(subscriber)
    return subscriber


def unsubscribe_from_newsletter(db: Session, token: str) -> bool:
    """Unsubscribe using token."""
    subscriber = db.query(models.Newsletter).filter(
        models.Newsletter.unsubscribe_token == token
    ).first()
    if subscriber:
        subscriber.is_active = False
        db.commit()
        return True
    return False


def get_active_subscribers(db: Session) -> List[models.Newsletter]:
    """Get all active newsletter subscribers."""
    return db.query(models.Newsletter).filter(models.Newsletter.is_active == True).all()


# ===== TAG MANAGEMENT =====

def create_tag(db: Session, name: str, slug: str) -> models.Tag:
    """Create a new tag."""
    tag = models.Tag(name=name, slug=slug)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def get_or_create_tag(db: Session, name: str) -> models.Tag:
    """Get existing tag or create new one."""
    from slugify import slugify
    
    slug = slugify(name)
    tag = db.query(models.Tag).filter(models.Tag.slug == slug).first()
    
    if not tag:
        tag = create_tag(db, name, slug)
    
    return tag


def get_all_tags(db: Session) -> List[models.Tag]:
    """Get all tags."""
    return db.query(models.Tag).order_by(models.Tag.name).all()


def get_popular_tags(db: Session, limit: int = 20) -> List[dict]:
    """Get most popular tags with article counts."""
    from sqlalchemy import func
    
    results = (
        db.query(
            models.Tag.name,
            models.Tag.slug,
            func.count(models.article_tags.c.article_id).label('count')
        )
        .join(models.article_tags)
        .group_by(models.Tag.id, models.Tag.name, models.Tag.slug)
        .order_by(func.count(models.article_tags.c.article_id).desc())
        .limit(limit)
        .all()
    )
    
    return [{"name": name, "slug": slug, "count": count} for name, slug, count in results]


def add_tags_to_article(db: Session, article_id: int, tag_names: List[str]):
    """Add tags to an article."""
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article:
        return
    
    for tag_name in tag_names:
        tag = get_or_create_tag(db, tag_name.strip())
        if tag not in article.tags:
            article.tags.append(tag)
    
    db.commit()


def get_articles_by_tag(db: Session, tag_slug: str, limit: int = 50) -> List[models.Article]:
    """Get articles filtered by tag."""
    return (
        db.query(models.Article)
        .join(models.article_tags)
        .join(models.Tag)
        .filter(models.Tag.slug == tag_slug)
        .order_by(models.Article.created_at.desc())
        .limit(limit)
        .all()
    )
