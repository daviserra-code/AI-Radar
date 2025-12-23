import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User

db = SessionLocal()
try:
    users = db.query(User).all()
    print(f"\nTotal users in database: {len(users)}\n")
    
    for u in users:
        print(f"Username: {u.username}")
        print(f"Email: {u.email}")
        print(f"Is Admin: {u.is_admin}")
        print(f"Is Active: {u.is_active}")
        print(f"Has password: {len(u.hashed_password) > 0 if u.hashed_password else False}")
        print("-" * 40)
        
finally:
    db.close()
