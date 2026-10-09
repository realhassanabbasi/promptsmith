# 🔨 PromptSmith

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Deps](https://img.shields.io/badge/dependencies-zero-blue?style=flat-square)
![Tests](https://img.shields.io/badge/tests-19%20passing-brightgreen?style=flat-square)

**Turn rough prompts into engineered ones.** Paste in *"help me with python"*, get back a structured prompt with a role, context slots, requirements, output format, and guardrails — scored before and after. Works **offline**, with **zero dependencies**.

## Why

Small vague prompts get small vague answers. PromptSmith applies the checklist every prompt-engineering guide agrees on — clarity, context, specificity, output format, guardrails — automatically. It even detects what you're trying to do with a Naive Bayes classifier written from scratch (no sklearn), so the enhancement fits the task.

## Features

- **`enhance`** — rewrite any rough prompt into a structured, engineered one (+40–55 points on average)
- **`score`** — grade a prompt 0–100 on 5 checks, with concrete fix-it feedback (`--json` for scripts)
- **`batch`** — score every prompt in a file (one per line): averages, weakest prompt, optional `--enhance` that writes `FILE.enhanced.md`
- **`templates`** — 8 fill-in-the-blank templates (debug code, explain concepts, learn vocabulary, study plans…)
- **`interactive`** — guided Q&A that builds your prompt with you
- **From-scratch ML** — intent classifier (Multinomial Naive Bayes) trained on a built-in labeled set, pure stdlib
- **Zero dependencies** — only the Python standard library; runs anywhere, even offline

## Quickstart

```bash
# install straight from GitHub (verified clean install, zero dependencies)
pip install git+https://github.com/realhassanabbasi/promptsmith.git

# score a prompt
promptsmith score "help me with python"

# enhance it
promptsmith enhance "help me with python"

# score a whole list at once (one prompt per line)
promptsmith batch my_prompts.txt
promptsmith batch my_prompts.txt --enhance   # also enhances each, saves my_prompts.txt.enhanced.md

# machine-readable output for scripts and pipelines
promptsmith score "help me with python" --json
promptsmith enhance "help me with python" --json

# guided mode
promptsmith interactive
```

Or run without installing:

```bash
git clone https://github.com/realhassanabbasi/promptsmith.git
cd promptsmith
python -m promptsmith score "help me with python"   # python -m promptsmith works too
```

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

Python 3.9+ and you're good. A CI workflow for 3.10 / 3.11 / 3.12 ships with the
repo the moment it's added under `.github/workflows/` (see `.github/workflows/ci.yml`
in the source tree — GitHub Apps can't push workflow files, so this one goes in
by hand).

## Batch mode

Real output — a file with one prompt per line:

```
$ promptsmith batch my_prompts.txt

Scored 3 prompts from my_prompts.txt

   1.  37/100 (weak    ) help me with python
   2.  94/100 (excellent) Write a cover letter for a data science internship. …
   3.  61/100 (okay    ) explain recursion with an example

Average: 64.0/100
Weakest: "help me with python" (37/100)
```

`--enhance` also rewrites every prompt, reports the average gain, and saves all
enhanced prompts to `my_prompts.txt.enhanced.md`. `--json` on `score`, `enhance`
or `batch` prints machine-readable JSON for scripts and pipelines.

## Demo

Real output, copied from the terminal — no mockups:

```
$ promptsmith score "help me with python"

Prompt score: 37/100 (weak)

  clarity      ██████████  20/20
  context      █░░░░░░░░░   3/20
  specificity  ██░░░░░░░░   5/20
  format       ██░░░░░░░░   4/20
  guardrails   ██░░░░░░░░   5/20

How to improve:
  • Too short to carry context. Add 2-3 sentences of background.
  • Be specific: names, numbers, versions, examples of what 'good' looks like.
  • Say what the answer should look like: bullets, table, code, steps…
  • Add one guardrail: tone, length limit, or 'say when unsure'.
```

```
$ promptsmith enhance "help me with python"

Detected intent: code (confidence 0.34)
Score: 37 → 92  (+55)

— Enhanced prompt (copy everything below) —

You are a senior software engineer who writes clean, well-commented code.

Task: help me with python

Context: (add 2-3 sentences of background here — who this is for, what you've tried)

Requirements:
- Handle edge cases
- Add brief comments on the tricky parts

Output format: Provide the code first, then a short explanation of how it works.
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

## Architecture

```
                        +------------------+
                        |      cli.py      |  argparse: score / enhance / batch /
                        +--------+---------+           templates / interactive
                                 |
            +--------------------+--------------------+
            |                    |                    |
     +------v------+      +------v------+      +------v------+
     | classifier  |      |   scorer    |      |  enhancer   |
     | Naive Bayes |      | 5-check     |      | intent ->   |
     | from scratch|      | rubric 0-100|      | role, reqs, |
     +------+------+      +------+------+      | format,     |
            |                    |             | guardrails  |
   training_prompts.json         |             +------+------+
   (70 labeled prompts,          +----> before/after scores -+
    7 intents x 10)                             (self-check)
```

Design decisions, stated plainly:

- **From-scratch Naive Bayes instead of sklearn** — the math is ~60 lines and fully auditable, and it keeps the tool at zero dependencies. For 7 intents and 70 examples, a hand-rolled classifier is the right-sized tool, not a shortcut.
- **Zero dependencies as a hard constraint** — the audience is students on free tiers. `pip install` should never pull a dependency tree, and the tool must run offline.
- **Rule-based scorer, not an LLM judge** — deterministic, instant, explainable. The point is teaching prompt craft, so the feedback must be inspectable. The honest cost of this choice is in Limitations below.
- **Enhancement by gap-filling, not rewriting** — the enhancer wraps *your* task text with a role, requirements, format and guardrails instead of replacing your intent. Your words stay yours.

## Limitations

Honest ones, verified against the code:

- **English only.** The tokenizer keeps `[a-z]+` and every scoring keyword list is English. Non-English prompts will score badly and misclassify — that's the tool's boundary, not yours.
- **Tiny training set.** 70 labeled prompts (10 per intent, 7 intents). Confidence numbers like `0.34` are honest but shaky; unusual prompts will be misclassified. (The enhancer's 8th `chat` role is a fallback default — the classifier only ever predicts the 7 trained intents.)
- **Scores are heuristic, not measured.** The rubric is a hand-written checklist. The "37 → 92" gain is computed by the *same* scorer that shaped the enhancement — self-reported progress, not an independent measurement of answer quality.
- **No model calls, ever.** PromptSmith never talks to an LLM, so it can't verify that an enhanced prompt actually gets better answers. That final check is yours.
- **Terminal needed for two modes.** `interactive` and `templates --show` read from `input()` — they need a real terminal, not a pipe.

## Project structure

```
promptsmith/
├── .github/
│   └── workflows/
│       └── ci.yml           # tests on Python 3.10 / 3.11 / 3.12
│                            # (add by hand — GitHub Apps can't push workflow files)
├── promptsmith/
│   ├── __init__.py        # public API
│   ├── __main__.py        # `python -m promptsmith`
│   ├── cli.py             # argparse CLI (score/enhance/templates/interactive)
│   ├── classifier.py      # Naive Bayes intent classifier, from scratch
│   ├── enhancer.py        # enhancement pipeline (role → structure → guardrails)
│   ├── scorer.py          # 5-check rubric, 0-100
│   ├── templates.py       # 8 ready-made templates
│   └── data/
│       └── training_prompts.json  # labeled set (70 prompts, 7 intents)
├── tests/
│   └── test_promptsmith.py  # 19 unit tests (scorer, classifier, enhancer, CLI, batch)
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
