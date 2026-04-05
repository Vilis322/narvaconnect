"""
Query RAG: search ChromaDB + generate answer with Llama via MLX.

Usage:
    python data/scripts/rag_query.py "Who teaches Data Science?"
"""

import sys
import argparse
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CHROMA_DIR = PROJECT_ROOT / "data" / "chromadb"


def retrieve_context(question: str, n_results: int = 5) -> list[dict]:
    """Search ChromaDB for relevant documents."""
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection("narvaconnect")

    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode([question])[0].tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )

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


def build_prompt(question: str, contexts: list[dict]) -> str:
    """Build Llama 3.1 chat template with RAG context."""
    context_text = "\n\n".join(
        f"[Source {i+1}, relevance {c['score']}]: {c['text']}"
        for i, c in enumerate(contexts)
    )

    system = f"""You are NarvaConnect AI Assistant for Kyrylo Pryiomyshev, a student at Narva Kolledž (Tartu Ülikool), IT Systems Development, Year 3, Semester 2 (Spring 2026).

Answer questions using ONLY the CONTEXT below. If the context doesn't contain the answer, say "I don't have information about that in my knowledge base."

Do NOT make up information. Do NOT invent teacher names or subject codes. Use only what's in the context.

CONTEXT:
{context_text}"""

    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system}<|eot_id|><|start_header_id|>user<|end_header_id|>

{question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""


def main():
    parser = argparse.ArgumentParser(description="RAG query for NarvaConnect")
    parser.add_argument("question", help="Your question")
    parser.add_argument("--n", type=int, default=5, help="Number of context docs to retrieve")
    parser.add_argument("--show-context", action="store_true", help="Show retrieved context")
    args = parser.parse_args()

    print(f"Question: {args.question}\n")
    print("Retrieving context from ChromaDB...")

    contexts = retrieve_context(args.question, n_results=args.n)

    if args.show_context:
        print(f"\n--- Retrieved {len(contexts)} documents ---")
        for i, c in enumerate(contexts):
            print(f"\n[{i+1}] Score: {c['score']} Type: {c['metadata'].get('type', 'unknown')}")
            print(f"    {c['text'][:200]}")

    prompt = build_prompt(args.question, contexts)

    # Save prompt for MLX generation
    prompt_file = PROJECT_ROOT / "data" / "processed" / "_rag_prompt.txt"
    prompt_file.write_text(prompt)

    print(f"\nPrompt saved to: {prompt_file}")
    print("\nNow generate with MLX:")
    print(f'  python -m mlx_lm generate \\')
    print(f'    --model mlx-community/Meta-Llama-3.1-8B-Instruct-4bit \\')
    print(f'    --prompt "$(cat {prompt_file})" \\')
    print(f'    --max-tokens 300')


if __name__ == "__main__":
    main()
