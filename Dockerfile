FROM ollama/ollama:latest

RUN apt-get update \
    && apt-get install -y python3 python3-pip curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip3 install --break-system-packages -r requirements.txt

COPY app.py .
COPY start.sh .

RUN chmod +x /app/start.sh

ENV OLLAMA_HOST=0.0.0.0:11434

ENTRYPOINT ["/bin/bash", "/app/start.sh"]