"""
news_sources.py

Definisce alcune sorgenti di notizie sull'AI e funzioni
per estrarre titolo + testo grezzo da ciascuna entry.
"""

from typing import List, Dict, Optional
import feedparser
import requests
from bs4 import BeautifulSoup
import re


# AI/LLM/ML related keywords for content filtering
AI_KEYWORDS = [
    # Core AI/ML terms
    'artificial intelligence', 'ai', 'machine learning', 'ml', 'deep learning',
    'neural network', 'transformer', 'attention mechanism',
    
    # LLM specific
    'llm', 'large language model', 'language model', 'gpt', 'bert', 'claude',
    'chatbot', 'chat', 'conversational ai', 'generative ai', 'gen ai',
    
    # Popular models
    'chatgpt', 'gemini', 'llama', 'mistral', 'falcon', 'phi', 'qwen',
    'openai', 'anthropic', 'deepmind', 'hugging face',
    
    # ML/AI techniques
    'training', 'fine-tuning', 'inference', 'prompt', 'embedding',
    'rag', 'retrieval augmented', 'vector database', 'semantic search',
    
    # Frameworks & tools
    'pytorch', 'tensorflow', 'langchain', 'ollama', 'huggingface',
    'transformers', 'diffusion', 'stable diffusion',
    
    # Applications
    'computer vision', 'nlp', 'natural language', 'text generation',
    'image generation', 'multimodal', 'speech recognition',
    
    # Hardware for AI
    'gpu', 'tpu', 'ai chip', 'nvidia', 'cuda', 'inference engine',
    'ai accelerator', 'neural processing'
]


def is_ai_related(title: str, text: str) -> bool:
    """
    Check if article content is related to AI/LLM/ML.
    Returns True if relevant keywords are found.
    """
    combined = (title + " " + text).lower()
    
    # Check for AI keywords
    for keyword in AI_KEYWORDS:
        if keyword in combined:
            return True
    
    return False


def upgrade_image_url(url: str) -> str:
    """
    Try to upgrade image URL to higher resolution version.
    Many sites use predictable patterns for different image sizes.
    """
    if not url:
        return url
    
    # Replace common small size indicators with large ones
    replacements = [
        ('150x150', '1200x675'),
        ('300x200', '1200x675'),
        ('300x169', '1200x675'),
        ('600x338', '1200x675'),
        ('640x360', '1920x1080'),
        ('768x432', '1920x1080'),
        ('-thumb', '-large'),
        ('-small', '-large'),
        ('-medium', '-large'),
        ('_thumb', '_large'),
        ('_small', '_large'),
        ('_medium', '_large'),
        ('/thumbs/', '/images/'),
        ('/small/', '/large/'),
        ('?w=300', '?w=1200'),
        ('?w=600', '?w=1200'),
        ('?width=300', '?width=1200'),
        ('?width=600', '?width=1200'),
    ]
    
    upgraded = url
    for old, new in replacements:
        if old in upgraded:
            upgraded = upgraded.replace(old, new)
            print(f"  [IMAGE UPGRADE] {old} -> {new}")
            break
    
    return upgraded


def is_high_quality_image(url: str) -> bool:
    """
    Check if image URL suggests high quality (not a thumbnail).
    """
    if not url:
        return False
    
    url_lower = url.lower()
    
    # Reject obvious low-quality indicators
    bad_indicators = ['thumb', '150x', '300x', '320x', '480x', 'small', 'icon', 'avatar', 'logo']
    for indicator in bad_indicators:
        if indicator in url_lower:
            return False
    
    # Accept good quality indicators
    good_indicators = ['1200', '1920', '2048', 'large', 'full', 'original', 'hero']
    for indicator in good_indicators:
        if indicator in url_lower:
            return True
    
    # Default to acceptable if no clear indicators
    return True


AI_FEEDS = [
    # Major AI Labs & Research (100% AI-focused)
    "https://openai.com/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://ai.googleblog.com/feeds/posts/default",
    "https://www.anthropic.com/news/rss.xml",
    "https://www.deepmind.com/blog/rss.xml",
    "https://blog.research.google/feeds/posts/default",
    "https://www.microsoft.com/en-us/research/feed/",
    
    # LLM & ML Tools/Frameworks (100% AI-focused)
    "https://blog.langchain.dev/rss.xml",
    "https://ollama.com/blog/rss.xml",
    "https://pytorch.org/blog/feed.xml",
    "https://blog.tensorflow.org/feeds/posts/default",
    
    # AI News & Analysis - English (AI-specific feeds)
    "https://techcrunch.com/tag/artificial-intelligence/feed/",
    "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "https://arstechnica.com/tag/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "https://www.artificialintelligence-news.com/feed/",
    
    # Developer & OSS AI
    "https://github.blog/category/ai-and-ml/feed/",
    
    # Hardware - AI specific only
    "https://www.tomshardware.com/tag/artificial-intelligence/feed/",
    
    # Academic & Research
    "https://arxiv.org/rss/cs.AI",
    "https://arxiv.org/rss/cs.LG",
    "https://arxiv.org/rss/cs.CL",
]


def extract_high_res_image(url: str) -> Optional[str]:
    """
    Scrape the actual article page to find high-resolution images.
    Prioritizes highest quality sources and replaces small images with larger versions.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Priority 1: Open Graph image with high-res preference
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image['content']
            # Try to upgrade to larger version if URL contains size indicators
            img_url = upgrade_image_url(img_url)
            if is_high_quality_image(img_url):
                return img_url
        
        # Priority 2: Twitter Card large image  
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'}) or soup.find('meta', attrs={'name': 'twitter:image:src'})
        if twitter_image and twitter_image.get('content'):
            img_url = upgrade_image_url(twitter_image['content'])
            if is_high_quality_image(img_url):
                return img_url
        
        # Priority 3: Look for hero/featured image in article
        hero_selectors = [
            'article img',
            '.article-image img',
            '.featured-image img',
            '.hero-image img',
            '.post-thumbnail img',
            'figure img',
        ]
        
        for selector in hero_selectors:
            hero = soup.select_one(selector)
            if hero:
                src = hero.get('src') or hero.get('data-src') or hero.get('data-lazy-src')
                if src:
                    src = upgrade_image_url(src)
                    if is_high_quality_image(src):
                        from urllib.parse import urljoin
                        return urljoin(url, src)
        
        # Priority 4: Find the largest image in content
        images = soup.find_all('img')
        best_image = None
        max_size = 0
        
        for img in images:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if not src:
                continue
            
            # Skip definitely small images
            if any(skip in src.lower() for skip in ['icon', 'logo', 'avatar', 'gravatar', '32x32', '64x64']):
                continue
            
            # Get dimensions
            width = img.get('width') or img.get('data-width')
            height = img.get('height') or img.get('data-height')
            
            if width and height:
                try:
                    size = int(width) * int(height)
                    if size > max_size and size >= 400*300:  # Minimum quality threshold
                        max_size = size
                        best_image = src
                except:
                    pass
            elif not best_image:
                best_image = src
        
        # Make relative URLs absolute
        if best_image and not best_image.startswith('http'):
            from urllib.parse import urljoin
            best_image = urljoin(url, best_image)
        
        return best_image
    except Exception as e:
        print(f"Error scraping image from {url}: {e}")
        return None


def get_best_image_url(entry, article_url: str) -> Optional[str]:
    """
    Extract the best quality image from RSS entry or scrape the article page.
    Always tries to upgrade image quality before returning.
    """
    image_url = None
    
    # Try to extract high-res image from RSS feed first
    if hasattr(entry, "media_content") and entry.media_content:
        # Look for the largest media content (prefer 1200+ width)
        best_width = 0
        for media in entry.media_content:
            url = media.get("url")
            width = int(media.get("width", 0) or 0)
            if url and width > best_width:
                best_width = width
                image_url = url
    
    # Try media_thumbnail only if no media_content found
    if not image_url and hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        for thumb in entry.media_thumbnail:
            url = thumb.get("url")
            if url:
                # Try to upgrade thumbnail URL
                image_url = upgrade_image_url(url)
                break
    
    # Check enclosures (upgrade if found)
    if not image_url and hasattr(entry, "enclosures") and entry.enclosures:
        for enclosure in entry.enclosures:
            if enclosure.get("type", "").startswith("image/"):
                enclosure_url = upgrade_image_url(enclosure.get("href"))
                if is_high_quality_image(enclosure_url):
                    return enclosure_url
    
    # Check image element (upgrade if found)
    if not image_url and hasattr(entry, "image") and entry.image:
        img_url = upgrade_image_url(entry.image.get("href"))
        if is_high_quality_image(img_url):
            return img_url
    
    # Always scrape if RSS image is low quality or missing
    if not image_url or not is_high_quality_image(image_url):
        scraped_image = extract_high_res_image(article_url)
        if scraped_image:
            return scraped_image
    
    return image_url


def fetch_raw_news(limit_per_feed: int = 5) -> List[Dict[str, str]]:
    """
    Ritorna una lista di dict:
      { "title": ..., "text": ..., "link": ..., "image_url": ... }
    per tutte le sorgenti definite in AI_FEEDS.
    Filters content to ensure it's AI/LLM/ML related.
    """
    items: List[Dict[str, str]] = []
    filtered_count = 0

    for feed_url in AI_FEEDS:
        parsed = feedparser.parse(feed_url)
        feed_items = 0
        
        for entry in parsed.entries:
            # Stop if we have enough items from this feed
            if feed_items >= limit_per_feed:
                break
                
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
            
            # Filter: Only include AI/LLM/ML related content
            if not is_ai_related(title, text):
                filtered_count += 1
                print(f"  [FILTERED] Non-AI content: {title[:60]}...")
                continue

            # Extract high-resolution image
            image_url = get_best_image_url(entry, link)

            items.append(
                {
                    "title": title,
                    "text": text,
                    "link": link,
                    "image_url": image_url or "",
                }
            )
            feed_items += 1

    print(f"\nTotal articles: {len(items)}, Filtered out: {filtered_count}")
    return items
