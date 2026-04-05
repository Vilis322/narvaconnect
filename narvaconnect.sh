#!/bin/bash
# narvaconnect.sh — run local or deploy to VPS
# Usage: ./narvaconnect.sh <command>

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_ROOT}"

DOMAIN="narvaconnect.app"
TUNNEL_NAME="narvaconnect-mlx"

case "$1" in

  # === Build frontend for production ===
  build)
    if [ ! -d "frontend/node_modules" ]; then
      (cd frontend && npm install)
    fi
    (cd frontend && npm run build)
    echo "Frontend built to frontend/dist/"
    ;;

  # === Start FastAPI backend (serves API + static frontend) ===
  backend)
    source .venv/bin/activate
    python backend/server.py
    ;;

  # === Start MLX inference server (Apple Silicon only) ===
  mlx)
    source .venv/bin/activate
    python -m mlx_lm server \
      --model mlx-community/Meta-Llama-3.1-8B-Instruct-4bit \
      --port 8080
    ;;

  # === Start Cloudflare Tunnel (narvaconnect.app -> localhost:3000) ===
  tunnel)
    cloudflared tunnel run "${TUNNEL_NAME}"
    ;;

  # === Start EVERYTHING (backend + MLX + tunnel) ===
  up)
    echo "Starting NarvaConnect stack..."
    source .venv/bin/activate

    if [ ! -d "frontend/node_modules" ]; then
      echo "Installing frontend deps..."
      (cd frontend && npm install)
    fi

    if [ ! -d "frontend/dist" ]; then
      echo "Building frontend..."
      (cd frontend && npm run build)
    fi

    python -m mlx_lm server \
      --model mlx-community/Meta-Llama-3.1-8B-Instruct-4bit \
      --port 8080 &
    MLX_PID=$!
    echo "MLX server: PID $MLX_PID (port 8080)"
    sleep 3

    (cd "${PROJECT_ROOT}" && python backend/server.py) &
    BACKEND_PID=$!
    echo "Backend: PID $BACKEND_PID (port 3000)"
    sleep 2

    cloudflared tunnel run "${TUNNEL_NAME}" &
    TUNNEL_PID=$!
    echo "Tunnel: PID $TUNNEL_PID"
    echo ""
    echo "=== NarvaConnect is live at https://${DOMAIN} ==="
    echo "Ctrl+C to stop all services"

    trap "kill $MLX_PID $BACKEND_PID $TUNNEL_PID 2>/dev/null; exit" INT TERM
    wait
    ;;

  # === Dev mode (hot reload frontend) ===
  dev-backend)
    source .venv/bin/activate
    python backend/server.py
    ;;
  dev-frontend)
    cd frontend && npm run dev
    ;;

  # === Quality ===
  test)
    source .venv/bin/activate
    ruff check backend/ data/scripts/
    cd frontend && npx tsc --noEmit
    ;;

  # === Open ===
  open)
    open "https://${DOMAIN}"
    ;;

  # === VPS deployment (for students to learn) ===
  # Set SSH_HOST env var: SSH_HOST=root@YOUR_IP ./narvaconnect.sh <cmd>
  #
  # deploy)
  #   ssh "${SSH_HOST}" "cd /var/www/narvaconnect && git pull origin main && source .venv/bin/activate && pip install -q -r backend/requirements.txt && cd frontend && npm ci && npm run build && pm2 reload narvaconnect-api"
  #   ;;
  # logs)
  #   ssh "${SSH_HOST}" "pm2 logs narvaconnect-api --lines ${2:-50}"
  #   ;;
  # status)
  #   ssh "${SSH_HOST}" "pm2 status narvaconnect-api"
  #   ;;
  # restart)
  #   ssh "${SSH_HOST}" "pm2 reload narvaconnect-api"
  #   ;;

  *)
    echo "narvaconnect.sh — ${DOMAIN}"
    echo ""
    echo "Production (all via Cloudflare Tunnel):"
    echo "  up             Start MLX + backend + tunnel (one command)"
    echo "  build          Build frontend static files"
    echo "  backend        Start FastAPI (serves API + frontend, :3000)"
    echo "  mlx            Start MLX inference server (:8080)"
    echo "  tunnel         Start Cloudflare Tunnel"
    echo "  open           Open ${DOMAIN} in browser"
    echo ""
    echo "Development (hot reload):"
    echo "  dev-backend    FastAPI (:3000)"
    echo "  dev-frontend   Vite dev server (:5173)"
    echo ""
    echo "Quality:"
    echo "  test           Run lints"
    echo ""
    echo "VPS deployment (commented — see script for students):"
    echo "  # deploy, logs, status, restart"
    ;;
esac
