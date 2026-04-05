#!/bin/bash
# ask.sh — RAG query with assembled streaming output
# Usage: ./ask.sh "Your question"

QUESTION="${1:-Who teaches Data Science?}"
API="${API:-http://localhost:3000}"

echo ""
echo "> $QUESTION"
echo ""

curl -N -s -X POST "${API}/api/chat" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"${QUESTION}\"}" | \
  while IFS= read -r line; do
    if [[ "$line" =~ ^data:\ (.+)$ ]]; then
      data="${BASH_REMATCH[1]}"
      token=$(echo "$data" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('token',''), end='', flush=True)" 2>/dev/null)
      printf "%s" "$token"
    fi
  done

echo ""
echo ""
