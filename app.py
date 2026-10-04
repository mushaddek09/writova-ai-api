import os
import uuid
import time
import httpx

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="Writova AI API")

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11434"
)

API_KEY = os.getenv("API_KEY", "")
DEFAULT_MODEL = os.getenv(
    "MODEL",
    "qwen3:14b"
)


def check_auth(request: Request):
    if not API_KEY:
        return

    auth = request.headers.get("Authorization", "")

    if auth != f"Bearer {API_KEY}":
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )


def extract_input_text(data):
    """
    Supports OpenAI Responses API input as:
    - string
    - list of message/content objects
    """

    input_data = data.get("input", "")

    if isinstance(input_data, str):
        return input_data

    if not isinstance(input_data, list):
        return str(input_data)

    parts = []

    for item in input_data:

        if not isinstance(item, dict):
            continue

        content = item.get("content", "")

        if isinstance(content, str):
            parts.append(content)

        elif isinstance(content, list):

            for part in content:

                if not isinstance(part, dict):
                    continue

                if part.get("type") in (
                    "input_text",
                    "text"
                ):
                    if part.get("text"):
                        parts.append(part["text"])

    return "\n".join(parts)


def build_prompt(data):

    instructions = data.get(
        "instructions",
        ""
    )

    user_input = extract_input_text(data)

    return {
        "system": instructions,
        "user": user_input
    }


@app.get("/")
async def root():

    return {
        "service": "Writova AI API",
        "status": "online",
        "model": DEFAULT_MODEL
    }


@app.get("/health")
async def health():

    try:

        async with httpx.AsyncClient(timeout=10) as client:

            response = await client.get(
                f"{OLLAMA_URL}/api/tags"
            )

            if response.status_code != 200:
                return {
                    "status": "unhealthy",
                    "ollama": False
                }

        return {
            "status": "healthy",
            "ollama": True,
            "model": DEFAULT_MODEL
        }

    except Exception as e:

        return {
            "status": "unhealthy",
            "ollama": False,
            "error": str(e)
        }


@app.post("/v1/responses")
async def responses(request: Request):

    check_auth(request)

    data = await request.json()

    model = data.get(
        "model",
        DEFAULT_MODEL
    )

    prompt = build_prompt(data)

    max_output_tokens = data.get(
        "max_output_tokens",
        6000
    )

    text_config = data.get("text", {})

    output_format = None

    if isinstance(text_config, dict):

        format_config = text_config.get(
            "format"
        )

        if isinstance(format_config, dict):

            if format_config.get("type") == "json_schema":

                schema = format_config.get(
                    "schema"
                )

                if schema:
                    output_format = schema

            elif format_config.get("type") == "json":

                output_format = "json"

    messages = []

    if prompt["system"]:
        messages.append({
            "role": "system",
            "content": prompt["system"]
        })

    if prompt["user"]:
        messages.append({
            "role": "user",
            "content": prompt["user"]
        })

    ollama_payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.6,
            "top_p": 0.95,
            "num_predict": max_output_tokens,
            "repeat_penalty": 1.05
        }
    }

    if output_format:
        ollama_payload["format"] = output_format

    started = time.time()

    try:

        async with httpx.AsyncClient(
            timeout=600
        ) as client:

            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json=ollama_payload
            )

        if response.status_code != 200:

            raise HTTPException(
                status_code=502,
                detail=response.text
            )

        result = response.json()

    except httpx.TimeoutException:

        raise HTTPException(
            status_code=504,
            detail="Model generation timed out"
        )

    content = (
        result
        .get("message", {})
        .get("content", "")
    )

    if not content:

        raise HTTPException(
            status_code=502,
            detail="Empty model response"
        )

    response_id = "resp_" + uuid.uuid4().hex

    elapsed = time.time() - started

    return JSONResponse({

        "id": response_id,

        "object": "response",

        "created_at": int(time.time()),

        "model": model,

        "status": "completed",

        "output_text": content,

        "output": [
            {
                "type": "message",
                "id": "msg_" + uuid.uuid4().hex,
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": content,
                        "annotations": []
                    }
                ]
            }
        ],

        "usage": {
            "input_tokens": result
            .get("prompt_eval_count", 0),

            "output_tokens": result
            .get("eval_count", 0),

            "total_tokens":
                result.get(
                    "prompt_eval_count",
                    0
                )
                +
                result.get(
                    "eval_count",
                    0
                )
        },

        "metadata": {
            "generation_time":
                round(elapsed, 2)
        }

    })