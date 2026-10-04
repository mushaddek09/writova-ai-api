FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y curl ca-certificates bash \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY start.sh .

RUN chmod +x /app/start.sh

ENV OLLAMA_HOST=0.0.0.0:11434

CMD ["/bin/bash", "/app/start.sh"]