"""
news_sources.py

Definisce alcune sorgenti di notizie sull'AI e funzioni
per estrarre titolo + testo grezzo da ciascuna entry.
"""

from typing import List, Dict
import feedparser


AI_FEEDS = [
    # Major AI Labs
    "https://openai.com/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://ai.googleblog.com/feeds/posts/default",
    "https://www.anthropic.com/news/rss.xml",
    
    # LLM & ML News
    "https://blog.langchain.dev/rss.xml",
    "https://ollama.com/blog/rss.xml",
    
    # Tech News (AI focused)
    "https://techcrunch.com/tag/artificial-intelligence/feed/",
    "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "https://arstechnica.com/tag/artificial-intelligence/feed/",
    
    # Developer/Framework News
    "https://pytorch.org/blog/feed.xml",
    "https://blog.tensorflow.org/feeds/posts/default",
    
    # Hardware & Local AI
    "https://www.tomshardware.com/feeds/all",
    "https://www.anandtech.com/rss/",
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
