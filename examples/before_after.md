# Before / After examples

Real outputs from `python -m promptsmith enhance`. Scores by the built-in rubric.

---

## 1. "help me with python" → score 37 → 92

**Before:** `help me with python`

**After:**
```
You are a senior software engineer who writes clean, well-commented code.

Task: help me with python

Context: (add 2-3 sentences of background here — who this is for, what you've tried)

Requirements:
- Handle edge cases
- Add brief comments on the tricky parts

Output format: Provide the code first, then a short explanation of how it works.
Guardrails: if you are unsure about something, say so instead of guessing.
```

---

## 2. "write email to professor" → score 37 → 92

**Before:** `write email to professor`

**After:**
```
You are a professional writer with a clear, natural voice.

Task: write email to professor

Context: (add 2-3 sentences of background here — who this is for, what you've tried)

Requirements:
- No filler phrases or purple prose

Output format: Match the tone I asked for. Keep paragraphs short.
Guardrails: if you are unsure about something, say so instead of guessing.
```

---

## 3. "explain blockchain" → score 37 → 92

**Before:** `explain blockchain`

**After:**
```
You are a teacher who explains hard ideas with simple words and everyday examples.

Task: explain blockchain

Context: (add 2-3 sentences of background here — who this is for, what you've tried)

Requirements:
- Avoid jargon; when a technical word is needed, define it

Output format: Use short paragraphs, one everyday example, and end with a one-line recap.
Guardrails: if you are unsure about something, say so instead of guessing.
```

---

## Try it

```bash
python -m promptsmith score "your prompt here"
python -m promptsmith enhance "your prompt here"
python -m promptsmith interactive
```
