#!/usr/bin/env python3
"""
Reset database utility - useful for development
"""

import os
from app import app, db
from flask_migrate import upgrade, init, migrate


def reset_database():
    """Reset the database completely"""
    with app.app_context():
        try:
            database_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")

            if "postgresql" in database_url.lower():
                print("Resetting PostgreSQL database...")

                # Drop all tables
                db.drop_all()
                print("✅ All tables dropped")

                # Remove migration files
                import shutil
                if os.path.exists("migrations"):
                    shutil.rmtree("migrations")
                    print("✅ Migration files removed")

                # Reinitialize migrations
                init()
                print("✅ Migrations reinitialized")

                # Create initial migration
                migrate(message="Initial migration")
                print("✅ Initial migration created")

                # Apply migration
                upgrade()
                print("✅ Migration applied")

            else:
                print("Resetting SQLite database...")
                db.drop_all()
                db.create_all()
                print("✅ SQLite database reset complete")

        except Exception as e:
            print(f"❌ Error resetting database: {e}")


if __name__ == "__main__":
    reset_database()
