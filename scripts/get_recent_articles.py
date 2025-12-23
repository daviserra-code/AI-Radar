import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Article, Base
from app.database import DATABASE_URL

def get_articles_last_month():
    # Database setup
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Calculate date 30 days ago
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        print(f"Fetching articles from {cutoff_date} to now...\n")

        # Query articles
        articles = session.query(Article).filter(Article.created_at >= cutoff_date).order_by(Article.created_at.desc()).all()

        if not articles:
            print("No articles found in the last month.")
            return

        print(f"Found {len(articles)} articles:\n")
        print(f"{'ID':<5} | {'Date':<12} | {'Source':<20} | {'Title'}")
        print("-" * 100)
        
        for article in articles:
            date_str = article.created_at.strftime('%Y-%m-%d')
            source = article.source_name or "Unknown"
            # Truncate title if too long
            title = article.title[:60] + "..." if len(article.title) > 60 else article.title
            print(f"{article.id:<5} | {date_str:<12} | {source:<20} | {title}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    get_articles_last_month()
