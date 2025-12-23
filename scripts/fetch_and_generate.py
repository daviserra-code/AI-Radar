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


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch news and generate articles")
    parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    parser.add_argument("--limit", type=int, default=5, help="Limit articles per feed (default: 5)")
    parser.add_argument("--fast", action="store_true", help="Fast mode: Skip LLM generation, save raw articles")
    
    args = parser.parse_args()
    
    print(f"Starting ingest: {args.limit} articles/feed, last {args.days} days, fast_mode={args.fast}")
    
    db: Session = SessionLocal()
    try:
        raw_items = fetch_raw_news(limit_per_feed=args.limit, lookback_days=args.days)
        print(f"Trovate {len(raw_items)} news grezze dai feed.")

        for item in raw_items:
            link = item["link"]
            image_url = item.get("image_url", "")

            if article_exists_by_source(db, link):
                # print(f"- Già presente, skip: {link}")
                continue

            raw_title = item["title"]
            raw_text = item["text"]
            source_name = item.get("source_name", "Unknown Source")
            credibility_score = item.get("credibility_score", 3)
            
            print(f"- Elaboro [{source_name}]: {raw_title[:50]}...")

            if args.fast:
                # Fast mode: Create article directly without LLM
                try:
                    article = crud.create_article(
                        db=db,
                        title=raw_title,
                        summary=raw_text[:200] + "...", # Use start of text as summary
                        content=raw_text, # Use raw text as content
                        title_en=raw_title, # Fallback
                        summary_en=None,
                        content_en=None,
                        category_name="Altro", # Default category
                        source_url=link,
                        source_name=source_name,
                        credibility_score=credibility_score,
                        image_url=image_url if image_url else None,
                        editor_comment="IMPORTED FAST MODE (Raw Data)",
                        ai_generated=False,
                    )
                    print(f"  -> [FAST] Salvato: {article.title[:40]}...")
                except Exception as e:
                    print(f"  [ERROR] Fast save failed for {link}: {e}")
                continue

            # Slow mode: Use LLM
            try:
                article_data = ai_client.generate_article_from_news(
                    raw_title=raw_title,
                    raw_text=raw_text,
                )

                article = crud.create_article(
                    db=db,
                    title=article_data["title"],
                    summary=article_data["summary"],
                    content=article_data["content"],
                    title_en=article_data.get("title_en", ""),
                    summary_en=article_data.get("summary_en", ""),
                    content_en=article_data.get("content_en", ""),
                    category_name=article_data["category"],
                    source_url=link,
                    source_name=source_name,
                    credibility_score=credibility_score,
                    image_url=image_url if image_url else None,
                    editor_comment=None,
                    ai_generated=True,
                )
                print(f"  -> [AI] Creato articolo: {article.title} ({article.category.name})")
            except Exception as e:
                print(f"  [ERROR] Processing failed for {link}: {e}")

        print("Ingest completato.")
    finally:
        db.close()
