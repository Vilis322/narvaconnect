"""
Build RAG knowledge base from all parsed documents + manual teacher facts.

Creates ChromaDB collection with embeddings from:
- Teacher facts (high priority)
- Schedule events from ois2
- Moodle document excerpts

Usage:
    python data/scripts/build_rag.py
"""

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = DATA_DIR / "chromadb"

# Authoritative teacher facts (highest priority)
TEACHERS = {
    "Introduction to Data Science": {"code": "SVNC.00.228", "teacher": "Erika Lorents, PhD"},
    "Analysis and Design of Information Systems": {"code": "P2NC.01.095", "teacher": "Daria Chukhlebova"},
    "Software Engineering": {"code": "SVNC.00.308", "teacher": "Nicolai Morozov"},
    "Software Testing": {"code": "SVNC.00.058", "teacher": "André Sääsk"},
    "Starting a Business": {"code": "P2NC.01.050", "teacher": "Tiit Urva"},
    "Web Application Development": {"code": "P2NC.01.094", "teacher": "André Sääsk"},
    "Practical Project-based Training in IT": {"code": "SVNC.00.184", "teacher": "Sudath Rohan Munasinghe"},
    "Introductory Practice": {"code": "Tutvumispraktika", "teacher": "Pavel Kodõtšikov"},
}


def load_embedding_model():
    print("Loading sentence-transformers model...")
    return SentenceTransformer('all-MiniLM-L6-v2')


def build_teacher_facts() -> list[dict]:
    """Build high-priority teacher facts with strong authority."""
    facts = []

    for subject, info in TEACHERS.items():
        # Multiple phrasings for each teacher fact
        facts.append({
            "id": f"teacher-{info['code']}",
            "text": f"AUTHORITATIVE FACT: {subject} (course code {info['code']}) is taught by {info['teacher']} this semester (Spring 2026).",
            "metadata": {
                "type": "teacher_fact",
                "subject": subject,
                "code": info["code"],
                "teacher": info["teacher"],
                "priority": "high",
            }
        })

    # Summary document
    teacher_list = "\n".join(
        f"- {info['teacher']} teaches {subject} ({info['code']})"
        for subject, info in TEACHERS.items()
    )
    facts.append({
        "id": "teachers-summary",
        "text": f"Complete list of all teachers for Spring 2026 semester at Narva Kolledž:\n{teacher_list}",
        "metadata": {"type": "summary", "priority": "high"}
    })

    # Reverse index: teacher -> subject
    for subject, info in TEACHERS.items():
        facts.append({
            "id": f"teacher-reverse-{info['code']}",
            "text": f"{info['teacher']} is the instructor for {subject} ({info['code']}) during Spring 2026 semester at Narva Kolledž.",
            "metadata": {
                "type": "teacher_reverse",
                "subject": subject,
                "code": info["code"],
                "teacher": info["teacher"],
                "priority": "high",
            }
        })

    print(f"Teacher facts: {len(facts)}")
    return facts


def load_ois2_events() -> list[dict]:
    """Load schedule events from parsed ois2 data."""
    events_file = DATA_DIR / "processed" / "ois2_parsed.json"
    if not events_file.exists():
        print(f"Warning: {events_file} not found, skipping")
        return []

    with open(events_file) as f:
        data = json.load(f)

    docs = []
    for code, subject in data.get("subjects", {}).items():
        for i, event in enumerate(subject.get("events", [])):
            date = event.get("date") or "TBD"
            time_s = event.get("time_start") or ""
            time_e = event.get("time_end") or ""
            desc = event.get("description") or event.get("type", "event")
            room = event.get("room") or "online"

            text = f"Schedule event: {subject.get('name', code)} - {date} {time_s}-{time_e}, {room}, type: {event.get('type', 'event')}, description: {desc}"

            docs.append({
                "id": f"event-{code}-{i}",
                "text": text,
                "metadata": {
                    "type": "schedule_event",
                    "subject_code": code,
                    "subject_name": subject.get("name", code),
                    "date": date,
                    "event_type": event.get("type", "event"),
                    "priority": "medium",
                }
            })

    print(f"Schedule events: {len(docs)}")
    return docs


def load_moodle_docs() -> list[dict]:
    """Load Moodle document summaries from parsed moodle data."""
    moodle_file = DATA_DIR / "processed" / "moodle_parsed.json"
    if not moodle_file.exists():
        print(f"Warning: {moodle_file} not found, skipping")
        return []

    with open(moodle_file) as f:
        data = json.load(f)

    docs = []
    for i, doc in enumerate(data.get("documents", [])):
        subject = doc.get("subject", "")
        filename = doc.get("filename", "")
        preview = doc.get("text_preview", "")

        if not preview or len(preview) < 30:
            continue

        text = f"Document from {subject}, file '{filename}': {preview}"

        docs.append({
            "id": f"moodle-{i}",
            "text": text[:1500],  # Keep chunks manageable
            "metadata": {
                "type": "moodle_doc",
                "subject": subject,
                "filename": filename,
                "priority": "low",
            }
        })

    print(f"Moodle documents: {len(docs)}")
    return docs


def build_rag_index():
    """Main: build ChromaDB collection with all documents."""
    print("=" * 60)
    print("  NarvaConnect RAG — Building Knowledge Base")
    print("=" * 60)

    # Load embedding model
    model = load_embedding_model()

    # Initialize ChromaDB (persistent, local)
    print(f"\nInitializing ChromaDB at {CHROMA_DIR}")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Drop existing collection if present
    try:
        client.delete_collection("narvaconnect")
        print("Dropped existing collection")
    except Exception:
        pass

    collection = client.create_collection(
        name="narvaconnect",
        metadata={"description": "NarvaConnect knowledge base", "version": "1.0"},
    )

    # Gather all documents
    all_docs = []
    all_docs.extend(build_teacher_facts())
    all_docs.extend(load_ois2_events())
    all_docs.extend(load_moodle_docs())

    print(f"\nTotal documents to index: {len(all_docs)}")

    # Generate embeddings in batches
    print("Generating embeddings...")
    texts = [d["text"] for d in all_docs]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)

    # Add to ChromaDB
    print("Adding to ChromaDB...")
    collection.add(
        documents=texts,
        embeddings=embeddings.tolist(),
        metadatas=[d["metadata"] for d in all_docs],
        ids=[d["id"] for d in all_docs],
    )

    print(f"\n{'=' * 60}")
    print(f"  Done! Indexed {collection.count()} documents")
    print(f"  Location: {CHROMA_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    build_rag_index()
