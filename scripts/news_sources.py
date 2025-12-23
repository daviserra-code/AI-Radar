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


# Source Credibility Mapping (1-5 scale)
# 5 = Highest (Official AI Labs, Academic)
# 4 = High (Major Tech Publications)
# 3 = Medium (General Tech News)
# 2 = Lower (Aggregators, Blogs)
# 1 = Lowest (Unverified sources)
SOURCE_CREDIBILITY = {
    # AI Labs & Research - Highest credibility (5)
    "OpenAI Blog": {"score": 5, "badge": "🏆", "label": "Official AI Lab", "color": "#10b981"},
    "Anthropic News": {"score": 5, "badge": "🏆", "label": "Official AI Lab", "color": "#10b981"},
    "Google AI Blog": {"score": 5, "badge": "🏆", "label": "Official AI Lab", "color": "#10b981"},
    "HuggingFace Blog": {"score": 5, "badge": "🏆", "label": "Official AI Lab", "color": "#10b981"},
    "DeepMind Blog": {"score": 5, "badge": "🏆", "label": "Official AI Lab", "color": "#10b981"},
    "Microsoft Research": {"score": 5, "badge": "🏆", "label": "Research Lab", "color": "#10b981"},
    "ArXiv cs.AI": {"score": 5, "badge": "🎓", "label": "Academic", "color": "#10b981"},
    "ArXiv cs.LG": {"score": 5, "badge": "🎓", "label": "Academic", "color": "#10b981"},
    "ArXiv cs.CL": {"score": 5, "badge": "🎓", "label": "Academic", "color": "#10b981"},
    
    # Major Framework/Tool Providers - High credibility (4)
    "LangChain Blog": {"score": 4, "badge": "✅", "label": "Official Source", "color": "#3b82f6"},
    "Ollama Blog": {"score": 4, "badge": "✅", "label": "Official Source", "color": "#3b82f6"},
    "PyTorch Blog": {"score": 4, "badge": "✅", "label": "Official Source", "color": "#3b82f6"},
    "TensorFlow Blog": {"score": 4, "badge": "✅", "label": "Official Source", "color": "#3b82f6"},
    
    # Major Tech Publications - High credibility (4)
    "TechCrunch AI": {"score": 4, "badge": "📰", "label": "Major Publication", "color": "#3b82f6"},
    "The Verge AI": {"score": 4, "badge": "📰", "label": "Major Publication", "color": "#3b82f6"},
    "Ars Technica AI": {"score": 4, "badge": "📰", "label": "Major Publication", "color": "#3b82f6"},
    "VentureBeat AI": {"score": 4, "badge": "📰", "label": "Major Publication", "color": "#3b82f6"},
    
    # Tech News & Hardware - Medium credibility (3)
    "Tom's Hardware": {"score": 3, "badge": "ℹ️", "label": "Tech News", "color": "#8b5cf6"},
    "AnandTech": {"score": 3, "badge": "ℹ️", "label": "Tech News", "color": "#8b5cf6"},
    "AI News": {"score": 3, "badge": "ℹ️", "label": "Aggregator", "color": "#8b5cf6"},
    "AlphaSignal.ai": {"score": 3, "badge": "ℹ️", "label": "Aggregator", "color": "#8b5cf6"},
    "Tech Titans": {"score": 3, "badge": "🏢", "label": "Industry Org", "color": "#8b5cf6"},
}


def get_source_credibility(source_name: str) -> Dict[str, any]:
    """Get credibility information for a source."""
    return SOURCE_CREDIBILITY.get(source_name, {
        "score": 3,  # Default to medium
        "badge": "ℹ️",
        "label": "News Source",
        "color": "#8b5cf6"
    })


# RSS Feeds with source names for credibility tracking
RSS_FEEDS = [
    {"url": "https://openai.com/blog/rss/", "name": "OpenAI Blog"},
    {"url": "https://www.anthropic.com/news/rss.xml", "name": "Anthropic News"},
    {"url": "https://blog.google/technology/ai/rss/", "name": "Google AI Blog"},
    {"url": "https://huggingface.co/blog/feed.xml", "name": "HuggingFace Blog"},
    {"url": "https://blog.langchain.dev/rss/", "name": "LangChain Blog"},
    {"url": "https://ollama.com/blog/rss", "name": "Ollama Blog"},
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/", "name": "TechCrunch AI"},
    {"url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "name": "The Verge AI"},
    {"url": "https://arstechnica.com/ai/feed/", "name": "Ars Technica AI"},
    {"url": "https://pytorch.org/blog/feed.xml", "name": "PyTorch Blog"},
    {"url": "https://blog.tensorflow.org/feeds/posts/default", "name": "TensorFlow Blog"},
    {"url": "https://www.tomshardware.com/feeds/all", "name": "Tom's Hardware"},
    {"url": "https://www.anandtech.com/rss/", "name": "AnandTech"},
    {"url": "https://www.artificialintelligence-news.com/feed/", "name": "AI News"},
    {"url": "https://alphasignal.ai/feed/", "name": "AlphaSignal.ai"},
    {"url": "https://www.microsoft.com/en-us/research/feed/", "name": "Microsoft Research"},
    {"url": "http://export.arxiv.org/rss/cs.AI", "name": "ArXiv cs.AI"},
    {"url": "http://export.arxiv.org/rss/cs.LG", "name": "ArXiv cs.LG"},
    {"url": "http://export.arxiv.org/rss/cs.CL", "name": "ArXiv cs.CL"},
    {"url": "https://www.techtitans.org/feed", "name": "Tech Titans"},
]


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

# Keywords to EXCLUDE (commercial, deals, unrelated)
AI_EXCLUDE_KEYWORDS = [
    'deal', 'price', 'sale', 'off', 'discount', 'amazon', 'coupon', 'promo',
    'buy', 'sconto', 'offerta', 'prezzo', 'miglior', 'recensione', 'review',
    'laptop', 'monitor', 'tv', 'smartphone', 'router', 'mouse', 'keyboard',
    'headphone', 'cuffie', 'speaker', 'vacuum', 'robot', 'cleaning',
    'gaming', 'console', 'ps5', 'xbox', 'nintendo', 'steam', 'game',
    'ssd', 'ddr', 'ram', 'nvme', 'hard drive', 'storage',
    'black friday', 'prime day', 'cyber monday',
]


def is_ai_related(title: str, text: str) -> bool:
    """
    Check if article content is related to AI/LLM/ML.
    Returns True if relevant keywords are found.
    """
    combined = (title + " " + text).lower()
    
    # First, check for EXCLUSION keywords (deals, hardware spam)
    for exclude in AI_EXCLUDE_KEYWORDS:
        # Check as whole words to avoid false positives
        # e.g. "deal" in "ideal" should be allowed
        if f" {exclude} " in f" {combined} ":
            print(f"    [EXCLUDED] Found exclusion keyword: {exclude}")
            return False

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


# Legacy AI_FEEDS kept for backward compatibility (deprecated - use RSS_FEEDS instead)
AI_FEEDS = [feed["url"] for feed in RSS_FEEDS]


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



def fetch_raw_news(limit_per_feed: int = 5, lookback_days: int = 7) -> List[Dict[str, str]]:
    """
    Ritorna una lista di dict:
      { "title": ..., "text": ..., "link": ..., "image_url": ... }
    per tutte le sorgenti definite in AI_FEEDS.
    Filters content to ensure it's AI/LLM/ML related.
    
    Args:
        limit_per_feed: Max articles per feed
        lookback_days: Max age of articles in days (default 7)
    """
    from datetime import datetime, timedelta
    from time import mktime
    
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
    print(f"Fetching news since {cutoff_date.strftime('%Y-%m-%d')}...")


    items: List[Dict[str, str]] = []
    filtered_count = 0

    for feed_info in RSS_FEEDS:
        feed_url = feed_info["url"]
        source_name = feed_info["name"]
        credibility_info = get_source_credibility(source_name)
        
        print(f"\n[SCAN] {source_name} Fetching...")
        
        parsed = feedparser.parse(feed_url)
        feed_items = 0
        
        for entry in parsed.entries:
            # Stop if we have enough items from this feed
            if feed_items >= limit_per_feed:
                break
                
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            summary = getattr(entry, "summary", "")
            
            # Date filtering
            published_parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            if published_parsed:
                published_dt = datetime.fromtimestamp(mktime(published_parsed))
                if published_dt < cutoff_date:
                    # Skip old articles
                    continue
            
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
                # print(f"  [FILTERED] Non-AI content: {title[:60]}...")
                continue

            # Extract high-resolution image
            image_url = get_best_image_url(entry, link)

            items.append(
                {
                    "title": title,
                    "text": text,
                    "link": link,
                    "image_url": image_url or "",
                    "source_name": source_name,
                    "credibility_score": credibility_info["score"],
                }
            )
            feed_items += 1
            print(f"  [OK] {title[:60]}...")

    print(f"\nTotal articles: {len(items)}, Filtered out: {filtered_count}")
    return items
