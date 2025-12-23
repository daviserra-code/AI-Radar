"""
Migration script to add missing columns to comments table
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from sqlalchemy import text

def migrate():
    """Add missing columns to comments table"""
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'comments'
        """))
        existing_columns = {row[0] for row in result}
        
        print(f"Existing columns in comments table: {existing_columns}")
        
        # Add is_deleted if missing
        if 'is_deleted' not in existing_columns:
            print("Adding is_deleted column...")
            conn.execute(text("""
                ALTER TABLE comments 
                ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
            print("✓ Added is_deleted column")
        
        # Add is_edited if missing
        if 'is_edited' not in existing_columns:
            print("Adding is_edited column...")
            conn.execute(text("""
                ALTER TABLE comments 
                ADD COLUMN is_edited BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
            print("✓ Added is_edited column")
        
        print("Migration complete!")

if __name__ == "__main__":
    migrate()
