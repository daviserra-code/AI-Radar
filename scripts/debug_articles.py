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
            # Print details of the last 3 articles
            recent_articles = session.query(Article).order_by(Article.created_at.desc()).limit(3).all()
            print(f"\n--- Analysis of the last {len(recent_articles)} articles ---\n")
            for i, art in enumerate(recent_articles):
                print(f"[{i+1}] TITLE: {art.title}")
                print(f"    DATE:  {art.created_at}")
                print(f"    SUMMARY: {art.summary}")
                print(f"    SNIPPET: {art.content[:200]}...") 
                print("-" * 50)
        else:
            print("The articles table is completely empty.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_all_articles()
