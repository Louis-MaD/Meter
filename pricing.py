"""Hardcoded pricing for common OpenAI models (approximate, as of MVP)."""

# Prices in USD per 1M tokens
MODEL_PRICING = {
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4-turbo-preview": {"input": 10.0, "output": 30.0},
    "gpt-4o": {"input": 5.0, "output": 15.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    "gpt-3.5-turbo-16k": {"input": 3.0, "output": 4.0},
}


def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Calculate cost in USD for given token usage."""
    # Normalize model name (handle version suffixes)
    normalized_model = model
    for known_model in MODEL_PRICING.keys():
        if model.startswith(known_model):
            normalized_model = known_model
            break

    pricing = MODEL_PRICING.get(normalized_model)
    if not pricing:
        # Unknown model - use gpt-4o-mini pricing as conservative default
        pricing = MODEL_PRICING["gpt-4o-mini"]

    input_cost = (tokens_in / 1_000_000) * pricing["input"]
    output_cost = (tokens_out / 1_000_000) * pricing["output"]

    return input_cost + output_cost
