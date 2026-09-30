#!/usr/bin/env bash
# Setup script for Travel Bot

set -e

echo "🚀 Setting up Travel Bot..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your tokens!"
    exit 1
fi

# Check if tokens are set
source .env
if [ "$TELEGRAM_BOT_TOKEN" = "your_telegram_bot_token_here" ] || [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN not set in .env"
    exit 1
fi

if [ "$OPENROUTER_API_KEY" = "your_openrouter_api_key_here" ] || [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ OPENROUTER_API_KEY not set in .env"
    exit 1
fi

# Start PostgreSQL with docker-compose
echo "🐘 Starting PostgreSQL..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
sleep 5

# Run database initialization
echo "🗄️ Initializing database..."
python -c "
import asyncio
from database import init_db
asyncio.run(init_db())
print('✅ Database initialized')
"

echo "✅ Setup complete!"
echo ""
echo "To run the bot:"
echo "  python bot.py"
echo ""
echo "Or with Docker:"
echo "  docker-compose up --build"