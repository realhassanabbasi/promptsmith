"""Agent skill export: package PromptSmith's rubric as an installable skill.

Agent skills (Claude Code, Codex, Cursor) are small SKILL.md instruction
packs. This module renders one from PromptSmith's REAL scoring logic and
enhancement pipeline — nothing invented, nothing hardcoded twice.
"""

import os

from . import scorer
from .enhancer import FORMATS, REQUIREMENTS, ROLES, enhance

SKILL_NAME = "promptsmith"

# The worked example is produced by the real enhance() call at render time,
# so the skill always shows genuine output, never a mockup.
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


def _example_section():
    result = enhance(EXAMPLE_ROUGH)
    return (
        "## Worked example (real output)\n\n"
        f'Rough prompt: "{EXAMPLE_ROUGH}"\n\n'
        f"Scored {result['before']}/100 ({scorer.grade(result['before'])}) → "
        f"enhanced {result['after']}/100 ({scorer.grade(result['after'])}), "
        f"intent `{result['intent']}` (confidence {result['confidence']}).\n\n"
        "```\n" + result["prompt"] + "\n```\n"
    )


def render_skill(name=SKILL_NAME):
    """Render the skill as SKILL.md markdown text."""
    frontmatter = (
        "---\n"
        f"name: {name}\n"
        "description: Score prompts 0-100 and rewrite them using a 5-check "
        "rubric (clarity, context, specificity, format, guardrails) with "
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
