"""Prompt scoring: 5 checks, 20 points each, plain feedback.

Not magic — a checklist of what prompt-engineering guides agree on:
clarity, context, specificity, output format, guardrails.
"""

import re

ACTION_WORDS = {
    "write", "explain", "analyze", "compare", "summarize", "create", "make",
    "generate", "draft", "list", "describe", "teach", "show", "help", "plan",
    "review", "fix", "debug", "convert", "design", "suggest", "recommend",
}

FORMAT_HINTS = {
    "bullet", "bullets", "table", "list", "code", "json", "paragraph",
    "step-by-step", "steps", "example", "examples", "summary", "outline",
}

GUARDRAIL_HINTS = {
    "don't", "do not", "avoid", "instead of", "if unsure", "say so",
    "no more than", "at most", "keep it", "simple", "beginner",
}


def _has(words, text):
    t = text.lower()
    return sum(1 for w in words if w in t)


def score_prompt(text):
    """Returns (total 0-100, breakdown dict, feedback list)."""
    text = text.strip()
    words = text.split()
    n = len(words)
    breakdown, feedback = {}, []

    # 1. clarity — does it open with a clear action?
    first = words[0].lower().strip(".,!?") if words else ""
    if first in ACTION_WORDS:
        s = 20
    elif _has(ACTION_WORDS, text) >= 1:
        s = 12
        feedback.append("Put the action verb first ('Write…', 'Explain…') instead of burying it.")
    else:
        s = 4
        feedback.append("No clear action. Start with what you want: write, explain, analyze…")
    breakdown["clarity"] = s

    # 2. context — is there background for the model to work with?
    if n >= 40:
        s = 20
    elif n >= 20:
        s = 14
    elif n >= 10:
        s = 8
        feedback.append("Add background: who it's for, what it's about, what you already tried.")
    else:
        s = 3
        feedback.append("Too short to carry context. Add 2-3 sentences of background.")
    breakdown["context"] = s

    # 3. specificity — concrete details, numbers, names
    concrete = len(re.findall(r"\b\d+\b", text)) + _has({"for", "about", "using", "with", "in"}, text)
    if concrete >= 4:
        s = 20
    elif concrete >= 2:
        s = 13
    else:
        s = 5
        feedback.append("Be specific: names, numbers, versions, examples of what 'good' looks like.")
    breakdown["specificity"] = s

    # 4. output format — did you say what the answer should look like?
    if _has(FORMAT_HINTS, text) >= 1:
        s = 20
    else:
        s = 4
        feedback.append("Say what the answer should look like: bullets, table, code, steps…")
    breakdown["format"] = s

    # 5. guardrails — tone, scope, honesty rules
    if _has(GUARDRAIL_HINTS, text) >= 1:
        s = 20
    else:
        s = 5
        feedback.append("Add one guardrail: tone, length limit, or 'say when unsure'.")
    breakdown["guardrails"] = s

    return sum(breakdown.values()), breakdown, feedback


def grade(total):
    if total >= 85:
        return "excellent"
    if total >= 70:
        return "good"
    if total >= 50:
        return "okay"
    return "weak"
