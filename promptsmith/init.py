"""Project init — start a PromptSmith project folder in one command.

`promptsmith init [DIR]` creates `.promptsmith/` (score history + prompt
library) in DIR, seeds the library with two worked demo prompts, and drops a
`PROMPTS.md` quickstart cheatsheet. Everything the seeds claim is real output
of the scorer/enhancer — they are computed at init time, never hardcoded.
"""

import os

from .history import HISTORY_FILE
from .library import LIBRARY_DIR, LIBRARY_FILE, entries_for, save_entry

CHEATSHEET_NAME = "PROMPTS.md"

# (name, prompt, tags, enhance_it) — scores are computed live by save_entry.
SEED_PROMPTS = [
    (
        "demo-rough",
        "help me with python",
        ["demo", "starter"],
        False,
    ),
    (
        "demo-engineered",
        "help me write an essay about climate change",
        ["demo", "starter"],
        True,
    ),
]


def cheatsheet():
    """The one-page quickstart written into every initialized project."""
    return """# PromptSmith project

This folder is a PromptSmith project: scores and prompts live in
`.promptsmith/`, so every prompt here gets the full improvement loop.

## The loop

1. **Score** — `promptsmith score "..."` — the 5 checks are your repair plan.
2. **Improve** — `promptsmith improve "..." --diff` — rebuild in one pass,
   prove the margin, see what changed word by word.
3. **Compare** — `promptsmith compare A.txt B.txt` — head-to-head, winner verdict.
4. **Keep** — `promptsmith save NAME "..."` — named prompts with version history.
5. **Track** — `promptsmith report` — trends and sparklines over time.
6. **Guard** — `promptsmith check --fail-on-regression` — CI-ready regression guard.
7. **Share** — `promptsmith export -o prompts.md` — Markdown or JSON of the library.

Tokens and cost before shipping: `promptsmith tokens "..."` and
`promptsmith cost "..." --calls 1000`.

## Try it now

The library already holds two demo prompts — run these in this folder:

    promptsmith library demo-rough
    promptsmith library demo-engineered
    promptsmith check

Then save your own: `promptsmith save NAME "your prompt" --improve`.

## Honest notes

- The seed scores were computed by the local scorer at init time — no mockups.
- `.promptsmith/` is plain JSONL; delete or edit it freely.
- Scoring is a heuristic rubric, not a quality guarantee. Use the loop,
  not a single number.
"""


def init_project(target=".", bare=False, force=False):
    """Initialize DIR as a PromptSmith project.

    Creates the dir (if missing), `.promptsmith/` inside it, two seeded
    library entries, and a PROMPTS.md cheatsheet (unless bare).

    Returns a payload dict with status "created", "topped-up" (already a
    project — only missing pieces were added), or "already" (a full
    project exists and --force was not passed; nothing touched).
    """
    target = os.path.abspath(target)
    if not os.path.isdir(target):
        os.makedirs(target)

    psdir = os.path.join(target, LIBRARY_DIR)
    existed = os.path.isdir(psdir)
    lib_file = os.path.join(psdir, LIBRARY_FILE)
    hist_file = os.path.join(psdir, HISTORY_FILE)
    sheet_file = os.path.join(target, CHEATSHEET_NAME)

    already_full = (
        os.path.isfile(lib_file)
        and os.path.isfile(hist_file)
        and os.path.isfile(sheet_file)
    )
    if already_full and not force:
        return {
            "status": "already",
            "target": target,
            "files": [],
            "seeds": [],
            "message": (
                f"{target} is already a PromptSmith project — "
                "run with --force to top up missing pieces."
            ),
        }

    os.makedirs(psdir, exist_ok=True)
    files = []
    seeds = []
    if not bare:
        for name, prompt, tags, enhance_it in SEED_PROMPTS:
            if entries_for(name, cwd=target):
                continue  # idempotent: never duplicate a seed
            record = save_entry(name, prompt, tags=tags,
                                enhance_it=enhance_it, cwd=target)
            seeds.append(record)
        if os.path.isfile(lib_file):
            files.append(os.path.join(LIBRARY_DIR, LIBRARY_FILE))
        # an empty history file makes `report`/`check` messaging clean
        if not os.path.isfile(hist_file):
            with open(hist_file, "w", encoding="utf-8"):
                pass
        files.append(os.path.join(LIBRARY_DIR, HISTORY_FILE))
        if not os.path.isfile(sheet_file) or force:
            with open(sheet_file, "w", encoding="utf-8") as f:
                f.write(cheatsheet())
            files.append(CHEATSHEET_NAME)

    return {
        "status": "topped-up" if existed else "created",
        "target": target,
        "files": files,
        "seeds": seeds,
        "message": None,
    }
