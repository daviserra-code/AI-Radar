#!/bin/bash

# AI-Radar Deployment Script for Hetzner Server
# Usage: ./deploy.sh

set -e

echo "🚀 Starting AI-Radar deployment..."

# Stash any local changes (database files, logs, etc.)
echo "💾 Stashing local changes..."
git stash --include-untracked || true

# Pull latest changes
echo "📥 Pulling latest code from GitHub..."
git pull origin main

# Restore stashed database if it exists
echo "🔄 Restoring local database..."
git checkout stash -- chroma_store/chroma.sqlite3 2>/dev/null || true
git stash drop 2>/dev/null || true

# Stop current containers
echo "🛑 Stopping current containers..."
docker-compose down

# Rebuild images
echo "🔨 Building Docker images..."
docker-compose build --no-cache

# Start containers
echo "▶️  Starting containers..."
docker-compose up -d

# Wait for database to be ready
echo "⏳ Waiting for database..."
sleep 10

# Check if containers are running
echo "✅ Checking container status..."
docker-compose ps

# Show logs
echo "📋 Recent logs:"
docker-compose logs --tail=50

echo "✨ Deployment complete!"
echo "🌐 Application should be available on port 8000"
