"""The enhancer: turns a rough prompt into an engineered one.

Pipeline: detect intent -> score the draft -> fill the gaps
(role, structure, format, guardrails) -> rebuild the prompt.
"""

from . import scorer

ROLES = {
    "code": "You are a senior software engineer who writes clean, well-commented code.",
    "debug": "You are a patient debugging expert. Diagnose first, then fix.",
    "explain": "You are a teacher who explains hard ideas with simple words and everyday examples.",
    "write": "You are a professional writer with a clear, natural voice.",
    "analyze": "You are a sharp analyst. Be honest about what the data does and doesn't show.",
    "plan": "You are a practical planner. Keep it realistic and step by step.",
    "learn": "You are a friendly tutor. Teach the key terms first, then build up with examples.",
    "chat": "You are a helpful assistant.",
}

FORMATS = {
    "code": "Provide the code first, then a short explanation of how it works.",
    "debug": "Give: 1) likely cause, 2) how to confirm it, 3) the fix.",
    "explain": "Use short paragraphs, one everyday example, and end with a one-line recap.",
    "write": "Match the tone I asked for. Keep paragraphs short.",
    "analyze": "Use bullet points for findings and end with a clear recommendation.",
    "plan": "Present as numbered steps with rough time estimates.",
    "learn": "For each term: definition in plain words, then a real-life example.",
    "chat": "Answer directly and concisely.",
}

REQUIREMENTS = {
    "code": "- Handle edge cases\n- Add brief comments on the tricky parts",
    "debug": "- Ask for the exact error message if I didn't include it",
    "explain": "- Avoid jargon; when a technical word is needed, define it",
    "write": "- No filler phrases or purple prose",
    "analyze": "- Separate facts from your interpretation",
    "plan": "- Flag anything that depends on someone else or costs money",
    "learn": "- Order terms from basic to advanced",
    "chat": "",
}


def enhance(raw, intent=None, confidence=None):
    """Returns dict with the enhanced prompt, intent, scores before/after."""
    from .classifier import load_default

    raw = raw.strip()
    if intent is None:
        clf = load_default()
        intent, confidence = clf.predict(raw)

    before, _, _ = scorer.score_prompt(raw)
    role = ROLES.get(intent, ROLES["chat"])
    fmt = FORMATS.get(intent, FORMATS["chat"])
    reqs = REQUIREMENTS.get(intent, "")

    parts = [role, "", f"Task: {raw}", ""]
    parts.append("Context: (add 2-3 sentences of background here — who this is for, what you've tried)")
    parts.append("")
    if reqs:
        parts.append("Requirements:")
        parts.append(reqs)
        parts.append("")
    parts.append(f"Output format: {fmt}")
    parts.append("Guardrails: if you are unsure about something, say so instead of guessing.")
    enhanced = "\n".join(parts)

    after, _, _ = scorer.score_prompt(enhanced)
    return {
        "intent": intent,
        "confidence": confidence,
        "before": before,
        "after": after,
        "gain": after - before,
        "prompt": enhanced,
    }
