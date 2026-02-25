#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting deployment for Online Paper Reader..."

# 1. Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "❌ Error: docker is not installed."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed."
    exit 1
fi

# 2. Setup environment variables
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update .env with your own secrets in production."
fi

# 3. Create necessary directories
echo "📁 Creating data directories..."
mkdir -p uploads backups

# 4. Build and start containers
echo "🏗️  Building and starting containers with Docker Compose..."
docker-compose up -d --build

# 5. Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
until docker-compose exec -T postgres pg_isready -U paperuser -d paper_reader; do
  sleep 2
done

# 6. Run database migrations
echo "🔄 Running database migrations..."
# Check if versions folder is empty
if [ -z "$(ls -A backend/alembic/versions)" ]; then
    echo "🐣 No migrations found, creating initial migration..."
    docker-compose exec -T backend alembic revision --autogenerate -m "Initial migration"
fi
docker-compose exec -T backend alembic upgrade head

# 7. Final status check
echo "✅ Deployment completed successfully!"
echo "📍 Services status:"
docker-compose ps

echo "🌐 Access your application at: http://localhost"
