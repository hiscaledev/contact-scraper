#!/bin/bash

# Contact Scraper Setup Script
# Docker-first deployment setup

set -e

echo "=========================================="
echo "Contact Scraper API - Setup Script"
echo "=========================================="
echo ""

# Check if Docker is installed
echo "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✅ Docker is installed"
echo ""

# Check if Docker Compose is available
echo "Checking Docker Compose..."
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available!"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
echo "✅ Docker Compose is available"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo ""
    echo "Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env file"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env and configure:"
        echo "   - API_KEYS (for authentication)"
        echo "   - OPENAI_API_KEY (required)"
        echo "   - SUPABASE_URL and SUPABASE_KEY (required)"
        echo ""
        echo "For Docker deployment, use these Redis settings:"
        echo "   REDIS_HOST=redis"
        echo "   REDIS_PORT=6379"
        echo ""
        exit 1
    else
        echo "❌ .env.example not found!"
        exit 1
    fi
fi

echo "✅ .env file found"
echo ""

# Validate critical environment variables
echo "Validating environment variables..."
source .env

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-openai-api-key-here" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not configured"
fi

if [ -z "$SUPABASE_URL" ] || [ "$SUPABASE_URL" = "https://your-project-id.supabase.co" ]; then
    echo "⚠️  Warning: SUPABASE_URL not configured"
fi

if [ -z "$SUPABASE_KEY" ] || [ "$SUPABASE_KEY" = "your_supabase_service_role_key_here" ]; then
    echo "⚠️  Warning: SUPABASE_KEY not configured"
fi

# Check Redis host configuration
if [ "$REDIS_HOST" = "localhost" ]; then
    echo "⚠️  Warning: REDIS_HOST is set to 'localhost'"
    echo "   For Docker deployment, it should be 'redis'"
    echo "   Update .env: REDIS_HOST=redis"
fi

echo ""

# Build Docker images
echo "Building Docker images..."
docker compose build
echo "✅ Docker images built successfully"
echo ""

echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Set up Supabase (if not done):"
echo "   - Run SQL script: schema/supabase_schema.sql"
echo "   - Create storage bucket: 'contact-scraper' (Private)"
echo ""
echo "2. Start the application:"
echo "   docker compose up -d"
echo ""
echo "3. View logs:"
echo "   docker compose logs -f"
echo ""
echo "4. Stop the application:"
echo "   docker compose down"
echo ""
echo "5. Access the API:"
echo "   - API: http://localhost:8000"
echo "   - Docs: http://localhost:8000/docs"
echo ""
echo "For local development without Docker:"
echo "   - Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
echo "   - Run: uv sync"
echo "   - Set REDIS_HOST=localhost in .env"
echo "   - Start Redis: docker run -d -p 6379:6379 redis:8.4.0-alpine"
echo "   - Run: uv run uvicorn main:app --reload"
echo ""
echo "=========================================="
