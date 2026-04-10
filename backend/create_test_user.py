"""
Script to create test user credentials for development.
Run this to add test@test.com / test credentials.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from security.auth import hash_password
import json

def create_test_users():
    """Create test users file with hashed passwords."""
    
    # Test users with hashed passwords
    test_users = {
        "test@test.com": {
            "email": "test@test.com",
            "password_hash": hash_password("testpass123"),
            "name": "Test User",
            "role": "admin",
            "user_id": "test-user-001",
            "verified": True
        },
        "admin@tradesense.com": {
            "email": "admin@tradesense.com",
            "password_hash": hash_password("admin123"),
            "name": "Admin User",
            "role": "admin",
            "user_id": "admin-user-001",
            "verified": True
        },
        "tech@tradesense.com": {
            "email": "tech@tradesense.com",
            "password_hash": hash_password("tech123"),
            "name": "Technician User",
            "role": "technician",
            "user_id": "tech-user-001",
            "verified": True
        }
    }
    
    # Save to file
    test_users_file = backend_dir / "test_users.json"
    with open(test_users_file, 'w') as f:
        json.dump(test_users, f, indent=2)
    
    print("✅ Test users created successfully!")
    print("\nAvailable test credentials:")
    print("\n1. Admin User:")
    print("   Email: test@test.com")
    print("   Password: testpass123")
    print("\n2. Admin User:")
    print("   Email: admin@tradesense.com")
    print("   Password: admin123")
    print("\n3. Technician User:")
    print("   Email: tech@tradesense.com")
    print("   Password: tech123")
    print(f"\nTest users saved to: {test_users_file}")

if __name__ == "__main__":
    create_test_users()
