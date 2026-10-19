"""Token estimation for prompts — offline heuristic, no dependencies.

Real tokenizers (tiktoken/BPE) need model vocab files. This module uses a
calibrated heuristic: ~4 characters per token for English prose, adjusted
for whitespace runs, punctuation, and long words. Good enough for
budgeting and context-window planning; documented as approximate.
"""

import re

# Average characters per token, calibrated on English prose.
_CHARS_PER_TOKEN = 4.0

# Model context windows (tokens) for the cost table.
_CONTEXT_WINDOWS = {
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "o1": 200_000,
    "o3-mini": 200_000,
    "claude-3-5-sonnet": 200_000,
    "claude-3-7-sonnet": 200_000,
    "gemini-2.0-flash": 1_000_000,
    "gemini-1.5-pro": 2_000_000,
}


def estimate_tokens(text):
    """Estimate token count for text. Returns int >= 0."""
    if not text or not text.strip():
        return 0
    # Collapse whitespace runs — they tokenize cheaply.
    collapsed = re.sub(r"\s+", " ", text.strip())
    chars = len(collapsed)
    # Long words (>12 chars) tend to split into multiple tokens.
    long_words = sum(1 for w in collapsed.split(" ") if len(w) > 12)
    estimate = chars / _CHARS_PER_TOKEN + long_words * 0.5
    return max(1, round(estimate))


def context_share(tokens, model="gpt-4o"):
    """Fraction of the model's context window used. Returns 0.0-1.0+."""
    window = _CONTEXT_WINDOWS.get(model, 128_000)
    return tokens / window if window else 0.0


def token_report(prompt, model="gpt-4o"):
    """Full report dict for a prompt: tokens, chars, words, context share."""
    tokens = estimate_tokens(prompt)
    words = len(prompt.split()) if prompt.strip() else 0
    return {
        "prompt": prompt,
        "tokens": tokens,
        "characters": len(prompt),
        "words": words,
        "model": model,
        "context_window": _CONTEXT_WINDOWS.get(model, 128_000),
        "context_share": round(context_share(tokens, model), 4),
        "note": "heuristic estimate (~4 chars/token); use a real tokenizer for exact counts",
    }
