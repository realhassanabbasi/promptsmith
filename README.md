# 🔨 PromptSmith

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Deps](https://img.shields.io/badge/dependencies-zero-blue?style=flat-square)
![Tests](https://img.shields.io/badge/tests-15%20passing-brightgreen?style=flat-square)

**Turn rough prompts into engineered ones.** Paste in *"help me with python"*, get back a structured prompt with a role, context slots, requirements, output format, and guardrails — scored before and after. Works **offline**, with **zero dependencies**.

## Why

Small vague prompts get small vague answers. PromptSmith applies the checklist every prompt-engineering guide agrees on — clarity, context, specificity, output format, guardrails — automatically. It even detects what you're trying to do with a Naive Bayes classifier written from scratch (no sklearn), so the enhancement fits the task.

## Features

- **`enhance`** — rewrite any rough prompt into a structured, engineered one (+40–55 points on average)
- **`score`** — grade a prompt 0–100 on 5 checks, with concrete fix-it feedback
- **`templates`** — 8 fill-in-the-blank templates (debug code, explain concepts, learn vocabulary, study plans…)
- **`interactive`** — guided Q&A that builds your prompt with you
- **From-scratch ML** — intent classifier (Multinomial Naive Bayes) trained on a built-in labeled set, pure stdlib
- **Zero dependencies** — only the Python standard library; runs anywhere, even offline

## Quickstart

```bash
git clone https://github.com/realhassanabbasi/promptsmith.git
cd promptsmith

# score a prompt
python -m promptsmith score "help me with python"

# enhance it
python -m promptsmith enhance "help me with python"

# guided mode
python -m promptsmith interactive

# run the test suite
python -m unittest discover -s tests -v
```

No install step needed. Python 3.9+ and you're good.

## Example

```
$ python -m promptsmith enhance "write email to professor"

Detected intent: write (confidence 0.77)
Score: 37 → 92  (+55)

— Enhanced prompt (copy everything below) —

You are a professional writer with a clear, natural voice.

Task: write email to professor

Context: (add 2-3 sentences of background here — who this is for, what you've tried)

Requirements:
- No filler phrases or purple prose

Output format: Match the tone I asked for. Keep paragraphs short.
Guardrails: if you are unsure about something, say so instead of guessing.
```

More pairs in [`examples/before_after.md`](examples/before_after.md).

## How the scoring works

| Check (20 pts each) | What it looks for |
|---|---|
| Clarity | Opens with a clear action verb (write, explain, analyze…) |
| Context | Enough background — who, what, what you've tried |
| Specificity | Concrete details: names, numbers, versions |
| Format | Says what the answer should look like (bullets, table, code…) |
| Guardrails | Tone, length limits, "say when unsure" |

## Project structure

```
promptsmith/
├── promptsmith/
│   ├── __init__.py        # public API
│   ├── __main__.py        # `python -m promptsmith`
│   ├── cli.py             # argparse CLI (score/enhance/templates/interactive)
│   ├── classifier.py      # Naive Bayes intent classifier, from scratch
│   ├── enhancer.py        # enhancement pipeline (role → structure → guardrails)
│   ├── scorer.py          # 5-check rubric, 0-100
│   ├── templates.py       # 8 ready-made templates
│   └── data/
│       └── training_prompts.json  # labeled set for the classifier
├── tests/
│   └── test_promptsmith.py  # 15 unit tests
├── examples/
│   └── before_after.md    # real before/after pairs
├── demo.py                # end-to-end demo, no args needed
├── pyproject.toml
└── LICENSE                # MIT
```

## Tech stack

Python 3.9+ · standard library only · unittest

## Author

**Hassan Abbasi** — AI Engineer. I build AI-powered products with excellent user experiences.
