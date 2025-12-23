import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User

db = SessionLocal()
try:
    # Get admin user
    admin = db.query(User).filter(User.username == "admin").first()
    
    if not admin:
        print("❌ Admin user not found!")
        exit(1)
    
    # Set simple password
    new_password = "admin123"
    admin.hashed_password = User.hash_password(new_password)
    db.commit()
    
    print("✓ Admin password updated!")
    print(f"  Username: admin")
    print(f"  New Password: {new_password}")
    print("\nYou can now login with these simpler credentials.")
    
finally:
    db.close()
