"""Cost estimation for prompts — offline, zero dependencies.

Token counts come from the offline heuristic in tokens.py. Prices are
public rate-card snapshots (USD per 1M tokens) checked on the date in
each entry's "checked" field; providers change prices without notice.
Every report carries the check date, and `--in-price`/`--out-price`
let you pass your own contract rates for real budgets.
"""

from .tokens import estimate_tokens

# USD per 1M tokens, as published on the "checked" date.
# Sources consulted 2026-10-19:
#   - intuitionlabs.ai/articles/ai-api-pricing-comparison-grok-gemini-openai-claude
#     (table checked 2026-10-10: GPT-4o, Grok 4.7, Gemini 3.8 Flash, Claude Sonnet/Opus 5.5)
#   - tokenestimate.com/blog/ai-api-pricing-2026.html (2026-10, list prices)
#   - modelcostwatch.com/models/openai-gpt-4o (rates checked 2026-10-12)
MODEL_PRICES = {
    "gpt-4o": {
        "input": 2.50, "output": 10.00,
        "checked": "2026-10-19",
        "source": "intuitionlabs.ai (verified 2026-10-10) + modelcostwatch.com",
    },
    "gpt-4o-mini": {
        "input": 0.15, "output": 0.60,
        "checked": "2026-10-19",
        "source": "tokenestimate.com/blog/ai-api-pricing-2026.html",
    },
    "gpt-5": {
        "input": 1.25, "output": 10.00,
        "checked": "2026-10-19",
        "source": "tokenestimate.com/blog/ai-api-pricing-2026.html",
    },
    "gpt-5-mini": {
        "input": 0.25, "output": 2.00,
        "checked": "2026-10-19",
        "source": "tokenestimate.com/blog/ai-api-pricing-2026.html",
    },
    "claude-sonnet-5.5": {
        "input": 2.00, "output": 10.00,
        "checked": "2026-10-19",
        "source": "intuitionlabs.ai (verified 2026-10-10) + tech-insider.org",
    },
    "claude-opus-5.5": {
        "input": 4.00, "output": 20.00,
        "checked": "2026-10-19",
        "source": "intuitionlabs.ai (verified 2026-10-10)",
    },
    "claude-haiku-5.5": {
        "input": 0.10, "output": 0.50,
        "checked": "2026-10-19",
        "source": "intuitionlabs.ai (verified 2026-10-10)",
    },
    "gemini-3.8-flash": {
        "input": 0.75, "output": 3.75,
        "checked": "2026-10-19",
        "source": "intuitionlabs.ai (Standard tier through 2026-12-31)",
    },
    "gemini-3.1-pro": {
        "input": 2.00, "output": 12.00,
        "checked": "2026-10-19",
        "source": "tokenestimate.com/blog/ai-api-pricing-2026.html",
    },
    "grok-4.7": {
        "input": 2.00, "output": 6.00,
        "checked": "2026-10-19",
        "source": "intuitionlabs.ai (short-context rate)",
    },
    "gpt-6.1-sol": {
        "input": 2.00, "output": 10.00,
        "checked": "2026-10-19",
        "source": "intuitionlabs.ai (verified 2026-10-10)",
    },
}


def known_models():
    """Sorted list of models with snapshot prices."""
    return sorted(MODEL_PRICES)


def price_for(model):
    """Price entry for a model; raises ValueError listing known models."""
    entry = MODEL_PRICES.get(model)
    if entry is None:
        raise ValueError(
            f"unknown model '{model}'. Known models: {', '.join(known_models())} "
            "(or pass --in-price/--out-price to use your own rates)"
        )
    return entry


def cost_estimate(in_tokens, out_tokens, model=None, in_price=None, out_price=None):
    """USD cost for a request. in_price/out_price override the snapshot table."""
    if in_tokens < 0 or out_tokens < 0:
        raise ValueError("token counts must be >= 0")
    if model is None and (in_price is None or out_price is None):
        raise ValueError(
            "pass a model name (e.g. --model gpt-4o) or both --in-price and --out-price"
        )
    custom = False
    if model is not None:
        entry = price_for(model)
        if in_price is None:
            in_price = entry["input"]
        else:
            custom = True
        if out_price is None:
            out_price = entry["output"]
        else:
            custom = True
        checked = entry["checked"]
    else:
        custom = True
        checked = None
    in_cost = in_tokens / 1_000_000 * in_price
    out_cost = out_tokens / 1_000_000 * out_price
    return {
        "in_tokens": in_tokens,
        "out_tokens": out_tokens,
        "in_price_per_1m": in_price,
        "out_price_per_1m": out_price,
        "in_cost_usd": round(in_cost, 6),
        "out_cost_usd": round(out_cost, 6),
        "total_usd": round(in_cost + out_cost, 6),
        "model": model,
        "prices_custom": custom,
        "prices_checked": checked,
    }


def cost_report(prompt, model="gpt-4o", calls=1, out_ratio=1.0,
                in_price=None, out_price=None):
    """Full cost report for a prompt: estimated tokens plus per-call and
    N-call budget. Output tokens are estimated as tokens * out_ratio."""
    if calls < 1:
        raise ValueError("calls must be >= 1")
    if out_ratio < 0:
        raise ValueError("out_ratio must be >= 0")
    tokens = estimate_tokens(prompt)
    out_tokens = round(tokens * out_ratio)
    per_call = cost_estimate(tokens, out_tokens, model=model,
                             in_price=in_price, out_price=out_price)
    return {
        "prompt": prompt,
        "tokens": tokens,
        "out_tokens_estimate": out_tokens,
        "out_ratio": out_ratio,
        "calls": calls,
        "cost_per_call_usd": per_call["total_usd"],
        "budget_usd": round(per_call["total_usd"] * calls, 4),
        "model": per_call["model"],
        "in_price_per_1m": per_call["in_price_per_1m"],
        "out_price_per_1m": per_call["out_price_per_1m"],
        "prices_custom": per_call["prices_custom"],
        "prices_checked": per_call["prices_checked"],
        "note": "tokens are the offline heuristic (~4 chars/token); "
                "prices are a 2026-10-19 snapshot — verify with the provider "
                "before budgeting, or pass --in-price/--out-price",
    }
