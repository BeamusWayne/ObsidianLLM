#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "── Building frontend…"
cd frontend
npm install --silent
npm run build
cd ..

echo "── Starting server at http://localhost:8000"
.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
