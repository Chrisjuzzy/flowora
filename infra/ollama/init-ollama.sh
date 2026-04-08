#!/bin/sh
set -eu

OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
MODEL="${OLLAMA_PRELOAD_MODEL:-qwen2.5:7b-instruct}"

export OLLAMA_HOST

echo "Waiting for Ollama API at ${OLLAMA_HOST}..."
until ollama list >/dev/null 2>&1; do
  sleep 2
done

if ollama list | awk 'NR>1 {print $1}' | grep -qx "${MODEL}"; then
  echo "Model ${MODEL} already present."
else
  echo "Pulling model ${MODEL}..."
  ollama pull "${MODEL}"
fi

ollama show "${MODEL}" >/dev/null
echo "Ollama model ${MODEL} is ready."
