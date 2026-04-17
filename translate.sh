#!/usr/bin/env bash
# Fetch articles with translation: starts Ollama model, scrapes, then unloads the model.
# Usage:
#   ./translate.sh 2026-04-17
#   ./translate.sh 2026-04-10 2026-04-17
#   ./translate.sh 2026-04-17 --model qwen2.5:7b

set -e

MODEL="qwen2.5:3b"
POSITIONAL=()

# Parse arguments — extract --model if provided
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)
            MODEL="$2"
            shift 2
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done

if [[ ${#POSITIONAL[@]} -lt 1 ]]; then
    echo "Usage: $0 <from_date> [to_date] [--model <model>]"
    echo "       Dates in YYYY-MM-DD format"
    exit 1
fi

echo "[*] Pulling model $MODEL (skipped if already present)..."
ollama pull "$MODEL"

echo "[*] Loading model into memory..."
ollama run "$MODEL" "" > /dev/null 2>&1 || true

echo "[*] Running scraper with translation..."
uv run python scraper.py "${POSITIONAL[@]}" --translate --model "$MODEL"

echo "[*] Unloading model to free resources..."
ollama stop "$MODEL" 2>/dev/null || true

echo "[+] Done."
