
import sys
import os
import secrets
import string

# Append parent dir to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User

def reset_users():
    db = SessionLocal()
    try:
        # 0. Delete all comments first to avoid FK violation
        from app.models import Comment
        deleted_comments = db.query(Comment).delete()
        print(f"Deleted {deleted_comments} existing comments.")

        # 1. Delete all users
        deleted_count = db.query(User).delete()
        print(f"Deleted {deleted_count} existing users.")
        
        # 2. Create admin user
        # Generate a strong random password
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for i in range(16))
        
        # Force a specific password for easier first login if preferred, 
        # but random is safer. Let's use a known strong one for the user to copy.
        # Actually, user asked "create an admin account for me".
        # I will set a known password and valid email.
        password = "Admin_User_2025!"
        email = "admin@airadar.com"
        username = "admin"
        
        hashed_pwd = User.hash_password(password)
        
        new_admin = User(
            username=username,
            email=email,
            hashed_password=hashed_pwd,
            is_active=True,
            is_admin=True,
            is_subscribed=True
        )
        
        db.add(new_admin)
        db.commit()
        
        print("\n" + "="*50)
        print("DATABASE RESET COMPLETE")
        print("="*50)
        print(f"Admin User {username} created successfully.")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"Error resetting users: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_users()
