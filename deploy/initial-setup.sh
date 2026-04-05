#!/bin/bash
# initial-setup.sh — run ONCE on fresh Ubuntu 22.04 VPS
# Usage on server: curl -sSL https://raw.githubusercontent.com/Vilis322/narvaconnect/main/deploy/initial-setup.sh | bash
# Or: scp this file to server, then: bash initial-setup.sh

set -e

APP_DIR="/var/www/narvaconnect"
DOMAIN="narvaconnect.app"
REPO="https://github.com/Vilis322/narvaconnect.git"

echo "=== NarvaConnect Initial Setup ==="
echo "Target: Ubuntu 22.04, domain: ${DOMAIN}"
echo ""

# === 1. System packages ===
echo "[1/7] Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt update -qq
apt install -y -qq software-properties-common curl git nginx
add-apt-repository -y ppa:deadsnakes/ppa
apt update -qq
apt install -y -qq python3.13 python3.13-venv python3.13-dev tesseract-ocr build-essential

# Node.js 20
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y -qq nodejs
fi

# PM2
if ! command -v pm2 &> /dev/null; then
    npm install -g pm2
fi

# Certbot
apt install -y -qq certbot python3-certbot-nginx

echo "[1/7] Done"

# === 2. Clone repo ===
echo "[2/7] Cloning repo..."
if [ -d "${APP_DIR}/.git" ]; then
    cd "${APP_DIR}" && git fetch origin && git reset --hard origin/main
else
    mkdir -p "${APP_DIR}"
    git clone "${REPO}" "${APP_DIR}"
    cd "${APP_DIR}"
fi
echo "[2/7] Done"

# === 3. Python backend ===
echo "[3/7] Setting up Python backend..."
cd "${APP_DIR}"
python3.13 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt
echo "[3/7] Done"

# === 4. Build RAG index ===
echo "[4/7] Building RAG index..."
# NOTE: data/raw/ is gitignored, so Moodle docs and OCR screenshots are NOT on the server.
# We build the index with what's available — teacher facts and pre-parsed JSON if present.
# For full index with Moodle content, user must copy data/processed/*.json and data/raw/ manually.
if [ -f "data/processed/ois2_parsed.json" ]; then
    python data/scripts/build_rag.py
else
    echo "  WARNING: data/processed/ois2_parsed.json not found — RAG will have only teacher facts"
    echo "  Upload parsed JSON files manually: scp data/processed/*.json root@SERVER:${APP_DIR}/data/processed/"
fi
echo "[4/7] Done"

# === 5. Build frontend ===
echo "[5/7] Building frontend..."
cd "${APP_DIR}/frontend"
npm ci --silent
npm run build
cd "${APP_DIR}"
echo "[5/7] Done"

# === 6. PM2 process ===
echo "[6/7] Starting PM2 process..."
pm2 delete narvaconnect-api 2>/dev/null || true
pm2 start "${APP_DIR}/.venv/bin/python" \
    --name narvaconnect-api \
    --cwd "${APP_DIR}" \
    -- backend/server.py
pm2 save
pm2 startup systemd -u root --hp /root | tail -1 | bash || true
echo "[6/7] Done"

# === 7. Nginx + SSL ===
echo "[7/7] Configuring nginx..."
cat > /etc/nginx/sites-available/narvaconnect.app <<EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    location / {
        root ${APP_DIR}/frontend/dist;
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_read_timeout 120s;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 3600s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/narvaconnect.app /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
echo "[7/7] Done"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "1. Point narvaconnect.app DNS A-record to this server IP"
echo "2. Run certbot for SSL:"
echo "   certbot --nginx -d narvaconnect.app -d www.narvaconnect.app --agree-tos -m YOUR_EMAIL --non-interactive"
echo "3. Test: curl http://narvaconnect.app/api/health"
echo ""
echo "To update inference server URL (when MLX is running via Cloudflare Tunnel):"
echo "   pm2 set narvaconnect-api:MLX_SERVER_URL https://ai.narvaconnect.app"
echo "   pm2 restart narvaconnect-api --update-env"
