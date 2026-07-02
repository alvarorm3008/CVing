#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

if [ ! -d .venv ]; then
  echo "Creating virtualenv..."
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  echo "Run: cd backend && .venv/bin/playwright install chromium"
fi

if [ ! -f .env ]; then
  echo "Warning: backend/.env missing. Copy from .env.example and set GEMINI_API_KEY"
fi

echo "Backend → http://localhost:8000"
exec .venv/bin/uvicorn main:app --reload --port 8000
