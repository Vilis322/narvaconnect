"""
Convert parsed ois2 JSON + moodle data into training JSONL for MLX LoRA fine-tuning.

Input:  data/processed/ois2_parsed.json (from screenshot parser)
Output: data/processed/training.jsonl (prompt/completion pairs)

Usage:
    python data/scripts/json_to_training.py
    python data/scripts/json_to_training.py --input data/processed/ois2_parsed.json --output data/processed/training.jsonl
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_parsed_data(input_path: str) -> dict:
    """Load the parsed ois2 JSON."""
    with open(input_path) as f:
        return json.load(f)


def generate_schedule_pairs(subjects: dict) -> list[dict]:
    """Generate Q&A pairs about schedule — when/where/who questions."""
    pairs = []

    for code, subject in subjects.items():
        name = subject["name"]
        events = subject.get("events", [])

        # Group events by type
        lectures = [e for e in events if e.get("type") == "lecture"]
        practices = [e for e in events if e.get("type") in ("practice", "lab")]
        deadlines = [e for e in events if e.get("type") in ("deadline", "assignment")]

        # --- "When is X?" questions ---
        if lectures:
            schedule_lines = []
            for lec in sorted(lectures, key=lambda e: e.get("date") or ""):
                date = lec.get("date", "TBD")
                time_s = lec.get("time_start", "")
                time_e = lec.get("time_end", "")
                week = lec.get("week", "")
                room = lec.get("room") or "online"
                time_str = f"{time_s}-{time_e}" if time_s else "TBD"
                week_str = f" (week {week})" if week else ""
                schedule_lines.append(f"  - {date} {time_str}, {room}{week_str}")

            pairs.append({
                "prompt": f"When is {name}?",
                "completion": f"{name} ({code}) lectures:\n" + "\n".join(schedule_lines[:10]),
            })

            # Day-of-week question
            if lectures[0].get("date"):
                try:
                    dt = datetime.strptime(lectures[0]["date"], "%Y-%m-%d")
                    day_name = dt.strftime("%A")
                    time_s = lectures[0].get("time_start", "")
                    time_e = lectures[0].get("time_end", "")
                    pairs.append({
                        "prompt": f"What day is {name}?",
                        "completion": f"{name} is on {day_name}s, {time_s}-{time_e}.",
                    })
                except ValueError:
                    pass

        # --- "What are the deadlines for X?" ---
        if deadlines:
            deadline_lines = []
            for dl in sorted(deadlines, key=lambda e: e.get("date") or ""):
                date = dl.get("date", "TBD")
                desc = dl.get("description", "Assignment")
                deadline_lines.append(f"  - {date}: {desc}")

            pairs.append({
                "prompt": f"What are the deadlines for {name}?",
                "completion": f"Deadlines for {name}:\n" + "\n".join(deadline_lines),
            })

        # --- "Tell me about X" ---
        teacher = None
        for e in events:
            if e.get("teacher"):
                teacher = e["teacher"]
                break

        total_events = len(events)
        teacher_str = f" taught by {teacher}" if teacher else ""
        pairs.append({
            "prompt": f"Tell me about {name}.",
            "completion": f"{name} ({code}){teacher_str}. This semester has {total_events} scheduled events: {len(lectures)} lectures, {len(practices)} practices/labs, {len(deadlines)} deadlines/assignments.",
        })

        # --- "Who teaches X?" ---
        if teacher:
            pairs.append({
                "prompt": f"Who teaches {name}?",
                "completion": f"{name} is taught by {teacher}.",
            })

    return pairs


def generate_daily_pairs(subjects: dict) -> list[dict]:
    """Generate 'what do I have on DAY?' questions."""
    pairs = []

    # Group all events by date
    by_date: dict[str, list] = defaultdict(list)
    for code, subject in subjects.items():
        for event in subject.get("events", []):
            date = event.get("date")
            if date:
                by_date[date].append({
                    **event,
                    "subject_code": code,
                    "subject_name": subject["name"],
                })

    # Group by day of week
    by_day: dict[str, list] = defaultdict(list)
    for date_str, events in by_date.items():
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_name = dt.strftime("%A")
            for e in events:
                by_day[day_name].append(e)
        except ValueError:
            continue

    for day_name, events in by_day.items():
        # Deduplicate by subject
        seen_subjects = set()
        unique_events = []
        for e in sorted(events, key=lambda x: x.get("time_start") or ""):
            key = (e["subject_name"], e.get("time_start", ""))
            if key not in seen_subjects:
                seen_subjects.add(key)
                unique_events.append(e)

        if unique_events:
            lines = []
            for e in unique_events[:5]:  # limit
                time_s = e.get("time_start", "TBD")
                time_e = e.get("time_end", "")
                time_str = f"{time_s}-{time_e}" if time_e else time_s
                room = e.get("room") or "online"
                lines.append(f"  - {time_str}: {e['subject_name']} ({room})")

            pairs.append({
                "prompt": f"What do I have on {day_name}?",
                "completion": f"Your {day_name} schedule:\n" + "\n".join(lines),
            })

    return pairs


def generate_deadline_overview(subjects: dict) -> list[dict]:
    """Generate overview questions about upcoming deadlines."""
    pairs = []

    all_deadlines = []
    for _code, subject in subjects.items():
        for event in subject.get("events", []):
            if event.get("type") in ("deadline", "assignment"):
                all_deadlines.append({
                    **event,
                    "subject_name": subject["name"],
                })

    if all_deadlines:
        sorted_deadlines = sorted(all_deadlines, key=lambda x: x.get("date") or "9999")
        lines = []
        for dl in sorted_deadlines[:10]:
            date = dl.get("date", "TBD")
            desc = dl.get("description", "Assignment")
            lines.append(f"  - {date}: {dl['subject_name']} — {desc}")

        pairs.append({
            "prompt": "What are my upcoming deadlines?",
            "completion": "Upcoming deadlines:\n" + "\n".join(lines),
        })

        pairs.append({
            "prompt": "What should I work on next?",
            "completion": f"Your next deadline is: {sorted_deadlines[0].get('date', 'TBD')} — {sorted_deadlines[0].get('subject_name', '')} ({sorted_deadlines[0].get('description', 'Assignment')}). I recommend starting with this.",
        })

    return pairs


def generate_semester_overview(subjects: dict) -> list[dict]:
    """Generate semester-level overview questions."""
    pairs = []

    subject_list = []
    for code, subject in subjects.items():
        subject_list.append(f"  - {subject['name']} ({code})")

    pairs.append({
        "prompt": "What subjects do I have this semester?",
        "completion": f"You have {len(subjects)} subjects this semester:\n" + "\n".join(sorted(subject_list)),
    })

    pairs.append({
        "prompt": "How many subjects am I taking?",
        "completion": f"You are taking {len(subjects)} subjects this semester.",
    })

    # Total events count
    total = sum(len(s.get("events", [])) for s in subjects.values())
    pairs.append({
        "prompt": "How many classes do I have this semester?",
        "completion": f"You have {total} scheduled events across {len(subjects)} subjects this semester.",
    })

    return pairs


def generate_multilingual_pairs(pairs_en: list[dict]) -> list[dict]:
    """Generate Estonian and Russian versions of key questions.

    Simple pattern-based translation for common schedule questions.
    """
    extra = []

    # Estonian translations for common patterns
    et_patterns = {
        "What do I have on Monday?": "Mis mul on esmaspäeval?",
        "What do I have on Tuesday?": "Mis mul on teisipäeval?",
        "What do I have on Wednesday?": "Mis mul on kolmapäeval?",
        "What do I have on Thursday?": "Mis mul on neljapäeval?",
        "What do I have on Friday?": "Mis mul on reedel?",
        "What are my upcoming deadlines?": "Millised on mu lähemad tähtajad?",
        "How many subjects am I taking?": "Mitu ainet ma õpin?",
    }

    # Russian translations
    ru_patterns = {
        "What do I have on Monday?": "Что у меня в понедельник?",
        "What do I have on Tuesday?": "Что у меня во вторник?",
        "What do I have on Wednesday?": "Что у меня в среду?",
        "What do I have on Thursday?": "Что у меня в четверг?",
        "What do I have on Friday?": "Что у меня в пятницу?",
        "What are my upcoming deadlines?": "Какие у меня ближайшие дедлайны?",
        "How many subjects am I taking?": "Сколько у меня предметов?",
    }

    for pair in pairs_en:
        prompt = pair["prompt"]

        if prompt in et_patterns:
            extra.append({
                "prompt": et_patterns[prompt],
                "completion": pair["completion"],
            })

        if prompt in ru_patterns:
            extra.append({
                "prompt": ru_patterns[prompt],
                "completion": pair["completion"],
            })

    return extra


def main():
    parser = argparse.ArgumentParser(description="Convert parsed ois2 JSON to training JSONL")
    parser.add_argument("--input", default="data/processed/ois2_parsed.json", help="Input JSON path")
    parser.add_argument("--output", default="data/processed/training.jsonl", help="Output JSONL path")
    args = parser.parse_args()

    # Resolve paths relative to project root
    project_root = Path(__file__).resolve().parent.parent.parent
    input_path = project_root / args.input
    output_path = project_root / args.output

    print(f"Loading parsed data from: {input_path}")
    data = load_parsed_data(str(input_path))
    subjects = data.get("subjects", {})
    print(f"Found {len(subjects)} subjects")

    # Generate all training pairs
    all_pairs = []

    schedule_pairs = generate_schedule_pairs(subjects)
    print(f"Schedule pairs: {len(schedule_pairs)}")
    all_pairs.extend(schedule_pairs)

    daily_pairs = generate_daily_pairs(subjects)
    print(f"Daily schedule pairs: {len(daily_pairs)}")
    all_pairs.extend(daily_pairs)

    deadline_pairs = generate_deadline_overview(subjects)
    print(f"Deadline pairs: {len(deadline_pairs)}")
    all_pairs.extend(deadline_pairs)

    semester_pairs = generate_semester_overview(subjects)
    print(f"Semester overview pairs: {len(semester_pairs)}")
    all_pairs.extend(semester_pairs)

    multilingual = generate_multilingual_pairs(all_pairs)
    print(f"Multilingual pairs: {len(multilingual)}")
    all_pairs.extend(multilingual)

    # Write JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"\nTotal training pairs: {len(all_pairs)}")
    print(f"Written to: {output_path}")
    print("\nNext step: MLX LoRA fine-tuning")
    print("  python -m mlx_lm.lora \\")
    print("    --model mlx-community/Meta-Llama-3.1-8B-Instruct-4bit \\")
    print(f"    --train-data {output_path} \\")
    print("    --adapter-path data/adapters/narvaconnect-v1 \\")
    print("    --num-epochs 3")


if __name__ == "__main__":
    main()
