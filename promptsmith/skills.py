"""Agent skill export: package PromptSmith's rubric AND its improvement loop.

Agent skills (Claude Code, Codex, Cursor) are small SKILL.md instruction
packs. This module renders one from PromptSmith's REAL scoring, comparison
and enhancement pipeline — nothing invented, nothing hardcoded twice.
"""

import os

from . import scorer
from .enhancer import FORMATS, REQUIREMENTS, ROLES
from .improve import improve_prompt, what_improved

SKILL_NAME = "promptsmith"

# The worked example is produced by the real improve() pipeline at render
# time, so the skill always shows genuine output, never a mockup.
EXAMPLE_ROUGH = "help me write an essay about climate change"


def _checks_section():
    return (
        "## The 5 checks (20 points each, 100 total)\n\n"
        "Score any prompt with these before writing the final version:\n\n"
        "1. **Clarity** — does the prompt open with a clear action verb? "
        "(`write`, `explain`, `analyze`, `compare`, `summarize`, `create`, "
        "`generate`, `draft`, `list`, `describe`, `teach`, `debug`, `design`…). "
        "Verb first = full marks; verb buried = partial; no action = near zero.\n\n"
        "2. **Context** — is there background for the model to work with? "
        "Roughly: 40+ words full marks, 20+ strong, 10+ partial, under 10 "
        "means 'add 2–3 sentences of background: who it's for, what you tried'.\n\n"
        "3. **Specificity** — concrete details: numbers, names, versions, "
        "and connector words (`for`, `about`, `using`, `with`, `in`) that "
        "tie the task to something real.\n\n"
        "4. **Output format** — state what the answer should look like: "
        "`bullets`, `table`, `list`, `code`, `json`, `steps`, `examples`, "
        "`summary`, `outline`. No format hint = near zero.\n\n"
        "5. **Guardrails** — at least one: tone, length limit, or an honesty "
        "rule like 'if unsure, say so instead of guessing'.\n\n"
        "Grades: 85+ excellent · 70+ good · 50+ okay · below 50 weak.\n"
    )


def _roles_section():
    lines = ["## Intent roles", "", "Pick the role that matches the task, then enforce its format:"]
    for intent in sorted(ROLES):
        reqs = REQUIREMENTS.get(intent, "").replace("\n", " ")
        lines.append(f"\n### {intent}")
        lines.append(f"Role: {ROLES[intent]}")
        lines.append(f"Format: {FORMATS.get(intent, '')}")
        if reqs:
            lines.append(f"Requirements: {reqs}")
    # scorer-grade bands come from the real grade() thresholds
    lines.append("\n### Low confidence rule")
    lines.append(
        "If you are not sure which intent fits, fall back to the generic "
        "`chat` role and answer directly. A confident wrong guess is worse "
        "than an honest generic answer."
    )
    return "\n".join(lines) + "\n"


def _workflow_section():
    return (
        "## The improvement loop\n\n"
        "Scoring alone is not the point. Run every prompt through this loop:\n\n"
        "1. **Score the draft** with the 5 checks above. Write down every "
        "check below full marks — that list is your repair plan.\n\n"
        "2. **Rebuild in one pass**: intent role → Task → Context "
        "(2–3 sentences) → Requirements → Output format → Guardrail "
        "('say when unsure'). Fix the weak checks first; do not rewrite "
        "the checks that already score full marks.\n\n"
        "3. **Prove it got better**: score the rebuild on the same 5 checks "
        "and demand a positive margin (rebuilt − draft, in points). If the "
        "margin is zero or negative, do not ship it — fix the single check "
        "with the biggest gap and re-score. A rewrite that only *looks* "
        "better but scores the same is a wasted rewrite.\n\n"
        "3b. **Inspect the rewrite**: diff the draft against the rebuild "
        "word by word. The changed words should map to the weak checks from "
        "step 1 — if untouched checks also changed, the rewrite added noise "
        "instead of focus.\n\n"
        "4. **Keep the good ones**: save named prompts with version history. "
        "Every re-save keeps the before→after scores on the record, so the "
        "version list is a scoreboard: last score, best score, and the "
        "improvement (Δ) since the first version.\n\n"
        "5. **Track over time**: log scores for repeated prompts and watch "
        "the trend — improving, steady, or slipping. A slipping prompt "
        "means the task drifted; rebuild it.\n\n"
        "6. **Guard the library**: re-score every saved prompt against the "
        "best score it ever recorded. A negative delta means the prompt "
        "regressed — re-pass it (rebuild, prove, re-save) before shipping. "
        "Run the guard in CI so regressions block automatically.\n\n"
        "With the PromptSmith CLI installed, start with `init` (a project folder with two worked demo prompts), then the loop maps to commands: "
        "`score` → `improve` → `compare` (+`diff` for the word changes) → "
        "`save` / `library` → `report` → `stats` (the whole picture: totals across history and library) → `check` (the regression guard) → "
        "`rollback` (restore any saved version as a new one — history is never rewritten) → "
        "`export` (share the library as Markdown or JSON) → "
        "`import` (bring a shared JSON export back in — duplicates skipped, "
        "scores preserved). "
        "Measure the prompt's token load with `tokens` and budget its API "
        "cost with `cost` before shipping. "
        "The workflow above works without the tool too.\n"
    )


def _example_section():
    result = improve_prompt(EXAMPLE_ROUGH)
    top = what_improved(result["deltas"], top=3)
    gains = ", ".join(f"{check} +{delta}" for check, delta in top)
    return (
        "## Worked example (real output)\n\n"
        f'Rough prompt: "{EXAMPLE_ROUGH}"\n\n'
        f"Scored {result['before']['score']}/100 ({scorer.grade(result['before']['score'])}) → "
        f"improved {result['after']['score']}/100 ({scorer.grade(result['after']['score'])}), "
        f"margin +{result['margin']} points, intent `{result['intent']}` "
        f"(confidence {result['confidence']}).\n\n"
        f"Biggest gains: {gains}.\n\n"
        "```\n" + result["enhanced"] + "\n```\n"
    )


def render_skill(name=SKILL_NAME):
    """Render the skill as SKILL.md markdown text."""
    frontmatter = (
        "---\n"
        f"name: {name}\n"
        "description: Score prompts 0-100, then run the improvement loop — "
        "rebuild, prove the gain, version the result — on a 5-check rubric "
        "(clarity, context, specificity, format, guardrails) with "
        "intent-specific roles.\n"
        "---\n"
    )
    body = (
        "\n# PromptSmith — prompt engineering skill\n\n"
        "Use this skill whenever you write or improve a prompt for an LLM. "
        "Apply the checks first, then rebuild the prompt.\n\n"
        + _checks_section()
        + "\n"
        + _roles_section()
        + "\n"
        + _workflow_section()
        + "\n"
        + _example_section()
        + "\n## Rebuild recipe\n\n"
        "1. Score the draft with the 5 checks above; note what's missing.\n"
        "2. Pick the intent role (or fall back to `chat`).\n"
        "3. Rebuild: role line → Task → Context (2–3 sentences) → "
        "Requirements → Output format → Guardrail ('say when unsure').\n"
        "4. Re-score mentally: the rebuilt prompt should gain 20+ points.\n"
    )
    return frontmatter + body


def write_skill(directory, name=SKILL_NAME):
    """Write <directory>/<name>/SKILL.md (the layout agent CLIs expect).

    Returns the path of the written file.
    """
    skill_dir = os.path.join(os.path.expanduser(directory), name)
    os.makedirs(skill_dir, exist_ok=True)
    path = os.path.join(skill_dir, "SKILL.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_skill(name))
    return path
