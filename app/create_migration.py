#!/usr/bin/env python3
"""
Create initial database migration
"""

import os
from flask_migrate import init, migrate, upgrade
from app import app


def create_initial_migration():
    """Create initial migration for the database"""
    with app.app_context():
        try:
            # Check if migrations directory exists
            if not os.path.exists('migrations'):
                print("Initializing migrations...")
                init()

            # Create initial migration
            print("Creating initial migration...")
            migrate(message="Initial migration")

            # Apply migration
            print("Applying migration...")
            upgrade()

            print("✅ Migration created and applied successfully!")

        except Exception as e:
            print(f"❌ Error creating migration: {e}")


if __name__ == "__main__":
    create_initial_migration()