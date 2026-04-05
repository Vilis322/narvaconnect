"""
Convert prompt/completion JSONL into chat-format JSONL for MLX LoRA.

Usage:
    python data/scripts/prepare_chat_training.py
"""

import json
import random
from datetime import datetime
from pathlib import Path

SYSTEM_PROMPT = (
    "You are NarvaConnect AI Assistant — a helpful assistant for Kyrylo Pryiomyshev, "
    "a student at Narva Kolledž (Tartu Ülikool), IT Systems Development program, Year 3, Semester 2 (Spring 2026). "
    "You know Kyrylo's current semester schedule, subjects, teachers, deadlines, and course materials. "
    "You can answer in English, Estonian (eesti keel), and Russian (русский). "
    f"Today's date is {datetime.now().strftime('%Y-%m-%d')}. "
    "\n\nTeachers this semester:\n"
    "- Erika Lorents, PhD — Introduction to Data Science (SVNC.00.228)\n"
    "- Daria Chukhlebova — Analysis and Design of Information Systems (P2NC.01.095)\n"
    "- Nicolai Morozov — Software Engineering (SVNC.00.308)\n"
    "- André Sääsk — Software Testing (SVNC.00.058), Web Application Development (P2NC.01.094)\n"
    "- Tiit Urva — Starting a Business (P2NC.01.050)\n"
    "- Sudath Rohan Munasinghe — Practical Project-based Training in IT (SVNC.00.184)\n"
    "- Pavel Kodõtšikov — Introductory Practice (Tutvumispraktika)\n"
    "\nBe concise and helpful. When discussing deadlines, mention how many days remain from today. "
    "Always refer to yourself as NarvaConnect AI Assistant."
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "combined_training_v2.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "chat_train_data_v2"


def convert_to_chat(prompt: str, completion: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": completion},
        ]
    }


def main():
    print("=" * 60)
    print("  NarvaConnect — Chat Training Data v2")
    print("=" * 60)

    pairs = []
    with open(INPUT_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                pairs.append(json.loads(line))

    print(f"Loaded: {len(pairs)} pairs")

    chat_data = []
    for pair in pairs:
        prompt = pair.get("prompt", "")
        completion = pair.get("completion", "")
        if prompt and completion and len(completion) > 10:
            chat_data.append(convert_to_chat(prompt, completion))

    print(f"Valid chat pairs: {len(chat_data)}")

    random.seed(42)
    random.shuffle(chat_data)
    split = int(len(chat_data) * 0.9)
    train = chat_data[:split]
    valid = chat_data[split:]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_DIR / "train.jsonl", "w") as f:
        for item in train:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(OUTPUT_DIR / "valid.jsonl", "w") as f:
        for item in valid:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\nTrain: {len(train)} -> {OUTPUT_DIR / 'train.jsonl'}")
    print(f"Valid: {len(valid)} -> {OUTPUT_DIR / 'valid.jsonl'}")

    # Optimal iters: val loss was best at ~iter 400 last run (5 epochs)
    # With 478 pairs, 5 epochs = 478*5/4 ≈ 600 iters
    iters = len(train) * 5 // 4
    print("\n--- Recommended training (5 epochs, best val loss zone) ---")
    print("python -m mlx_lm lora \\")
    print("  --model mlx-community/Meta-Llama-3.1-8B-Instruct-4bit \\")
    print(f"  --data {OUTPUT_DIR} \\")
    print("  --adapter-path data/adapters/narvaconnect-v3 \\")
    print(f"  --train --iters {iters} --batch-size 4 --learning-rate 5e-5 \\")
    print("  --steps-per-report 25 --save-every 200")


if __name__ == "__main__":
    main()
