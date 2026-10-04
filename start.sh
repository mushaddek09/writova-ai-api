#!/bin/bash

set -e

echo "================================="
echo "Starting Writova AI API"
echo "================================="

echo "Starting Ollama..."

ollama serve > /tmp/ollama.log 2>&1 &

OLLAMA_PID=$!

echo "Waiting for Ollama..."

for i in {1..60}; do
    if curl -sf http://127.0.0.1:11434/api/tags > /dev/null; then
        echo "Ollama is ready."
        break
    fi

    sleep 2
done

if ! curl -sf http://127.0.0.1:11434/api/tags > /dev/null; then
    echo "ERROR: Ollama failed to start."
    cat /tmp/ollama.log
    exit 1
fi

echo "Checking Qwen3-14B..."

if ! ollama list | grep -q "qwen3:14b"; then
    echo "Qwen3-14B not found."
    echo "Downloading Qwen3-14B..."

    ollama pull qwen3:14b
fi

echo "================================="
echo "Qwen3-14B is ready"
echo "================================="

echo "Starting FastAPI..."

exec uvicorn app:app \
    --host 0.0.0.0 \
    --port ${PORT:-8080}