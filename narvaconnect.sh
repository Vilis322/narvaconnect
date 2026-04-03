#!/bin/bash
# narvaconnect.sh — deployment & management commands
# Usage: ./narvaconnect.sh <command>
#
# Setup: SSH_HOST=root@YOUR_IP ./narvaconnect.sh deploy

set -e

SSH_HOST="${SSH_HOST:-root@0.0.0.0}"
APP_DIR="/var/www/narvaconnect"
PM2_NAME="narvaconnect-api"
DOMAIN="narvaconnect.app"

case "$1" in

  # === LOCAL DEV ===
  dev)
    cd backend && npm run start:dev
    ;;
  front)
    cd frontend && npm run dev
    ;;
  test)
    cd backend && npm test
    ;;
  open)
    open "https://${DOMAIN}"
    ;;

  # === SERVER DEPLOY ===
  deploy)
    echo "Deploying to ${SSH_HOST}..."
    ssh ${SSH_HOST} "cd ${APP_DIR} && git pull origin stage && cd backend && npm ci && npm run build && pm2 reload ${PM2_NAME}"
    echo "Deploy complete."
    ;;
  # setup)
  #   echo "First deploy to ${SSH_HOST}..."
  #   ssh ${SSH_HOST} "
  #     mkdir -p ${APP_DIR} &&
  #     cd ${APP_DIR} &&
  #     git clone https://github.com/Vilis322/narvaconnect.git . &&
  #     git checkout stage &&
  #     cd backend && npm ci && npm run build &&
  #     pm2 start dist/main.js --name ${PM2_NAME} -i 1 &&
  #     pm2 save
  #   "
  #   echo "Setup complete. Configure nginx: nginx/${DOMAIN}.conf.example"
  #   ;;

  # === SERVER MANAGEMENT ===
  logs)
    ssh ${SSH_HOST} "pm2 logs ${PM2_NAME} --lines ${2:-50}"
    ;;
  status)
    ssh ${SSH_HOST} "pm2 status ${PM2_NAME}"
    ;;
  restart)
    ssh ${SSH_HOST} "pm2 reload ${PM2_NAME}"
    ;;
  stop)
    ssh ${SSH_HOST} "pm2 stop ${PM2_NAME}"
    ;;

  # === DATABASE (uncomment when resources available) ===
  # infra)
  #   docker compose up -d postgres
  #   ;;
  # infra-down)
  #   docker compose down
  #   ;;
  # migrate)
  #   cd backend && npx prisma migrate dev
  #   ;;

  *)
    echo "narvaconnect.sh — ${DOMAIN}"
    echo ""
    echo "Local:"
    echo "  dev        Start backend (NestJS :3001)"
    echo "  front      Start frontend (React :5173)"
    echo "  test       Run backend tests"
    echo "  open       Open ${DOMAIN} in browser"
    echo ""
    echo "Deploy:  SSH_HOST=root@IP ./narvaconnect.sh <command>"
    echo "  setup      Initial server setup (clone, build, PM2)"
    echo "  deploy     Pull, build, reload PM2"
    echo ""
    echo "Server:"
    echo "  logs [N]   PM2 logs (default 50 lines)"
    echo "  status     PM2 status"
    echo "  restart    PM2 reload (zero-downtime)"
    echo "  stop       PM2 stop"
    ;;
esac
