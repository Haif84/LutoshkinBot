#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "==> Pulling latest code from GitHub..."
git pull origin master

echo "==> Rebuilding and restarting container..."
docker compose up -d --build

echo "==> Done! Bot is running."
docker compose logs --tail=10
