# NarvaConnect

Student schedule & university hub for Narva Kolledž (Tartu Ülikool) with AI assistant.

> This is a community project — not affiliated with Tartu Ülikool.

## Features

- **Weekly schedule** — mobile-first swipe navigation
- **Deadline tracker** — exams, assignments, projects with urgency highlighting
- **AI assistant** — RAG-powered chat grounded in course materials (Estonian, Russian, English)
- **Live server logs** — real-time view of backend activity (WebSocket stream)

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | FastAPI, ChromaDB, sentence-transformers, WebSockets |
| AI (Apple Silicon) | MLX, Llama 3.1 8B |
| AI (x86 fallback) | Ollama, Llama 3.1 8B |
| Deploy | Ubuntu 22.04, nginx, PM2, Cloudflare Tunnel |

## Quick Start

### Prerequisites
- Python 3.13+, Node.js 20+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (for parsing ÕIS screenshots)

### Setup

```bash
git clone https://github.com/Vilis322/narvaconnect.git
cd narvaconnect

# Python backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Build RAG knowledge base (indexes teacher facts, schedule, course materials)
python data/scripts/build_rag.py
```

### Run

You need 3 processes running in parallel:

```bash
# Terminal 1 — Inference server
# On Apple Silicon Mac:
./narvaconnect.sh mlx-server

# On x86 Linux/Windows (Ollama fallback):
ollama pull llama3.1:8b
ollama serve  # runs on :11434
# Then set env var before starting backend:
export MLX_SERVER_URL=http://localhost:11434

# Terminal 2 — FastAPI backend
./narvaconnect.sh dev-backend  # :3000

# Terminal 3 — Vite dev server
./narvaconnect.sh dev-frontend  # :5173
```

Open http://localhost:5173

## Architecture

```
narvaconnect.app (VPS)
   ├── Frontend (React static build, served by nginx)
   ├── Backend (FastAPI + ChromaDB, PM2 managed)
   │      │
   │      └── /api/chat → Cloudflare Tunnel → Local Mac (MLX)
   │
   └── Local Mac: MLX server :8080
          └── cloudflared tunnel → https://ai.narvaconnect.app
```

## Data Pipeline

All schedule/course data comes from university sources, parsed locally:

1. **ÕIS screenshots** → `data/scripts/ocr_parse_ois2.py` (Tesseract OCR)
2. **Moodle files** (PDF/DOCX/PPTX/XLSX) → `data/scripts/parse_moodle.py`
3. **Combined** → `data/scripts/build_rag.py` → ChromaDB

Student data (`data/raw/`, `data/processed/`, `data/chromadb/`) is gitignored — each contributor builds their own index from their own materials.

## Deploy

See `narvaconnect.sh` for deploy commands. Target: Ubuntu 22.04 VPS.

First-time setup is commented in the script. Subsequent deploys:

```bash
SSH_HOST=root@YOUR_IP ./narvaconnect.sh deploy
```

## Cloudflare Tunnel Setup (for AI on local Mac)

```bash
# 1. Install cloudflared
brew install cloudflared

# 2. Authenticate
cloudflared tunnel login

# 3. Create tunnel
cloudflared tunnel create narvaconnect-mlx

# 4. Route DNS
cloudflared tunnel route dns narvaconnect-mlx ai.narvaconnect.app

# 5. Configure ~/.cloudflared/config.yml:
#    tunnel: <tunnel-id>
#    credentials-file: /Users/you/.cloudflared/<tunnel-id>.json
#    ingress:
#      - hostname: ai.narvaconnect.app
#        service: http://localhost:8080
#      - service: http_status:404

# 6. Run tunnel
cloudflared tunnel run narvaconnect-mlx

# On VPS, set:
#   MLX_SERVER_URL=https://ai.narvaconnect.app
```

## Live

https://narvaconnect.app

## Contributing

Contributions welcome! Workflow:
1. Fork & clone
2. Create feature branch from `main`: `git checkout -b feat/your-feature`
3. Commit and push
4. Open Pull Request to `main`
5. CI runs lint + smoke tests automatically

## Contributors

- Kyrylo Pryiomyshev — [GitHub](https://github.com/Vilis322)

## License

All rights reserved.
