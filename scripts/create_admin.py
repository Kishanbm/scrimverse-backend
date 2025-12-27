#!/usr/bin/env python
"""
Script to create a Django superuser for Scrimverse admin panel
Run this from the backend directory with: python scripts/create_admin.py
"""
import os
import sys

import django

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scrimverse.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()


def create_superuser():
    """Create a superuser for Django admin"""

    # Default credentials
    email = "admin@scrimverse.com"
    username = "admin"
    password = "admin123"

    # Check if superuser already exists
    if User.objects.filter(email=email).exists():
        print(f"❌ Superuser with email '{email}' already exists!")
        existing_user = User.objects.get(email=email)
        print(f"   Username: {existing_user.username}")
        print(f"   Email: {existing_user.email}")
        print(f"   Is superuser: {existing_user.is_superuser}")
        print(f"   Is staff: {existing_user.is_staff}")

        # Ask if they want to reset password
        response = input("\nDo you want to reset the password? (yes/no): ").lower()
        if response == "yes":
            existing_user.set_password(password)
            existing_user.save()
            print("✅ Password reset successfully!")
            print("\n📝 Admin Credentials:")
            print(f"   Email: {email}")
            print(f"   Username: {username}")
            print(f"   Password: {password}")
            print("\n🌐 Access admin at: http://127.0.0.1:8000/admin/")
        return

    # Create superuser
    try:
        user = User.objects.create_superuser(email=email, username=username, password=password)

        print("=" * 60)
        print("✅ Django Superuser Created Successfully!")
        print("=" * 60)
        print("\n📝 Admin Credentials:")
        print(f"   Email: {email}")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   User ID: {user.id}")
        print("\n🌐 Access admin panel at: http://127.0.0.1:8000/admin/")
        print("\n⚠️  IMPORTANT: Change the password after first login!")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error creating superuser: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("\n🔧 Creating Django Superuser for Scrimverse Admin Panel...\n")
    create_superuser()
