#!/bin/bash
# Backend Discard Service - Start Script

echo "🤖 Starting Backend Discard Service..."

# Check if we're in the right directory
if [ ! -f "src/app.py" ]; then
    echo "❌ Error: Must run from backend_discard directory"
    echo "   Expected file: src/app.py"
    exit 1
fi

# Check for environment variables
if [ -z "$UPSTASH_REDIS_REST_URL" ]; then
    echo "❌ Error: Missing UPSTASH_REDIS_REST_URL environment variable"
    exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ Error: Missing OPENROUTER_API_KEY environment variable"
    exit 1
fi

echo "✅ Environment checks passed"

# Start the service
python src/app.py
