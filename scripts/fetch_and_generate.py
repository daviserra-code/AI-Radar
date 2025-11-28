"""
fetch_and_generate.py

Pipeline:
1. Legge le news dai feed RSS.
2. Per ogni news, chiama il LLM (via ai_client).
3. Crea articoli nel DB usando il CRUD.
"""

import os
import sys
from sqlalchemy.orm import Session

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT_DIR)

from app.database import SessionLocal, engine
from app import models, crud
from app import ai_client
from scripts.news_sources import fetch_raw_news


models.Base.metadata.create_all(bind=engine)


def article_exists_by_source(db: Session, source_url: str) -> bool:
    return (
        db.query(models.Article)
        .filter(models.Article.source_url == source_url)
        .first()
        is not None
    )


def ingest_from_feeds():
    db: Session = SessionLocal()
    try:
        raw_items = fetch_raw_news(limit_per_feed=3)
        print(f"Trovate {len(raw_items)} news grezze dai feed.")

        for item in raw_items:
            link = item["link"]
            image_url = item.get("image_url", "")

            if article_exists_by_source(db, link):
                print(f"- Già presente, skip: {link}")
                continue

            raw_title = item["title"]
            raw_text = item["text"]
            print(f"- Elaboro: {raw_title}")

            article_data = ai_client.generate_article_from_news(
                raw_title=raw_title,
                raw_text=raw_text,
            )

            article = crud.create_article(
                db=db,
                title=article_data["title"],
                summary=article_data["summary"],
                content=article_data["content"],
                category_name=article_data["category"],
                source_url=link,
                image_url=image_url if image_url else None,
                editor_comment=None,
                ai_generated=True,
            )

            print(f"  -> Creato articolo: {article.title} ({article.category.name})")

        print("Ingest completato.")
    finally:
        db.close()


if __name__ == "__main__":
    ingest_from_feeds()
