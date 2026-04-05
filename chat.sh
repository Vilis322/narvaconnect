#!/bin/bash
# chat.sh — test NarvaConnect AI adapter with proper Llama 3.1 chat template
# Usage: ./chat.sh "Your question here"

QUESTION="${1:-Who teaches Introduction to Data Science?}"
ADAPTER="${ADAPTER:-data/adapters/narvaconnect-v4}"
TODAY=$(date +%Y-%m-%d)

SYSTEM="You are NarvaConnect AI Assistant — a helpful assistant for Kyrylo Pryiomyshev, a student at Narva Kolledz (Tartu Ulikool), IT Systems Development program, Year 3, Semester 2 (Spring 2026). You know Kyrylo's current semester schedule, subjects, teachers, deadlines, and course materials. You can answer in English, Estonian, and Russian. Today's date is ${TODAY}. Be concise and helpful."

PROMPT="<|begin_of_text|><|start_header_id|>system<|end_header_id|>

${SYSTEM}<|eot_id|><|start_header_id|>user<|end_header_id|>

${QUESTION}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"

source .venv/bin/activate 2>/dev/null

python -m mlx_lm generate \
  --model mlx-community/Meta-Llama-3.1-8B-Instruct-4bit \
  --adapter-path "${ADAPTER}" \
  --prompt "${PROMPT}" \
  --max-tokens 200
