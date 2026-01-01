import hashlib
from datetime import datetime
from database import get_db
from pricing import calculate_cost


def hash_prompt(messages: list) -> str:
    """Create a deterministic hash of the prompt messages."""
    prompt_str = str(messages)
    return hashlib.sha256(prompt_str.encode()).hexdigest()[:16]


def log_usage(
    model: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: int,
    team: str,
    feature: str,
    environment: str,
    messages: list,
):
    """Log usage to database."""
    cost = calculate_cost(model, tokens_in, tokens_out)
    prompt_hash = hash_prompt(messages)
    timestamp = datetime.utcnow().isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO usage_logs (
                timestamp, model, tokens_in, tokens_out, cost,
                latency_ms, team, feature, environment, prompt_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                model,
                tokens_in,
                tokens_out,
                cost,
                latency_ms,
                team,
                feature,
                environment,
                prompt_hash,
            ),
        )
        conn.commit()
