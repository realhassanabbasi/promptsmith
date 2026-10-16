"""One-shot improvement: score, enhance, re-score — with proof it got better.

Chains the enhancer and the head-to-head comparison, so a single command
answers "is my prompt actually better now?" on the same 5-check rubric.
"""

from .compare import compare_prompts
from .enhancer import enhance


def improve_prompt(raw, intent=None, confidence=None):
    """Score `raw`, enhance it, then compare original vs enhanced.

    Returns a dict with the intent, confidence, the before/after
    score payloads, per-check deltas, the point margin, and the
    enhanced prompt text.
    """
    result = enhance(raw, intent=intent, confidence=confidence)
    cmp = compare_prompts(raw, result["prompt"])
    return {
        "prompt": raw,
        "intent": result["intent"],
        "confidence": round(result["confidence"], 3),
        "before": cmp["a"],
        "after": cmp["b"],
        "deltas": cmp["deltas"],
        "margin": cmp["margin"],
        "enhanced": result["prompt"],
    }


def what_improved(deltas, top=3):
    """The biggest per-check improvements, best first. [(check, delta)]."""
    ups = sorted(((k, v) for k, v in deltas.items() if v > 0),
                 key=lambda kv: -kv[1])
    return ups[:top]
