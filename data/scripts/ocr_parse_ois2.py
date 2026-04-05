"""
OCR-parse all ois2 screenshots using Tesseract (local, free, no API tokens).

Reads all PNG files from university/year3/semester2/*/ois2/
Extracts text via Tesseract OCR, then parses schedule events.
Writes results to data/processed/ois2_parsed.json

Usage:
    python data/scripts/ocr_parse_ois2.py
"""

import subprocess
import json
import re
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict


# Path constants
UNIVERSITY_DIR = Path.home() / "Projects/study/university/year3/semester2"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "processed"


def ocr_image(image_path: str) -> str:
    """Run Tesseract OCR on an image, return extracted text."""
    try:
        result = subprocess.run(
            ["tesseract", image_path, "stdout", "--psm", "6", "-l", "eng"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"  OCR error: {e}")
        return ""


def detect_subject_from_path(file_path: str) -> str:
    """Detect subject folder name from file path."""
    parts = Path(file_path).parts
    for i, part in enumerate(parts):
        if part == "ois2" and i > 0:
            return parts[i - 1]
    return "unknown"


def parse_course_code(text: str) -> str | None:
    """Extract course code like P2NC.01.095 from text."""
    match = re.search(r'[A-Z0-9]+\.[A-Z0-9]+\.[A-Z0-9]+', text)
    return match.group(0) if match else None


def parse_time_range(text: str) -> tuple[str | None, str | None]:
    """Extract time range like 17:40 - 19:20 from text."""
    match = re.search(r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})', text)
    if match:
        return match.group(1), match.group(2)
    # Single time
    match = re.search(r'(\d{1,2}:\d{2})\s+\d{2}/\d{2}/\d{4}', text)
    if match:
        return match.group(1), None
    return None, None


def parse_date(text: str) -> str | None:
    """Extract date in format DD/MM/YYYY and convert to YYYY-MM-DD."""
    match = re.search(r'(\d{2})/(\d{2})/(\d{4})', text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    # Also try DD.MM.YYYY in parentheses
    match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    return None


def parse_weeks(text: str) -> list[int]:
    """Extract week numbers from text like 'weeks 25-29, 31-32, 35'."""
    weeks = []
    match = re.search(r'weeks?\s+([\d,\s\-–]+)', text, re.IGNORECASE)
    if match:
        parts = re.split(r'[,\s]+', match.group(1).strip())
        for part in parts:
            if '-' in part or '–' in part:
                range_parts = re.split(r'[-–]', part)
                if len(range_parts) == 2:
                    try:
                        start, end = int(range_parts[0]), int(range_parts[1])
                        weeks.extend(range(start, end + 1))
                    except ValueError:
                        pass
            else:
                try:
                    weeks.append(int(part))
                except ValueError:
                    pass
    return weeks


def parse_week_number(text: str) -> int | None:
    """Extract single week number like 'Week 1' or 'Week 14'."""
    match = re.search(r'Week\s+(\d+)', text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def detect_event_type(text: str) -> str:
    """Detect event type from text content."""
    text_lower = text.lower()
    if "lecture" in text_lower or "loeng" in text_lower:
        return "lecture"
    if "practice" in text_lower or "praktikum" in text_lower or "praks" in text_lower:
        return "practice"
    if "lab" in text_lower:
        return "lab"
    if "exam" in text_lower or "eksam" in text_lower:
        return "exam"
    if "deadline" in text_lower or "tähtaeg" in text_lower:
        return "deadline"
    if "assignment" in text_lower or "ülesanne" in text_lower:
        return "assignment"
    if "seminar" in text_lower:
        return "seminar"
    if "quiz" in text_lower or "küsitlus" in text_lower:
        return "assignment"
    if "group" in text_lower:
        return "assignment"
    return "event"


def parse_teacher(text: str) -> str | None:
    """Extract teacher name — typically after & or Source: My timetable."""
    # Look for names after common patterns
    patterns = [
        r'&\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'[Oo]ppejõud:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def parse_room(text: str) -> str | None:
    """Extract room number or location."""
    if "online" in text.lower():
        return "online"
    if "e-learning" in text.lower() or "e-õpe" in text.lower():
        return "e-learning"
    # Room patterns: aud. 215, room 301, ruum 215
    match = re.search(r'(?:aud|room|ruum)\.?\s*(\d+)', text, re.IGNORECASE)
    if match:
        return f"room {match.group(1)}"
    return None


def parse_screenshot_text(text: str, subject_folder: str) -> list[dict]:
    """Parse OCR text from a single screenshot into events."""
    events = []

    # Split into logical blocks (separated by empty lines or @ markers)
    blocks = re.split(r'\n\s*\n|(?=@\s)', text)

    course_code = parse_course_code(text)
    teacher = parse_teacher(text)
    room = parse_room(text)

    for block in blocks:
        block = block.strip()
        if not block or len(block) < 5:
            continue

        date = parse_date(block)
        time_start, time_end = parse_time_range(block)
        event_type = detect_event_type(block)
        week = parse_week_number(block)
        weeks = parse_weeks(block)

        # Skip blocks that are just source labels
        if block.startswith("Source:") or block.startswith("Close"):
            continue

        # Only create event if we have meaningful data
        if date or time_start or (course_code and event_type != "event"):
            # Clean description: take first meaningful line
            desc_lines = [l.strip() for l in block.split('\n')
                         if l.strip() and not l.strip().startswith('Source:')
                         and not l.strip().startswith('@')
                         and 'Moodle' not in l
                         and 'Online link' not in l
                         and 'Close' not in l]
            description = ' '.join(desc_lines[:2]) if desc_lines else None

            events.append({
                "type": event_type,
                "date": date,
                "time_start": time_start,
                "time_end": time_end,
                "week": week,
                "weeks": weeks if weeks else None,
                "description": description,
                "room": room,
                "teacher": teacher,
                "course_code": course_code,
                "source": "ois2_ocr",
            })

    return events


# Known subject code → name mapping
SUBJECT_NAMES = {
    "P2NC.01.095": "Analysis and Design of Information Systems",
    "LTAT.05.005": "Introduction to Data Science",
    "P2NC.00.200": "Software Engineering",
    "P2NC.00.248": "Software Testing",
    "P2NC.00.384": "Starting a Business",
    "P2NC.00.330": "Web Application Development",
    "P2NC.00.197": "Practical Project Training",
    "P2NC.00.189": "Introductory Practice",
}


def main():
    print("=" * 60)
    print("  NarvaConnect — OCR Schedule Parser (Tesseract)")
    print("  Free, local, no API tokens")
    print("=" * 60)

    # Find all ois2 screenshot directories
    ois2_dirs = sorted(UNIVERSITY_DIR.glob("*/ois2"))
    # Also check root ois2/ and ois2_subjects/
    root_ois2 = UNIVERSITY_DIR / "ois2"
    root_ois2_subjects = UNIVERSITY_DIR / "ois2_subjects"

    all_images = []
    for d in ois2_dirs:
        images = sorted(d.glob("*.png"))
        all_images.extend([(str(img), detect_subject_from_path(str(img))) for img in images])

    if root_ois2.exists():
        for img in sorted(root_ois2.glob("*.png")):
            all_images.append((str(img), "general"))

    if root_ois2_subjects.exists():
        for img in sorted(root_ois2_subjects.glob("*.png")):
            all_images.append((str(img), "subject_descriptions"))

    print(f"\nFound {len(all_images)} screenshots to parse\n")

    # Parse all images
    subjects: dict[str, dict] = {}
    raw_texts: dict[str, str] = {}  # Save raw OCR for debugging
    parsed_count = 0
    error_count = 0

    for i, (image_path, subject_folder) in enumerate(all_images):
        filename = Path(image_path).name
        print(f"[{i+1}/{len(all_images)}] {subject_folder}/{filename}", end=" ... ")

        text = ocr_image(image_path)
        if not text:
            print("EMPTY")
            error_count += 1
            continue

        raw_texts[image_path] = text

        events = parse_screenshot_text(text, subject_folder)
        print(f"{len(events)} events")

        for event in events:
            code = event.pop("course_code", None)
            if not code:
                # Try to find from subject folder name
                for known_code, known_name in SUBJECT_NAMES.items():
                    folder_words = subject_folder.replace("_", " ").lower()
                    if any(w in known_name.lower() for w in folder_words.split()):
                        code = known_code
                        break

            if not code:
                code = f"UNKNOWN_{subject_folder.upper()}"

            if code not in subjects:
                name = SUBJECT_NAMES.get(code, subject_folder.replace("_", " ").title())
                subjects[code] = {"name": name, "events": []}

            subjects[code]["events"].append(event)
            parsed_count += 1

    # Write output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output = {
        "subjects": subjects,
        "parsed_at": datetime.now().isoformat(),
        "total_screenshots": len(all_images),
        "total_events": parsed_count,
        "errors": error_count,
        "method": "tesseract_ocr",
        "note": "Parsed locally with Tesseract 5.5.2, zero API tokens used",
    }

    output_path = OUTPUT_DIR / "ois2_parsed.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Also save raw OCR texts for debugging
    raw_path = OUTPUT_DIR / "ois2_raw_ocr.json"
    with open(raw_path, "w") as f:
        json.dump(raw_texts, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"  Done!")
    print(f"  Screenshots: {len(all_images)}")
    print(f"  Events parsed: {parsed_count}")
    print(f"  Subjects found: {len(subjects)}")
    print(f"  Errors: {error_count}")
    print(f"  Output: {output_path}")
    print(f"  Raw OCR: {raw_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
