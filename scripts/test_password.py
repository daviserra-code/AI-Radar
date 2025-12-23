import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User
import bcrypt

db = SessionLocal()
try:
    # Get admin user
    admin = db.query(User).filter(User.username == "admin").first()
    
    if not admin:
        print("❌ Admin user not found!")
        exit(1)
    
    print(f"✓ Admin user found: {admin.username}")
    print(f"  Email: {admin.email}")
    print(f"  Is Admin: {admin.is_admin}")
    print(f"  Is Active: {admin.is_active}")
    
    # Test password
    test_password = "Admin_User_2025!"
    print(f"\nTesting password: {test_password}")
    
    # Method 1: Using model method
    result1 = admin.verify_password(test_password)
    print(f"  Model verify_password(): {result1}")
    
    # Method 2: Direct bcrypt check
    try:
        result2 = bcrypt.checkpw(
            test_password.encode('utf-8'), 
            admin.hashed_password.encode('utf-8')
        )
        print(f"  Direct bcrypt.checkpw(): {result2}")
    except Exception as e:
        print(f"  Direct bcrypt error: {e}")
    
    # Show hash info
    print(f"\nStored hash (first 50 chars): {admin.hashed_password[:50]}...")
    print(f"Hash length: {len(admin.hashed_password)}")
    
    # Test creating a new hash
    print(f"\nCreating test hash for same password...")
    test_hash = User.hash_password(test_password)
    print(f"  New hash (first 50 chars): {test_hash[:50]}...")
    
    # Verify new hash
    test_verify = bcrypt.checkpw(test_password.encode('utf-8'), test_hash.encode('utf-8'))
    print(f"  New hash verifies: {test_verify}")
    
finally:
    db.close()
