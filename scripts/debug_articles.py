import sys
import os
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Article
from app.database import DATABASE_URL

def check_all_articles():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        total_count = session.query(Article).count()
        print(f"Total articles in database: {total_count}")

        if total_count > 0:
            latest_article = session.query(Article).order_by(Article.created_at.desc()).first()
            oldest_article = session.query(Article).order_by(Article.created_at.asc()).first()
            
            print(f"Most recent article: {latest_article.title} (Date: {latest_article.created_at})")
            print(f"Oldest article: {oldest_article.title} (Date: {oldest_article.created_at})")
        else:
            print("The articles table is completely empty.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_all_articles()
