"""
news_sources.py

Definisce alcune sorgenti di notizie sull'AI e funzioni
per estrarre titolo + testo grezzo da ciascuna entry.
"""

from typing import List, Dict
import feedparser


AI_FEEDS = [
    # Major AI Labs & Research
    "https://openai.com/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://ai.googleblog.com/feeds/posts/default",
    "https://www.anthropic.com/news/rss.xml",
    "https://www.deepmind.com/blog/rss.xml",
    "https://blog.research.google/feeds/posts/default",
    
    # LLM & ML Tools/Frameworks
    "https://blog.langchain.dev/rss.xml",
    "https://ollama.com/blog/rss.xml",
    "https://alphasignal.ai/rss.xml",
    "https://pytorch.org/blog/feed.xml",
    "https://blog.tensorflow.org/feeds/posts/default",
    
    # AI News & Analysis (English)
    "https://techcrunch.com/tag/artificial-intelligence/feed/",
    "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "https://arstechnica.com/tag/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    
    # Italian Tech & AI News
    "https://www.hwupgrade.it/rss/news.xml",
    "https://www.tomshw.it/feed/",
    "https://www.dday.it/rss",
    "https://www.punto-informatico.it/feed/",
    
    # Developer & OSS AI
    "https://github.blog/category/ai-and-ml/feed/",
    "https://news.ycombinator.com/rss",
    
    # Hardware (AI/ML focused, limited)
    "https://www.tomshardware.com/tag/artificial-intelligence/feed/",
    "https://www.anandtech.com/rss/",
]


def fetch_raw_news(limit_per_feed: int = 5) -> List[Dict[str, str]]:
    """
    Ritorna una lista di dict:
      { "title": ..., "text": ..., "link": ..., "image_url": ... }
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

            # Try to extract image from various RSS fields
            image_url = None
            if hasattr(entry, "media_content") and entry.media_content:
                image_url = entry.media_content[0].get("url")
            elif hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                image_url = entry.media_thumbnail[0].get("url")
            elif hasattr(entry, "enclosures") and entry.enclosures:
                for enclosure in entry.enclosures:
                    if enclosure.get("type", "").startswith("image/"):
                        image_url = enclosure.get("href")
                        break
            elif hasattr(entry, "image") and entry.image:
                image_url = entry.image.get("href")

            if not title or not text:
                continue

            items.append(
                {
                    "title": title,
                    "text": text,
                    "link": link,
                    "image_url": image_url or "",
                }
            )

    return items
