"""
news_sources.py

Definisce alcune sorgenti di notizie sull'AI e funzioni
per estrarre titolo + testo grezzo da ciascuna entry.
"""

from typing import List, Dict
import feedparser


AI_FEEDS = [
    "https://openai.com/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://ai.googleblog.com/feeds/posts/default",
]


def fetch_raw_news(limit_per_feed: int = 5) -> List[Dict[str, str]]:
    """
    Ritorna una lista di dict:
      { "title": ..., "text": ..., "link": ... }
    per tutte le sorgenti definite in AI_FEEDS.
    """
    items: List[Dict[str, str]] = []

    for feed_url in AI_FEEDS:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries[:limit_per_feed]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            summary = getattr(entry, "summary", "")
            content = ""
            if hasattr(entry, "content"):
                blocks = getattr(entry, "content", [])
                if blocks:
                    content = blocks[0].get("value", "")
            text = (content or summary or "").strip()

            if not title or not text:
                continue

            items.append(
                {
                    "title": title,
                    "text": text,
                    "link": link,
                }
            )

    return items
