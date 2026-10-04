#!/bin/bash

set -e

echo "Starting Ollama..."

ollama serve &

OLLAMA_PID=$!

echo "Waiting for Ollama..."

until curl -sf http://127.0.0.1:11434/api/tags > /dev/null
do
    sleep 2
done

echo "Ollama is ready."

echo "Checking Qwen3-14B..."

if ! ollama list | grep -q "qwen3:14b"; then

    echo "Downloading Qwen3-14B..."

    ollama pull qwen3:14b

fi

echo "Starting Writova API..."

exec uvicorn app:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000}