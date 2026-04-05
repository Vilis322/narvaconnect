"""
NarvaConnect backend — FastAPI server with RAG + MLX inference.

Endpoints:
  GET  /api/schedule         — all schedule events grouped by subject
  GET  /api/deadlines        — upcoming deadlines (sorted by date)
  GET  /api/subjects         — all subjects with teacher info
  POST /api/chat             — RAG-powered chat (SSE streaming)
  WS   /ws/logs              — real-time log stream for terminal mirror

Usage:
    python backend/server.py
"""

import json
import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer

# Inference server URL: local MLX (dev) or Cloudflare Tunnel URL (prod)
MLX_SERVER_URL = os.getenv("MLX_SERVER_URL", "http://localhost:8080")

# ---------------------------------------------------------------
# Setup
# ---------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHROMA_DIR = PROJECT_ROOT / "data" / "chromadb"
OIS2_FILE = PROJECT_ROOT / "data" / "processed" / "ois2_parsed.json"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger("narvaconnect")

# WebSocket log subscribers
log_subscribers: set[WebSocket] = set()


async def broadcast_log(message: str):
    """Broadcast log message to all WebSocket clients."""
    dead = set()
    for ws in log_subscribers:
        try:
            await ws.send_text(json.dumps({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": message,
            }))
        except Exception:
            dead.add(ws)
    log_subscribers.difference_update(dead)


def log_event(message: str):
    """Log to terminal AND broadcast to WebSocket subscribers."""
    log.info(message)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast_log(message))
    except RuntimeError:
        pass


# ---------------------------------------------------------------
# App
# ---------------------------------------------------------------

app = FastAPI(title="NarvaConnect API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Globals (lazy loaded)
_chroma = None
_embed_model = None
_ois2_data = None


def get_chroma():
    global _chroma
    if _chroma is None:
        log_event("Loading ChromaDB...")
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _chroma = client.get_collection("narvaconnect")
        log_event(f"ChromaDB ready — {_chroma.count()} documents")
    return _chroma


def get_embedder():
    global _embed_model
    if _embed_model is None:
        log_event("Loading embedding model (all-MiniLM-L6-v2)...")
        _embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        log_event("Embedding model ready")
    return _embed_model


def get_ois2():
    global _ois2_data
    if _ois2_data is None:
        with open(OIS2_FILE) as f:
            _ois2_data = json.load(f)
    return _ois2_data


# ---------------------------------------------------------------
# Teacher facts (authoritative)
# ---------------------------------------------------------------

TEACHERS = {
    "SVNC.00.228": {"name": "Introduction to Data Science", "teacher": "Erika Lorents, PhD"},
    "P2NC.01.095": {"name": "Analysis and Design of Information Systems", "teacher": "Daria Chukhlebova"},
    "SVNC.00.308": {"name": "Software Engineering", "teacher": "Nicolai Morozov"},
    "SVNC.00.058": {"name": "Software Testing", "teacher": "André Sääsk"},
    "P2NC.01.050": {"name": "Starting a Business", "teacher": "Tiit Urva"},
    "P2NC.01.094": {"name": "Web Application Development", "teacher": "André Sääsk"},
    "SVNC.00.184": {"name": "Practical Project-based Training in IT", "teacher": "Sudath Rohan Munasinghe"},
    "Tutvumispraktika": {"name": "Introductory Practice", "teacher": "Pavel Kodõtšikov"},
}


# ---------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------

@app.get("/api/subjects")
async def list_subjects():
    log_event("GET /api/subjects")
    return [
        {"code": code, "name": info["name"], "teacher": info["teacher"]}
        for code, info in TEACHERS.items()
    ]


@app.get("/api/schedule")
async def get_schedule():
    log_event("GET /api/schedule")
    data = get_ois2()
    events = []
    for code, subject in data.get("subjects", {}).items():
        for e in subject.get("events", []):
            if e.get("date"):
                events.append({
                    "subject_code": code,
                    "subject_name": subject.get("name", code),
                    "date": e.get("date"),
                    "time_start": e.get("time_start"),
                    "time_end": e.get("time_end"),
                    "type": e.get("type", "event"),
                    "description": e.get("description"),
                    "room": e.get("room"),
                })
    events.sort(key=lambda x: (x["date"] or "", x["time_start"] or ""))
    return events


@app.get("/api/deadlines")
async def get_deadlines():
    log_event("GET /api/deadlines")
    data = get_ois2()
    today = datetime.now().strftime("%Y-%m-%d")
    deadlines = []
    for code, subject in data.get("subjects", {}).items():
        for e in subject.get("events", []):
            if e.get("type") in ("deadline", "assignment", "exam"):
                date = e.get("date")
                if date and date >= today:
                    deadlines.append({
                        "subject_code": code,
                        "subject_name": subject.get("name", code),
                        "date": date,
                        "type": e.get("type"),
                        "description": e.get("description"),
                    })
    deadlines.sort(key=lambda x: x["date"])
    return deadlines[:20]


# ---------------------------------------------------------------
# RAG chat
# ---------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str
    n_results: int = 5


def retrieve_context(question: str, n: int = 5) -> list[dict]:
    collection = get_chroma()
    embedder = get_embedder()
    q_emb = embedder.encode([question])[0].tolist()
    results = collection.query(query_embeddings=[q_emb], n_results=n)

    contexts = []
    if results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            contexts.append({
                "text": doc,
                "metadata": meta,
                "score": round(1 - dist, 4),
            })
    return contexts


def build_rag_prompt(question: str, contexts: list[dict]) -> str:
    context_text = "\n\n".join(
        f"[Source {i+1}]: {c['text']}" for i, c in enumerate(contexts)
    )

    system = f"""You are NarvaConnect AI Assistant for Kyrylo Pryiomyshev at Narva Kolledz (Tartu Ulikool), IT Systems Development, Year 3 Spring 2026.

Answer questions using ONLY the CONTEXT below. If context doesn't contain the answer, say "I don't have that information."

Do NOT make up teacher names, subject codes, or dates. Use only what's in the context.

CONTEXT:
{context_text}"""

    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system}<|eot_id|><|start_header_id|>user<|end_header_id|>

{question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""


@app.post("/api/chat")
async def chat_rag(req: ChatRequest):
    log_event(f"POST /api/chat — question: {req.question[:80]}")

    # 1. Retrieve context
    contexts = retrieve_context(req.question, n=req.n_results)
    log_event(f"Retrieved {len(contexts)} documents from ChromaDB")
    for i, c in enumerate(contexts[:3]):
        log_event(f"  [{i+1}] score={c['score']} type={c['metadata'].get('type')}")

    # 2. Build prompt
    prompt = build_rag_prompt(req.question, contexts)

    # 3. Stream from MLX server (must be running on :8080)
    import httpx

    async def stream_tokens() -> AsyncIterator[str]:
        log_event(f"Querying inference server: {MLX_SERVER_URL}")
        token_count = 0
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "POST",
                    f"{MLX_SERVER_URL}/v1/completions",
                    json={
                        "prompt": prompt,
                        "max_tokens": 300,
                        "stream": True,
                        "temperature": 0.3,
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                obj = json.loads(data)
                                token = obj.get("choices", [{}])[0].get("text", "")
                                if token:
                                    token_count += 1
                                    yield f"data: {json.dumps({'token': token})}\n\n"
                            except Exception:
                                continue
        except httpx.ConnectError:
            msg = "AI assistant is offline. The inference server is currently unavailable. Try again later."
            log_event(f"Inference server offline ({MLX_SERVER_URL})")
            yield f"data: {json.dumps({'token': msg})}\n\n"
        except Exception as e:
            log_event(f"Inference error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        log_event(f"Generation done — {token_count} tokens")
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(stream_tokens(), media_type="text/event-stream")


# ---------------------------------------------------------------
# WebSocket log stream
# ---------------------------------------------------------------

@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    log_subscribers.add(websocket)
    log_event(f"WebSocket client connected ({len(log_subscribers)} total)")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        log_subscribers.discard(websocket)
        log_event(f"WebSocket client disconnected ({len(log_subscribers)} total)")


@app.get("/api/health")
async def health():
    return {"ok": True, "chroma_docs": get_chroma().count()}


if __name__ == "__main__":
    import uvicorn
    log_event("Starting NarvaConnect API on :3000")
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
