#!/bin/bash
# narvaconnect.sh — deployment & management commands
# Usage: ./narvaconnect.sh <command>

set -e

SSH_HOST="${SSH_HOST:-root@64.111.93.12}"
APP_DIR="/var/www/narvaconnect"
PM2_NAME="narvaconnect-api"
DOMAIN="narvaconnect.app"

case "$1" in

  # === LOCAL DEV ===
  dev-backend)
    cd backend && python server.py
    ;;
  dev-frontend)
    cd frontend && npm run dev
    ;;
  test)
    ruff check backend/ data/scripts/
    cd frontend && npx tsc --noEmit
    ;;
  open)
    open "https://${DOMAIN}"
    ;;

  # === MLX LOCAL (Apple Silicon only) ===
  mlx-server)
    source .venv/bin/activate
    python -m mlx_lm server \
      --model mlx-community/Meta-Llama-3.1-8B-Instruct-4bit \
      --port 8080
    ;;

  # === DEPLOY ===
  deploy)
    echo "Deploying to ${SSH_HOST}..."
    ssh "${SSH_HOST}" "cd ${APP_DIR} && git pull origin main && cd backend && pip install -q -r requirements.txt && cd ../frontend && npm ci && npm run build && pm2 reload ${PM2_NAME}"
    echo "Deploy complete."
    ;;

  # === SERVER MANAGEMENT ===
  logs)
    ssh "${SSH_HOST}" "pm2 logs ${PM2_NAME} --lines ${2:-50}"
    ;;
  status)
    ssh "${SSH_HOST}" "pm2 status ${PM2_NAME}"
    ;;
  restart)
    ssh "${SSH_HOST}" "pm2 reload ${PM2_NAME}"
    ;;
  stop)
    ssh "${SSH_HOST}" "pm2 stop ${PM2_NAME}"
    ;;

  # === FIRST DEPLOY (run once on fresh server) ===
  # setup)
  #   echo "Initial setup on ${SSH_HOST}..."
  #   ssh "${SSH_HOST}" "
  #     apt update && apt install -y python3.13 python3.13-venv nodejs npm nginx &&
  #     npm install -g pm2 &&
  #     mkdir -p ${APP_DIR} &&
  #     cd ${APP_DIR} &&
  #     git clone https://github.com/Vilis322/narvaconnect.git . &&
  #     python3 -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt &&
  #     cd frontend && npm ci && npm run build && cd .. &&
  #     pm2 start backend/server.py --name ${PM2_NAME} --interpreter .venv/bin/python &&
  #     pm2 save
  #   "
  #   echo "Setup complete. Configure nginx: nginx/${DOMAIN}.conf.example"
  #   ;;

  *)
    echo "narvaconnect.sh — ${DOMAIN}"
    echo ""
    echo "Local dev:"
    echo "  dev-backend    Start FastAPI (:3000)"
    echo "  dev-frontend   Start Vite (:5173)"
    echo "  mlx-server     Start MLX inference server (Apple Silicon only, :8080)"
    echo "  test           Run lints"
    echo "  open           Open narvaconnect.app in browser"
    echo ""
    echo "Deploy:  SSH_HOST=root@64.111.93.12 ./narvaconnect.sh <command>"
    echo "  deploy         Pull, build, reload PM2"
    echo ""
    echo "Server:"
    echo "  logs [N]       PM2 logs (default 50)"
    echo "  status         PM2 status"
    echo "  restart        PM2 reload"
    echo "  stop           PM2 stop"
    ;;
esac
