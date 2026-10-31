"""Prompt library — save named prompts with version history.

A library entry is one JSON object per line in `.promptsmith/library.jsonl`
in the current working directory. Saving the same NAME again appends a new
version instead of overwriting — the full version history stays, so the
best-scoring version is always one glance away.

`promptsmith save NAME "prompt"`   -> scores (optionally improves) and saves
`promptsmith library`              -> one row per name: versions, last, best
`promptsmith library NAME`         -> full version history of one name

Saving the exact same prompt text under the same name twice is refused
(it would only double an entry) unless `force=True` / `--force` is given.
Rollback is exempt: restoring an old version as a new one is intentional.
"""

import json
import os
from datetime import datetime, timezone

LIBRARY_DIR = ".promptsmith"
LIBRARY_FILE = "library.jsonl"


def library_path(cwd=None):
    base = cwd or os.getcwd()
    return os.path.join(base, LIBRARY_DIR, LIBRARY_FILE)


def load_library(cwd=None):
    """Read all saved entries, oldest first. Missing file -> []. Bad lines skipped."""
    records = []
    try:
        with open(library_path(cwd), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return []
    return records


def entries_for(name, records=None, cwd=None):
    """All versions of one name, oldest first. Name matching is exact."""
    if records is None:
        records = load_library(cwd)
    return [r for r in records if r.get("name") == name]


def save_entry(name, prompt, tags=None, enhance_it=False, cwd=None,
               force=False):
    """Score (optionally improve) a prompt and save it as a new version.

    Returns the record dict. `version` is 1 + the number of existing entries
    with the same name. `enhanced` is None unless `enhance_it` is True.
    Saving the exact same prompt text under the same name raises
    ValueError unless `force` is True — an exact duplicate adds no
    information, it only doubles an entry. A different name, or a
    different prompt text, always saves normally.
    """
    from .improve import improve_prompt
    from .scorer import grade, score_prompt

    tags = [t.strip() for t in (tags or []) if t.strip()]
    if not force:
        for existing in entries_for(name, cwd=cwd):
            if existing.get("prompt") == prompt:
                raise ValueError(
                    f"'{name}' already has this exact prompt saved as "
                    f"v{existing.get('version')} — use --force to save "
                    "it again"
                )
    if enhance_it:
        result = improve_prompt(prompt)
        score = result["after"]["score"]
        record = {
            "prompt": prompt,
            "enhanced": result["enhanced"],
            "before_score": result["before"]["score"],
            "intent": result["intent"],
            "confidence": result["confidence"],
            "breakdown": result["after"]["breakdown"],
        }
    else:
        total, breakdown, _feedback = score_prompt(prompt)
        record = {
            "prompt": prompt,
            "enhanced": None,
            "before_score": None,
            "intent": None,
            "confidence": None,
            "breakdown": breakdown,
        }
        score = total

    record.update({
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "name": name,
        "version": len(entries_for(name, cwd=cwd)) + 1,
        "score": score,
        "grade": grade(score),
        "tags": tags,
    })
    path = library_path(cwd)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def summarize(records=None, cwd=None):
    """One row per saved name: versions, last/best score, delta, tags."""
    if records is None:
        records = load_library(cwd)
    groups = {}
    for r in records:
        groups.setdefault(r.get("name", ""), []).append(r)
    rows = []
    for name, rs in groups.items():
        scores = [r["score"] for r in rs]
        tags = []
        for r in rs:
            for t in r.get("tags") or []:
                if t not in tags:
                    tags.append(t)
        rows.append({
            "name": name,
            "versions": len(rs),
            "last": scores[-1],
            "best": max(scores),
            "delta": scores[-1] - scores[0],
            "tags": tags,
            "saved": rs[-1].get("ts"),
        })
    rows.sort(key=lambda r: r["best"], reverse=True)
    return rows


def filter_by_tags(rows, tags):
    """Keep only rows carrying at least one of the given tags.

    Tag matching is case-insensitive and comma-separated input is split
    by the caller. Empty/blank tags mean no filtering — every row passes.
    Same any-match rule as `search --tags`, so the two flags agree.
    """
    wanted = [t.strip().lower() for t in (tags or []) if t.strip()]
    if not wanted:
        return list(rows)
    return [r for r in rows
            if any(t.lower() in wanted for t in (r.get("tags") or []))]
