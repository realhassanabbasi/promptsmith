"""Skill enhance — score and rewrite an agent skill file (SKILL.md).

`promptsmith skill` exports a skill from the real rubric. `skill-enhance`
does the same job for a skill file that already exists: it scores the file
part by part on what makes a skill usable by a coding agent, then rewrites
each weak part the way `enhance` rewrites a weak prompt.

Six parts, weighted to 100 (weights in PART_WEIGHTS):

- frontmatter — name + description present, specific, right length.
  A skill without frontmatter does not load in Claude Code, so it scores 0.
- instructions — clear steps, concrete actions, no vague filler
  ("be helpful", "do your best", "use your judgment").
- examples — present, realistic, showing input -> output.
- workflow — ordered steps, a decision point, what to do when stuck.
- references — file paths the skill mentions must exist next to the skill
  (user-install paths like ~/.claude/skills/ are skipped: they cannot be
  checked here). Missing paths are findings, never silently fixed.
- constraints — what the skill must NOT do, stated explicitly.

The rewrite is honest the way `enhance` is: it only makes mechanical,
safe fixes. Missing sections become clearly-marked TODO placeholders
(the skill's own words are never invented), vague lines the rewriter
cannot fix safely are listed as "still vague" with line numbers instead
of being hidden, and the original file is never touched by default:
`skill-enhance SKILL.md` writes SKILL.enhanced.md next to it.
`--in-place` overwrites only after writing a `.bak` backup, the same
safety rule `doctor --fix` uses.

`promptsmith skill-enhance SKILL.md`  -> per-part bars, before -> after
`promptsmith skill-enhance`            -> SKILL.md in the current folder
`--dry-run`                           -> score + planned changes, write nothing
`--output FILE`                       -> write the enhanced skill to FILE
`--in-place`                          -> overwrite after a .bak backup
`--fail`                              -> exit 1 when the BEFORE score is
                                         below 70 (the rubric's good line)
`--json`                              -> machine-readable results
"""

import os
import re

# part -> weight; the weights sum to 100, so the overall score is the
# weighted mean of the part scores.
PART_WEIGHTS = {
    "frontmatter": 15,
    "instructions": 25,
    "examples": 20,
    "workflow": 15,
    "references": 10,
    "constraints": 15,
}

# Phrases that sound like guidance but say nothing an agent can act on.
VAGUE_PHRASES = (
    "be helpful",
    "do your best",
    "use your judgment",
    "use your judgement",
    "as needed",
    "appropriately",
    "handle it well",
    "do a good job",
    "best practice",
    "best practices",
    "and so on",
    "something like that",
)

# Vague lines the rewriter can replace safely: the meaning is fully
# covered by the house guardrail, so nothing is lost.
SAFE_REPLACEMENTS = {
    "be helpful": "Answer directly. If you are unsure, say so and ask "
                  "for the missing input instead of guessing.",
    "do your best": "Answer directly. If you are unsure, say so and ask "
                    "for the missing input instead of guessing.",
}

# Lines that state a hard limit. Distinct markers count, not repeats.
CONSTRAINT_MARKERS = (
    "do not",
    "don't",
    "never",
    "must not",
    "must never",
    "avoid",
    "forbidden",
    "not allowed",
)

STUCK_MARKERS = (
    "if unsure",
    "if stuck",
    "fallback",
    "escalate",
    "ask the user",
    "say so",
    "stop and",
)

# File paths a skill may reference: backtick spans or bare tokens with a
# known suffix. URLs and ~ install paths are never treated as references.
_PATH_RE = re.compile(
    r"`([^`\s]*\.(?:md|py|json|ya?ml|toml|js|ts|txt|html|css|sh))`"
    r"|(?<![\w/:])((?:[\w.\-]+/)+[\w.\-]+\.(?:md|py|json|ya?ml|toml|js|ts|txt|html|css|sh))"
    r"|`([^`\s]+/[^`\s]*)`"
)

HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)


def grade(total):
    """Same bands as the prompt rubric: 85+ excellent, 70+ good, 50+ okay."""
    if total >= 85:
        return "excellent"
    if total >= 70:
        return "good"
    if total >= 50:
        return "okay"
    return "weak"


def parse_skill(text):
    """Split a skill file into frontmatter + sections.

    Returns {"frontmatter": {"name": str|None, "description": str|None,
    "present": bool}, "sections": [(heading, body)], "body": str}.
    Headings are the ## lines; the text before the first heading is the
    intro and is kept as a section headed "".
    """
    text = text.replace("\r\n", "\n")
    frontmatter = {"name": None, "description": None, "present": False}
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            frontmatter["present"] = True
            raw = text[4:end]
            for line in raw.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key = key.strip().lower()
                if key in ("name", "description"):
                    frontmatter[key] = value.strip().strip("\"'")
            body = text[end + 4:].lstrip("\n")
    sections = []
    current_head, current_lines = "", []
    for line in body.splitlines():
        match = HEADING_RE.match(line)
        if match:
            sections.append((current_head, "\n".join(current_lines)))
            current_head, current_lines = match.group(1).strip(), []
        else:
            current_lines.append(line)
    sections.append((current_head, "\n".join(current_lines)))
    return {"frontmatter": frontmatter, "sections": sections, "body": body}


def _append_to_section(text, words, heading, addition):
    """Add `addition` to the end of the section whose heading contains
    any of `words`; if there is no such section, create it at the end.

    Appending to the existing section (instead of adding a second heading)
    keeps a skill with a thin Workflow or Constraints section to exactly
    one heading for it.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match and any(w in match.group(1).lower() for w in words):
            start = i
            break
    if start is None:
        return text.rstrip("\n") + "\n\n## " + heading + "\n\n" + addition
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if HEADING_RE.match(lines[j]):
            end = j
            break
    while end > start + 1 and lines[end - 1].strip() == "":
        end -= 1
    new_lines = (lines[:end] + [""] + addition.rstrip("\n").splitlines()
                 + lines[end:])
    result = "\n".join(new_lines)
    return result + ("\n" if text.endswith("\n") else "")


def _find_section(parsed, *words):
    """First section whose heading contains any of the words, else None."""
    for heading, section_body in parsed["sections"]:
        low = heading.lower()
        if any(w in low for w in words):
            return section_body
    return None


def _vague_lines(text):
    """(line_number, line) for every line carrying a vague filler phrase."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        low = line.lower()
        if any(phrase in low for phrase in VAGUE_PHRASES):
            found.append((number, line.strip()))
    return found


def _find_references(text):
    """File paths the skill mentions, in order, duplicates removed."""
    refs = []
    for match in _PATH_RE.finditer(text):
        ref = match.group(1) or match.group(2) or match.group(3)
        if not ref or ref.startswith(("http://", "https://", "~/")):
            continue
        ref = ref.strip().strip(".,;")
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _score_frontmatter(parsed, findings):
    fm = parsed["frontmatter"]
    if not fm["present"]:
        findings.append("No frontmatter — the skill will not load in "
                        "Claude Code. Add a --- block with name + "
                        "description.")
        return 0
    score = 0
    if fm["name"]:
        score += 35
        if re.fullmatch(r"[a-z0-9][a-z0-9\-]*", fm["name"]):
            score += 20
        else:
            score += 5
            findings.append(f"Skill name {fm['name']!r} is not a "
                            "lowercase-hyphen slug — rename it.")
    else:
        findings.append("Frontmatter has no name — add one.")
    desc = fm["description"]
    if desc:
        score += 25
        if 40 <= len(desc) <= 250:
            score += 10
        else:
            findings.append("Description should be one specific sentence "
                            f"({len(desc)} chars now) — 40 to 250 chars.")
        low = desc.lower()
        generic = ("helpful assistant", "a skill", "does things",
                   "helps with tasks")
        if (any(v in low for v in ("write", "score", "build", "check",
                                    "generate", "review", "create", "teach",
                                    "explain", "improve", "find"))
                and not any(g in low for g in generic)):
            score += 10
        else:
            findings.append("Description is vague — say what the skill "
                            "does, for whom, and what good output looks "
                            "like.")
    else:
        findings.append("Frontmatter has no description — add one specific "
                        "sentence.")
    return min(score, 100)


def _score_instructions(parsed, findings):
    body = parsed["body"]
    words = body.split()
    vague = _vague_lines(body)
    score = 100
    numbered = bool(re.search(r"(?m)^\s*\d+[.)]\s+\S", body))
    # Imperative lines count only when they are not themselves vague:
    # "Use your judgment" is an instruction-shaped filler line, not a step.
    vague_set = {number for number, _ in vague}
    concrete_lines = [line for number, line in
                      enumerate(body.splitlines(), start=1)
                      if number not in vague_set]
    imperative = bool(re.search(
        r"(?m)^(use|write|check|run|score|build|read|list|do|don't|do not|"
        r"never|always|start|pick|save|open|create|generate|compare|"
        r"explain|review)\b", "\n".join(concrete_lines), re.IGNORECASE))
    if not numbered and not imperative:
        score -= 25
        findings.append("Instructions have no numbered steps or imperative "
                        "lines — write what to do as steps.")
    if vague:
        penalty = min(15 * len(vague), 45)
        score -= penalty
        for number, line in vague:
            findings.append(f"Vague line {number}: {line!r} — say what "
                            "to do instead.")
    if len(words) < 60:
        score -= 20
        findings.append("Instructions are too thin (under 60 words) — "
                        "say what to do, in order.")
    return max(score, 0)


def _score_examples(parsed, findings):
    section = _find_section(parsed, "example")
    score = 0
    if section is not None:
        score += 40
        low = section.lower()
        has_io = (("input" in low and "output" in low)
                  or ("before" in low and "after" in low)
                  or ("given" in low and "return" in low))
        if has_io:
            score += 35
        else:
            findings.append("Example shows no input → output pair — add "
                            "one real pair.")
        concrete = (re.search(r"\b\d+\b", section)
                    or re.search(r"`[^`]+`", section)
                    or '"' in section)
        if concrete:
            score += 25
        else:
            findings.append("Example has no concrete detail — a number, a "
                            "path, or a quoted string.")
    else:
        findings.append("No example section — add one real input → output "
                        "pair.")
        if "```" in parsed["body"]:
            score += 20
    return min(score, 100)


def _score_workflow(parsed, findings):
    body = parsed["body"].lower()
    score = 0
    if (re.search(r"(?m)^\s*\d+[.)]\s+\S", parsed["body"])
            or "step 1" in body):
        score += 40
    else:
        findings.append("No ordered workflow steps — number the steps.")
    if (("if " in body and ("then" in body or "otherwise" in body
                            or "else" in body))
            or "when " in body):
        score += 30
    else:
        findings.append("No decision point — say what to do when the "
                        "task branches (if/when).")
    if any(marker in body for marker in STUCK_MARKERS):
        score += 30
    else:
        findings.append("No stuck rule — say what to do when a step "
                        "cannot be completed.")
    return min(score, 100)


def _score_references(parsed, base_dir, findings):
    refs = _find_references(parsed["body"])
    if not refs:
        findings.append("No file references mentioned — nothing to check.")
        return 100
    score = 100
    for ref in refs:
        path = os.path.expanduser(ref)
        if not os.path.isabs(path):
            path = os.path.join(base_dir or os.getcwd(), path)
        if not os.path.exists(path):
            score -= 25
            findings.append(f"Broken reference: {ref} does not exist — "
                            "create the file or fix the path.")
    return max(score, 0)


def _score_constraints(parsed, findings):
    low = parsed["body"].lower()
    found = [m for m in CONSTRAINT_MARKERS if m in low]
    if len(found) >= 3:
        return 100
    if len(found) == 2:
        return 75
    if len(found) == 1:
        findings.append("Only one explicit constraint — state at least "
                        "two hard limits (never / do not).")
        return 50
    findings.append("No explicit constraints — say what the skill must "
                    "NOT do.")
    return 10


def score_skill(text, base_dir=None):
    """Score a skill file: (overall 0-100, parts dict, findings list).

    Parts are scored 0-100 each; the overall score is the weighted mean
    (weights in PART_WEIGHTS). Findings name the fix for every weak part.
    """
    parsed = parse_skill(text)
    findings = []
    parts = {
        "frontmatter": _score_frontmatter(parsed, findings),
        "instructions": _score_instructions(parsed, findings),
        "examples": _score_examples(parsed, findings),
        "workflow": _score_workflow(parsed, findings),
        "references": _score_references(parsed, base_dir, findings),
        "constraints": _score_constraints(parsed, findings),
    }
    overall = round(sum(parts[p] * PART_WEIGHTS[p] for p in parts) / 100)
    return overall, parts, findings


def enhance_skill(text, base_dir=None, name_hint=None):
    """Rewrite each weak part of a skill file.

    Returns a dict with before/after scores, per-part scores, the list of
    changes made, the vague lines left for the human (line, text), and
    the enhanced text. Only mechanical, safe fixes are applied: missing
    sections become clearly-marked TODO placeholders, vague lines with a
    safe replacement get the house guardrail, everything else is listed
    instead of rewritten.
    """
    before, parts_before, _ = score_skill(text, base_dir)
    parsed = parse_skill(text)
    changes, still_vague = [], []
    enhanced = text.replace("\r\n", "\n")

    # Frontmatter: add the block if missing; fill a missing/vague
    # description with a marked placeholder (never invent the wording).
    fm = parsed["frontmatter"]
    if not fm["present"]:
        stem = name_hint or "skill"
        changes.append("Frontmatter: added --- block (name + description "
                       "placeholder) — the skill would not load without it.")
        enhanced = ("---\n"
                    f"name: {stem}\n"
                    "description: TODO: one specific sentence — what this "
                    "skill does, for whom, and what good output looks like.\n"
                    "---\n\n" + enhanced)
    elif not fm["description"] or len(fm["description"]) < 40:
        desc_line = ("description: TODO: one specific sentence — "
                     "what this skill does, for whom, and what good "
                     "output looks like.")
        lines = enhanced.splitlines()
        replaced = False
        for i, line in enumerate(lines):
            if line.lower().startswith("description:"):
                lines[i] = desc_line
                replaced = True
                break
        if not replaced:
            # insert before the closing --- of the frontmatter block
            for i, line in enumerate(lines):
                if i > 0 and line.strip() == "---":
                    lines.insert(i, desc_line)
                    break
        enhanced = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
        changes.append("Frontmatter: description was missing or too short "
                       "— replaced with a marked TODO placeholder.")

    # Instructions: safe replacements only; the rest stays listed.
    fixed_vague = 0
    lines = enhanced.splitlines()
    for i, line in enumerate(lines):
        low = line.lower()
        for phrase, replacement in SAFE_REPLACEMENTS.items():
            if phrase in low:
                lines[i] = replacement
                fixed_vague += 1
                break
    if fixed_vague:
        enhanced = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
        changes.append(f"Instructions: replaced {fixed_vague} vague line(s) "
                       "with the concrete guardrail (answer directly; say "
                       "when unsure).")
    for number, line in _vague_lines(enhanced):
        still_vague.append((number, line))

    # Examples: a missing section becomes a marked template.
    parsed = parse_skill(enhanced)
    if _find_section(parsed, "example") is None:
        enhanced = enhanced.rstrip("\n") + (
            "\n\n## Example\n\n"
            "TODO: show one real input → output pair here.\n\n"
            "Input: ...\n\n"
            "Output: ...\n")
        changes.append("Examples: added an Example section template — fill "
                       "in one real input → output pair.")
    elif parts_before["examples"] < 100:
        changes.append("Examples: kept as-is — add an input → output pair "
                       "and a concrete detail to reach full marks.")

    # Workflow: generic guardrail steps that hold for any skill. They go
    # into the existing Workflow section when there is one, so the skill
    # never ends up with two Workflow headings.
    parsed = parse_skill(enhanced)
    if parts_before["workflow"] < 100:
        steps = (
            "1. Read the task and the instructions above, in order.\n"
            "2. Do the steps in order; do not skip ahead.\n"
            "3. If a step cannot be completed, stop and say what is "
            "missing instead of guessing.\n"
            "4. If the task does not match this skill, say so instead of "
            "forcing it.\n\n"
            "If you get stuck, report what you tried and what is missing, "
            "then ask.\n")
        enhanced = _append_to_section(enhanced, ("workflow",), "Workflow",
                                      steps)
        changes.append("Workflow: added ordered steps with a decision point "
                       "and a stuck rule.")

    # Constraints: generic hard limits, true for any skill — same rule,
    # into the existing Constraints section when there is one.
    parsed = parse_skill(enhanced)
    if parts_before["constraints"] < 100:
        limits = (
            "- Never invent facts the skill does not give you.\n"
            "- Never rewrite what is already correct.\n"
            "- If you are unsure, say so instead of guessing.\n"
            "- Do not use this skill for tasks it does not cover.\n")
        enhanced = _append_to_section(enhanced, ("constraint",),
                                      "Constraints", limits)
        changes.append("Constraints: added explicit hard limits "
                       "(never / do not).")

    after, parts_after, _ = score_skill(enhanced, base_dir)
    return {
        "before": before,
        "after": after,
        "gain": after - before,
        "parts_before": parts_before,
        "parts_after": parts_after,
        "changes": changes,
        "still_vague": still_vague,
        "enhanced": enhanced,
    }


def skill_enhance_payload(result):
    """Machine-readable envelope for the enhance result."""
    return {
        "before": result["before"],
        "grade_before": grade(result["before"]),
        "after": result["after"],
        "grade_after": grade(result["after"]),
        "gain": result["gain"],
        "parts_before": result["parts_before"],
        "parts_after": result["parts_after"],
        "changes": result["changes"],
        "still_vague": [{"line": n, "text": t}
                        for n, t in result["still_vague"]],
        "enhanced": result["enhanced"],
    }


def enhanced_path(path):
    """Default output next to the original: SKILL.md -> SKILL.enhanced.md."""
    if path.endswith(".md"):
        return path[:-3] + ".enhanced.md"
    return path + ".enhanced.md"


def enhance_skill_file(path, output=None, in_place=False, dry_run=False):
    """Score + enhance a skill file on disk.

    Default: write the enhanced skill next to the original and leave the
    original untouched. --output writes to FILE instead. --in-place
    overwrites the original after writing a .bak backup. --dry-run writes
    nothing. Returns the enhance result plus "file", "written" (path or
    None) and "backup" (path or None).
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    base_dir = os.path.dirname(os.path.abspath(path))
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-") or "skill"
    result = enhance_skill(text, base_dir, name_hint=stem)
    result["file"] = path
    result["written"] = None
    result["backup"] = None
    if dry_run:
        return result
    if in_place:
        backup = path + ".bak"
        with open(backup, "w", encoding="utf-8") as f:
            f.write(text)
        result["backup"] = backup
        target = path
    else:
        target = output or enhanced_path(path)
    with open(target, "w", encoding="utf-8") as f:
        f.write(result["enhanced"])
    result["written"] = target
    return result
