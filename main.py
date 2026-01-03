import os
import time
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
from dotenv import load_dotenv
from database import init_db, get_db, get_today_spend
from logger import log_usage

load_dotenv()

app = FastAPI(title="Meter - AI Token Attribution Proxy")

PROXY_API_KEY = os.getenv("PROXY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
DAILY_SPEND_CAP = float(os.getenv("METER_DAILY_SPEND_CAP", "5.0"))

if not PROXY_API_KEY:
    raise ValueError("PROXY_API_KEY environment variable is required")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")


@app.on_event("startup")
def startup():
    init_db()


def verify_api_key(authorization: str = Header(None)):
    """Verify the proxy API key."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    token = authorization.replace("Bearer ", "")
    if token != PROXY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    authorization: str = Header(None),
    x_team: str = Header(None),
    x_feature: str = Header(None),
    x_environment: str = Header(None),
):
    """Proxy endpoint for OpenAI chat completions."""
    verify_api_key(authorization)

    # Check daily spend cap
    today_spend = get_today_spend()
    if today_spend >= DAILY_SPEND_CAP:
        raise HTTPException(
            status_code=429,
            detail={"error": "Meter daily spend cap reached. Requests temporarily disabled."}
        )

    # Extract metadata with defaults
    team = x_team or "unknown"
    feature = x_feature or "unknown"
    environment = x_environment or "unknown"

    # Parse request body
    body = await request.json()
    model = body.get("model", "unknown")
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    # Forward request to OpenAI
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        if stream:
            # Handle streaming response
            async def stream_and_log():
                tokens_in = 0
                tokens_out = 0
                response_model = model

                async with client.stream(
                    "POST",
                    f"{OPENAI_BASE_URL}/chat/completions",
                    json=body,
                    headers=headers,
                    timeout=300.0,
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise HTTPException(
                            status_code=response.status_code, detail=error_text.decode()
                        )

                    async for chunk in response.aiter_bytes():
                        yield chunk

                        # Parse usage from stream chunks if available
                        # Note: OpenAI doesn't always send usage in stream mode
                        # This is a limitation we accept for MVP

                # For streaming, we log with estimated tokens (or 0 if unavailable)
                # This is acceptable for MVP - consistency over accuracy
                latency_ms = int((time.time() - start_time) * 1000)
                log_usage(
                    model=response_model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=latency_ms,
                    team=team,
                    feature=feature,
                    environment=environment,
                    messages=messages,
                )

            return StreamingResponse(
                stream_and_log(),
                media_type="text/event-stream",
            )

        else:
            # Handle non-streaming response
            response = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                json=body,
                headers=headers,
                timeout=300.0,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, detail=response.json()
                )

            response_data = response.json()

            # Extract usage
            usage = response_data.get("usage", {})
            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)
            response_model = response_data.get("model", model)

            # Log usage
            log_usage(
                model=response_model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                team=team,
                feature=feature,
                environment=environment,
                messages=messages,
            )

            return JSONResponse(content=response_data)


@app.get("/usage")
def get_usage(group_by: str = None):
    """Get usage statistics, optionally grouped by team, feature, or environment."""
    with get_db() as conn:
        cursor = conn.cursor()

        if group_by in ["team", "feature", "environment"]:
            # Grouped query
            query = f"""
                SELECT
                    {group_by} as group_name,
                    SUM(tokens_in) as total_tokens_in,
                    SUM(tokens_out) as total_tokens_out,
                    SUM(tokens_in + tokens_out) as total_tokens,
                    SUM(cost) as total_cost,
                    COUNT(*) as request_count
                FROM usage_logs
                GROUP BY {group_by}
                ORDER BY total_cost DESC
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    group_by: row["group_name"],
                    "total_tokens_in": row["total_tokens_in"],
                    "total_tokens_out": row["total_tokens_out"],
                    "total_tokens": row["total_tokens"],
                    "total_cost": round(row["total_cost"], 6),
                    "request_count": row["request_count"],
                })

            return JSONResponse(content={"grouped_by": group_by, "results": results}, indent=2)

        else:
            # Overall summary
            query = """
                SELECT
                    SUM(tokens_in) as total_tokens_in,
                    SUM(tokens_out) as total_tokens_out,
                    SUM(tokens_in + tokens_out) as total_tokens,
                    SUM(cost) as total_cost,
                    COUNT(*) as request_count
                FROM usage_logs
            """
            cursor.execute(query)
            row = cursor.fetchone()

            return JSONResponse(
                content={
                    "total_tokens_in": row["total_tokens_in"] or 0,
                    "total_tokens_out": row["total_tokens_out"] or 0,
                    "total_tokens": row["total_tokens"] or 0,
                    "total_cost": round(row["total_cost"] or 0, 6),
                    "request_count": row["request_count"] or 0,
                },
                indent=2
            )


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
