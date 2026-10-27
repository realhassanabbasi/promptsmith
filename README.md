# 🔨 PromptSmith

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Deps](https://img.shields.io/badge/dependencies-zero-blue?style=flat-square)
![Tests](https://img.shields.io/badge/tests-166%20passing-brightgreen?style=flat-square)
[![Live demo](https://img.shields.io/badge/demo-live%20in%20browser-black?style=flat-square)](https://realhassanabbasi.github.io/promptsmith/)

**Turn rough prompts into engineered ones.** Paste in *"help me with python"*, get back a structured prompt with a role, context slots, requirements, output format, and guardrails — scored before and after. Works **offline**, with **zero dependencies**.

## Try it in your browser

**[Live interactive demo →](https://realhassanabbasi.github.io/promptsmith/)** — the full engine (score, enhance, compare, intent classifier) running in the page. No install, no server.

## Why

Small vague prompts get small vague answers. PromptSmith applies the checklist every prompt-engineering guide agrees on — clarity, context, specificity, output format, guardrails — automatically. It even detects what you're trying to do with a Naive Bayes classifier written from scratch (no sklearn), so the enhancement fits the task.

## Features

- **`init`** — start a PromptSmith project folder in one command: creates `.promptsmith/`, seeds the library with two worked demo prompts (real scorer output, 37 weak → 92 excellent), and drops a `PROMPTS.md` quickstart cheatsheet — new users get a working project, not a blank screen (`--bare` for an empty folder, `--json` for scripts)
- **`improve`** — the one-step loop: score, enhance, and re-score a prompt in one command — before/after table with per-check deltas, what improved, `--log`, `--save`, `--json`
- **`enhance`** — rewrite any rough prompt into a structured, engineered one (+40–55 points on average)
- **`score`** — grade a prompt 0–100 on 5 checks, with concrete fix-it feedback (`--json` for scripts)
- **`batch`** — score every prompt in a file (one per line): averages, weakest prompt, optional `--enhance` that writes `FILE.enhanced.md`
- **`compare`** — put two prompt versions head-to-head: scores, per-check deltas, a winner verdict, and what the loser should fix first (`--json` for scripts)
- **`diff`** — show exactly what changed, word by word: `diff A.txt B.txt` on its own, or `--diff` on `enhance` and `compare` so a score gain is backed by visible edits (`--json` for scripts)
- **`history`** — log scored runs (`score`/`compare --log`) and print per-prompt trend reports (`report`): runs, averages, sparklines, and an improving/steady/slipping verdict (`--json` for dashboards)
- **`stats`** — the whole picture in one glance: total runs and prompts tracked, average/best/worst score, per-intent averages, and library totals (names, versions, best prompt) — `report` shows trends per prompt, `stats` shows the project (`--json` for dashboards)
- **`library`** — save named prompts as versioned library entries (`save NAME "prompt"`; `--improve` saves the enhanced version too): `library` lists each name's versions/last/best, `library NAME` shows its full version history — your best-scoring prompt is always one glance away (`--tags`, `--json`)
- **`check`** — regression guard for your saved library: re-scores every prompt against its recorded best and flags regressions (rubric upgrades can't silently change what your prompts score); `--fail-on-regression` exits 1 for CI, `--json` for dashboards
- **`export`** — share your prompt library: `export` prints it as Markdown (one section per prompt, versions with scores and improved text), `--format json` for machine-readable output, `-o FILE` to write to a file, `export NAME` for a single prompt
- **`import`** — bring a shared library back in: `import FILE` reads a `export --format json` file into your library — scores preserved exactly as exported, duplicates skipped (never doubled), existing names continue their version numbers (`--json` for scripts)
- **`rollback`** — restore any saved version as a new version: `rollback NAME` brings back the previous version, `rollback NAME --to 2` restores version 2 — history is never rewritten, so a rollback is always undoable, and the restored prompt is scored fresh under the current rubric (`--json` for scripts)
- **`search`** — find a saved prompt without remembering its name: `search QUERY` matches names, prompt text, improved text, and tags (case-insensitive), one row per name with versions/last/best and what matched; `--tags a,b` narrows to names carrying a tag (`--json` for scripts)
- **`tokens`** — estimate token count and context-window share for any prompt: `tokens "prompt"` prints ~tokens, words, chars, and % of the model's window used (`--model` to pick the model, `--json` for scripts)
- **`templates`** — 8 fill-in-the-blank templates (debug code, explain concepts, learn vocabulary, study plans…)
- **`interactive`** — guided Q&A that builds your prompt with you
- **`skill`** — generate an installable agent skill (SKILL.md) from the real scoring rubric AND the full score→improve→compare/diff→version loop, so coding agents apply the same workflow themselves
- **From-scratch ML** — intent classifier (Multinomial Naive Bayes) trained on 94 labeled prompts across 8 intents, pure stdlib; shaky guesses fall back to a generic role instead of a confident wrong one
- **Zero dependencies** — only the Python standard library; runs anywhere, even offline

## Quickstart

```bash
# install straight from GitHub (verified clean install, zero dependencies)
pip install git+https://github.com/realhassanabbasi/promptsmith.git

# start a project folder — working demo prompts included
promptsmith init my-prompts && cd my-prompts

# score a prompt
promptsmith score "help me with python"

# enhance it
promptsmith enhance "help me with python"

# or do both in one step — score, enhance, re-score, with proof
promptsmith improve "help me with python" --diff   # also shows the word-level changes

# score a whole list at once (one prompt per line)
promptsmith batch my_prompts.txt
promptsmith batch my_prompts.txt --enhance   # also enhances each, saves my_prompts.txt.enhanced.md

# project totals across history and library
promptsmith stats

# machine-readable output for scripts and pipelines
promptsmith score "help me with python" --json
promptsmith enhance "help me with python" --json

# compare two versions of a prompt (whole file = one prompt)
promptsmith compare prompt_v1.txt prompt_v2.txt

# see exactly what changed, word by word
promptsmith diff prompt_v1.txt prompt_v2.txt
promptsmith enhance "help me with python" --diff   # also on compare via --diff

# track scores over time, then see the trend
promptsmith score "help me with python" --log
promptsmith report

# save your best prompts as versioned library entries
promptsmith save py-help "help me with python" --tags coding,debug
promptsmith library

# guard the library — flag anything that regressed since it was saved
promptsmith check
promptsmith check --fail-on-regression   # for CI: exits 1 on any regression

# share the library — Markdown for docs/teams, JSON for scripts
promptsmith export
promptsmith export -o library.md
promptsmith export --format json

# bring a teammate's shared library back into yours
promptsmith import shared.json
promptsmith import shared.json --json

# a rewrite turned out worse? bring a saved version back as a new version
promptsmith rollback py-help            # previous version becomes the new latest
promptsmith rollback py-help --to 1     # or pick the exact version

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

## Start a project

Real output — a blank folder becomes a working project in one command.
The two seeds are the real scorer's own output, computed at init time:

```
$ promptsmith init my-prompts

PromptSmith project ready: /home/user/my-prompts

  created  .promptsmith/library.jsonl
  created  .promptsmith/history.jsonl
  created  PROMPTS.md

Seed prompts (real scores, from the local scorer):
  demo-rough — 37/100 (weak)
  demo-engineered — 37 → 92/100 (excellent)

Next steps (in this folder):
  promptsmith library demo-engineered   # the worked example
  promptsmith check                     # the regression guard
  promptsmith save my-prompt "..."        # save your own
```

`PROMPTS.md` is a one-page cheatsheet of the loop; `promptsmith init --bare`
creates only `.promptsmith/`; re-running without `--force` refuses instead of
overwriting your library.

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

## Compare mode

Real output — two prompt versions, one question ("did my rewrite help?"):

```
$ promptsmith compare prompt_v1.txt prompt_v2.txt

Compare: prompt_v1.txt  vs  prompt_v2.txt

  A:  37/100 (weak     )  "help me with python"
  B:  94/100 (excellent)  "Write a guide to learning python for beginners.
Give m…"

Verdict: B wins by 57 points.

  check           A    B  delta
  clarity        20   20    +0
  context         3   14   +11
  specificity     5   20   +15
  format          4   20   +16
  guardrails      5   20   +15

Fix A first:
  • Too short to carry context. Add 2-3 sentences of background.
  • Be specific: names, numbers, versions, examples of what 'good' looks like.
  • Say what the answer should look like: bullets, table, code, steps…
  • Add one guardrail: tone, length limit, or 'say when unsure'.
```

`--json` gives the same comparison as machine-readable JSON
(`a`, `b`, `deltas`, `winner`, `margin`) for scripts and pipelines.

## Improve mode

Real output — the most common loop in one command (score → enhance → re-score):

```
$ promptsmith improve "help me with python"

Detected intent: code (confidence 0.38)
Score: 37 (weak) → 92 (excellent)  (+55)

  check        before  after  delta
  clarity          20     12     -8
  context           3     20    +17
  specificity       5     20    +15
  format            4     20    +16
  guardrails        5     20    +15

What improved: context (+17), format (+16), specificity (+15)

— Improved prompt (copy everything below) —

You are a senior software engineer who writes clean, well-commented code.

Task: help me with python

Context: (add 2-3 sentences of background here — who this is for, what you've tried)

Requirements:
- Handle edge cases
- Add brief comments on the tricky parts

Output format: Provide the code first, then a short explanation of how it works.
Guardrails: if you are unsure about something, say so instead of guessing.
```

It's honest about the trade too: the engineered prompt opens with a role
sentence, so `clarity` dips 20→12 while the total climbs 37→92.

Real output — `improve --diff` appends the word changes after the improved
prompt (same block as `enhance --diff`, handy when the margin is small and
you want to see what actually moved):

```
$ promptsmith improve "help me with python" --diff
# score table and improved prompt as above, then:

What changed: 4 → 70 words (+66 / -0)

+ You are a senior software engineer who writes clean, well-commented code.
+ Task:
help me with python
+ Context: (add 2-3 sentences of background here — who this is for, what you've tried)
+ Requirements:
+ - Handle edge cases
+ - Add brief comments on the tricky parts
+ Output format: Provide the code first, then a short explanation of how it works.
+ Guardrails: if you are unsure about something, say so instead of guessing.
```

`--log` records both the before and after runs in the score history
(`promptsmith report` shows them as a two-run trend), `--save FILE` writes
the improved prompt, and `--json` gives the full result
(`prompt`, `intent`, `before`, `after`, `deltas`, `margin`, `enhanced`
— plus a `diff` payload with `--diff`)
for scripts and pipelines.

## Change diff

Scores say a rewrite is better; the diff shows *what* changed.
`diff FILE_A FILE_B` compares two prompts on their own, and `--diff`
adds the word-level changes to `enhance`, `compare`, and `improve`:

```
$ promptsmith diff draft.txt rewrite.txt

Diff: draft.txt  →  rewrite.txt

What changed: 4 → 5 words (+2 / -1)

help me -with- +learn+ python+today+
```

Real output — `enhance --diff` on the classic weak prompt
(enhanced prompt shown in full under Improve mode above):

```
$ promptsmith enhance "help me with python" --diff

What changed: 4 → 70 words (+66 / -0)

+ You are a senior software engineer who writes clean, well-commented code.
+ Task:
help me with python
+ Context: (add 2-3 sentences of background here — who this is for, what you've tried)
+ Requirements:
+ - Handle edge cases
+ - Add brief comments on the tricky parts
+ Output format: Provide the code first, then a short explanation of how it works.
+ Guardrails: if you are unsure about something, say so instead of guessing.
```

The rule of thumb: the changed words should map to the checks that were
weak before the rewrite. If untouched checks also changed, the rewrite added
noise instead of focus.

## Regression check

Scores say a rewrite is better; the diff shows *what* changed; `check`
makes sure your *saved* prompts still score what they used to. It re-scores
each library entry's keeper text with the **current** rubric and compares it
to the best score that prompt ever recorded. The scorer is deterministic, so
a negative delta means the rubric moved — a PromptSmith upgrade made it
stricter (or fairer) — and the regressed prompts deserve a re-pass before
they ship again.

Real output (the stored best of 98 came from an older, looser rubric, so the
current 92 reads as a regression — this is exactly what a rubric upgrade
looks like):

```
$ promptsmith check py-help

Prompt health — 1 checked (re-scored against recorded best)

  name                      ver  now best    Δ  verdict
  py-help                     1   92   98   -6▼  regressed

1 regressed — re-pass them before shipping: improve, verify, re-save.
```

- `check` — health table for the whole library, regressed first
- `check --fail-on-regression` — exits 1 when any prompt scores below its
  recorded best; drop it into CI so a rubric upgrade can't silently change
  what your prompts score
- `check --json` — machine-readable `{results, checked, regressed, steady,
  improved}` for dashboards

## Score history

Real output — log runs with `--log`, then watch trends with `report`:

```
$ promptsmith score "help me with python" --log

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

$ promptsmith report

Score history — 2 runs, 2 prompt(s) tracked

  prompt                                     runs   avg best last    Δ  trend   verdict
  help me with python                           1  37.0   37   37   +0  ▄       baseline —
  Write a Python function that sorts a lis…     1  58.0   58   58   +0  ▄       baseline —
```

Re-score the same prompt over days and the verdict column reads
`improving ▲`, `steady ▬`, or `slipping ▼` with a sparkline — the honest
answer to "are my prompts getting better?" `compare --log` logs both
versions. Records live in `.promptsmith/history.jsonl` (git-ignored), and
`report --json` gives the same table as JSON for dashboards.

## Project stats

Real output — `report` shows trends per prompt; `stats` shows the whole project:

```
$ promptsmith stats

Project stats

  Score history — 2 runs, 2 prompt(s) tracked
    average 47.5   best 58 (Write a Python function that sorts a lis…)   worst 37 (help me with python)
    code: 2 runs, avg 47.5
  Library — 3 name(s), 3 version(s)
    best 92 (demo-engineered)
```

`score --log` and `compare --log` now record each run's intent, so the
per-intent lines only cover runs logged with this version — older records
(with no intent stored) are counted in the totals but not in any intent row.
`stats --json` gives the same totals as JSON for dashboards.

## Prompt library

Real output — save prompts by name; re-saving adds a version:

```
$ promptsmith save py-help "help me with python" --tags coding,debug

Saved: py-help v1 — 37/100 (weak)
Tags: coding, debug
Library: /home/user/project/.promptsmith/library.jsonl

$ promptsmith save py-help --improve "write a python function that sorts a list"

Saved: py-help v2 — 92/100 (excellent)
Improved version saved too: 53/100 → 92/100.
  "You are a senior software engineer who writes clean, well-commented code. …"
Library: /home/user/project/.promptsmith/library.jsonl

$ promptsmith library

Prompt library — 2 version(s), 1 prompt(s) saved

  name                      ver last best    Δ  tags
  py-help                     2   92   92  +55▲  coding, debug

$ promptsmith library py-help

py-help — 2 version(s)

  ver score grade     saved
  v1   37/100 (weak    ) 2026-10-16
       "help me with python"
  v2   92/100 (excellent) 2026-10-16
       "write a python function that sorts a list"
       → improved: "You are a senior software engineer who writes clean, well-commen…"
```

The library answers "which version of my prompt is the best?" — `library`
lists every name's last/best score and the Δ since the first save, `library NAME`
shows the full version history. Records live in `.promptsmith/library.jsonl`
(git-ignored, same folder as score history), and `--json` gives the same data
for scripts. `--improve` saves both the original and its enhanced rewrite,
with the before→after proof stored on the record.

## Export

Real output — share the library as Markdown or JSON:

```
$ promptsmith export

# Prompt Library

_Exported 2026-10-22 with promptsmith._

## email-writer (2 version(s), best 92/100)

### v1 — 37/100 (weak) — 2026-10-22

> write a good email

### v2 — 92/100 (excellent) — 2026-10-22

> write a professional business email

**Improved version:**

> You are a professional writer with a clear, natural voice. …

$ promptsmith export --format json | head -12
{
  "exported": "2026-10-22T17:31:23+00:00",
  "tool": "promptsmith",
  "prompts": [
    {
      "name": "email-writer",
      "versions": 2,
      "best": 92,
```

`export NAME` exports one prompt, `-o FILE` writes to a file instead of
stdout. The Markdown is ready to paste into docs or share with a team;
the JSON has the full version history for scripts and backups.

## Import

Real output — the round trip: a teammate exports, you import, nothing
gets doubled:

```
$ promptsmith import shared.json
Imported 1 prompt version(s) into: py-help (0 skipped as duplicates).

$ promptsmith import shared.json
Nothing new to import (1 skipped as duplicates).

$ promptsmith library

Prompt library — 1 version(s), 1 prompt(s) saved

  name                      ver last best    Δ  tags
  py-help                     1   37   37   +0▬  —
```

Import keeps the exported scores exactly (the point of sharing is proven
prompts, not re-scoring them), continues version numbers for names you
already have, and refuses anything that is not a promptsmith export —
no half-imports, no silent overwrites.

## Rollback

Real output — the mechanism, shown on a two-version library: the
previous version comes back as a new version, history untouched. (In
real use you roll back when a rewrite turns out worse than the version
it replaced — here v2 happens to score higher, so this demo shows the
mechanism, not a rescue.)

```
$ promptsmith library py-help

py-help — 2 version(s)

  ver score grade     saved
  v1   37/100 (weak    ) 2026-10-26
       "help me with python"
  v2   45/100 (weak    ) 2026-10-26
       "help me with python 3 and pip"

$ promptsmith rollback py-help

Rolled back: py-help v1 → v3 — 37/100 (weak)
  "help me with python"
Library: /tmp/rb-demo/.promptsmith/library.jsonl
```

`rollback NAME --to N` restores exactly version N; rolling back to
the version you are already on, or to a version that does not exist, is
refused instead of silently duplicating. The restored version keeps the
original's tags and is scored fresh under the current rubric, so a
rollback after a rubric upgrade tells you what the old prompt scores now.

## Search

Real output — the library grows, and names get forgotten. Search finds the
prompt by any word in it:

```
$ promptsmith search python

Search results — 1 match(es) for "python"

  name                      ver last best  matched   tags
  py-help                     2   92   92  prompt, improved  coding, debug

$ promptsmith search python --tags debug --json
{
  "query": "python",
  "tags": ["debug"],
  "results": [
    {
      "name": "py-help",
      "versions": 2,
      "last": 92,
      "best": 92,
      "delta": 55,
      "tags": ["coding", "debug"],
      "matched": ["prompt", "improved"]
    }
  ]
}
```

One row per matching name, best score first (same order as `library`).
`matched` says where the word hit: `name`, `prompt`, `improved`, or `tag`.
No match gets an honest one-liner, not an empty table — and an empty query
lists everything, so `search ""` doubles as a quick library scan.

## Agent skill export

Coding agents (Claude Code, Codex, Cursor) can use PromptSmith's rubric
directly — no CLI calls needed:

```bash
# print the skill, or write it to a skills folder:
promptsmith skill
promptsmith skill --out ~/.claude/skills
```

This writes `~/.claude/skills/promptsmith/SKILL.md`: the 5-check rubric
(clarity, context, specificity, format, guardrails — 20 points each), all 8
intent roles with their formats, **the improvement loop** (score → rebuild →
prove the margin → keep versions → track trends, with the CLI commands each
step maps to), and a real worked example. The skill is generated from the
actual code — the example is produced by a real `improve()` call at render
time — so it always matches the current version, nothing to keep in sync by
hand.

Real `promptsmith skill` output (excerpt):

```markdown
## Worked example (real output)

Rough prompt: "help me write an essay about climate change"

Scored 37/100 (weak) → improved 92/100 (excellent), margin +55 points,
intent `write` (confidence 0.69).

Biggest gains: context +17, format +16, specificity +15.
```

## Demo

![PromptSmith terminal demo](assets/demo.svg)

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

Detected intent: code (confidence 0.38)
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
                        +--------+---------+    templates / interactive /
                                 |                skill / compare / diff / report /
                                                  stats / improve / save / library /
                                                  rollback / search / tokens / cost /
                                                  check / export / import / init
            +--------------------+--------------------+
            |                    |                    |
     +------v------+      +------v------+      +------v------+
     | classifier  |      |   scorer    |      |  enhancer   |
     | Naive Bayes |      | 5-check     |      | intent ->   |
     | from scratch|      | rubric 0-100|      | role, reqs, |
     +------+------+      +------+------+      | format,     |
            |                    |             | guardrails  |
   training_prompts.json         |             +------+------+
   (94 labeled prompts,          +----> before/after scores -+
    8 intents)              compare reuses the scorer for A vs B
```

Design decisions, stated plainly:

- **From-scratch Naive Bayes instead of sklearn** — the math is ~60 lines and fully auditable, and it keeps the tool at zero dependencies. For 8 intents and 94 examples, a hand-rolled classifier is the right-sized tool, not a shortcut.
- **Low-confidence fallback instead of confident wrong guesses** — when intent confidence drops below 0.35, the enhancer uses the generic `chat` role rather than the top guess. A wrong role and format actively harms the output; an honest generic one doesn't.
- **Zero dependencies as a hard constraint** — the audience is students on free tiers. `pip install` should never pull a dependency tree, and the tool must run offline.
- **Rule-based scorer, not an LLM judge** — deterministic, instant, explainable. The point is teaching prompt craft, so the feedback must be inspectable. The honest cost of this choice is in Limitations below.
- **Enhancement by gap-filling, not rewriting** — the enhancer wraps *your* task text with a role, requirements, format and guardrails instead of replacing your intent. Your words stay yours.

## Limitations

Honest ones, verified against the code:

- **English only.** The tokenizer keeps `[a-z]+` and every scoring keyword list is English. Non-English prompts will score badly and misclassify — that's the tool's boundary, not yours.
- **Tiny training set.** 94 labeled prompts across 8 intents (10–16 per intent). Holdout accuracy (last example per intent, retrained) is 6/8 — both misses were low-confidence guesses, exactly the case the 0.35 fallback now catches by using the generic `chat` role. Unusual prompts will still misclassify; that's the tool's boundary, not yours.
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
│   ├── cli.py             # argparse CLI (score/enhance/batch/templates/interactive/skill/compare/diff/report/stats/improve/save/library/rollback/search/tokens/cost/check/export/init/import)
│   ├── check.py           # `promptsmith check` — re-score the library, flag regressions
│   ├── cost.py            # `promptsmith cost` — offline API cost estimates (11-model price snapshot)
│   ├── diff.py            # `promptsmith diff` + `--diff` — word-level change diffs, stdlib difflib
│   ├── export.py          # `promptsmith export` — library to Markdown/JSON
│   ├── init.py            # `promptsmith init` — project folder with demo seeds + PROMPTS.md cheatsheet
│   ├── importing.py       # `promptsmith import` — shared JSON export back into the library (scores kept, duplicates skipped)
│   ├── tokens.py          # offline token estimation + context-window share
│   ├── classifier.py      # Naive Bayes intent classifier, from scratch (+0.35 fallback)
│   ├── compare.py         # `promptsmith compare` — head-to-head, per-check deltas
│   ├── enhancer.py        # enhancement pipeline (role → structure → guardrails)
│   ├── history.py         # `score/compare --log` + `promptsmith report` — score history & trends
│   ├── improve.py         # `promptsmith improve` — score, enhance, re-score in one step
│   ├── library.py         # `promptsmith save` + `promptsmith library` — versioned prompt library
│   ├── rollback.py        # `promptsmith rollback` — restore any saved version as a new version
│   ├── search.py          # `promptsmith search` — find saved prompts by word or tag
│   ├── scorer.py          # 5-check rubric, 0-100
│   ├── skills.py          # `promptsmith skill` — renders an installable agent skill (rubric + improvement loop)
│   ├── stats.py           # `promptsmith stats` — project totals across history + library
│   ├── templates.py       # 8 ready-made templates
│   └── data/
│       └── training_prompts.json  # labeled set (94 prompts, 8 intents)
├── tests/
│   └── test_promptsmith.py  # 166 unit tests (scorer, classifier, enhancer, CLI, batch, packaging, skill, compare, diff, history, improve, library, tokens, cost, check, export, init, import, stats, rollback, search)
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
