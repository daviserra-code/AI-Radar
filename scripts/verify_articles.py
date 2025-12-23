import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime

# Connection URL for host -> docker db
DATABASE_URL = "postgresql+psycopg2://llmobs_user:llmobs_pass@localhost:5433/llmobs_db"

def check_articles():
    print(f"[{datetime.now()}] Connecting to database...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Check total count
            result = conn.execute(text("SELECT count(*) FROM articles"))
            count = result.scalar()
            print(f"Total articles in DB: {count}")

            if count > 0:
                # Check latest articles
                print("\nLatest 5 articles:")
                result = conn.execute(text("SELECT title, source_name, created_at, ai_generated FROM articles ORDER BY created_at DESC LIMIT 5"))
                for row in result:
                    title, source, created, ai = row
                    print(f"- [{source}] {title[:60]}... (Created: {created}, AI: {ai})")
            else:
                print("No articles found in the database!")
                
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        print("Make sure the database container is running and port 5433 is exposed.")

if __name__ == "__main__":
    check_articles()
