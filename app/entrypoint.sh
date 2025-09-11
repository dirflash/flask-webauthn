#!/bin/sh

echo "Starting Flask WebAuthn Demo Application..."

# Check if we're using PostgreSQL (Docker) or SQLite (local)
if [ "$DATABASE_URL" ] && echo "$DATABASE_URL" | grep -q "postgresql"; then
    echo "Using PostgreSQL database, waiting for connection..."
    wait-for-it -t 30 db:5432 -- echo "PostgreSQL is ready"
    
    echo "Running database migrations..."
    # Initialize migrations if they don't exist
    if [ ! -d "migrations/versions" ] || [ -z "$(ls -A migrations/versions 2>/dev/null)" ]; then
        echo "No migrations found, creating initial migration..."
        flask db init || echo "Migrations already initialized"
        flask db migrate -m "Initial migration" || echo "Migration creation failed"
    fi
    
    # Apply migrations
    flask db upgrade || echo "Migration upgrade failed"
    
else
    echo "Using SQLite database (local development)"
    # For SQLite, we can use manual table creation
    echo "Creating database tables..."
    python -c "
from app import app, db
with app.app_context():
    try:
        db.create_all()
        print('✅ Database tables created successfully')
    except Exception as e:
        print(f'❌ Error creating tables: {e}')
"
fi

echo "Starting application server..."
if [ "$FLASK_ENV" = "development" ]; then
    echo "Running in development mode..."
    python app.py
else
    echo "Running in production mode with Waitress..."
    waitress-serve --host 0.0.0.0 --port 5000 app:app
fi