"""Import a shared library export back into the local library.

This is the round trip for `promptsmith export --format json`: a teammate
exports their library, you import the JSON, and their proven prompts land
in your `.promptsmith/library.jsonl` as new versions — nothing overwrites
anything you already saved.

`promptsmith import library.json`   -> import every prompt in the file
`promptsmith import library.json --json` -> machine-readable report

Rules, kept honest on purpose:
- Only exports made by promptsmith are accepted (`"tool": "promptsmith"`).
  Anything else is refused, not half-imported.
- Imported scores are preserved exactly as exported — the point of sharing
  is proven prompts, not re-scoring them under your scorer.
- An entry that is already in your library (same name, same prompt text,
  same improved text) is skipped as a duplicate, never doubled.
- A name you already have gets new version numbers continuing from yours,
  so history stays one clean sequence per name.
"""

import json
import os
from datetime import datetime, timezone

from .library import LIBRARY_DIR, LIBRARY_FILE, entries_for, load_library
from .scorer import grade


def _append_records(records, cwd=None):
    """Append raw library records to library.jsonl. No re-scoring."""
    base = cwd or os.getcwd()
    path = os.path.join(base, LIBRARY_DIR, LIBRARY_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def import_payload(payload, cwd=None):
    """Import an export payload (see export.py) into the library.

    Returns a report dict: {"imported", "skipped", "names"}. Raises
    ValueError on anything that is not a promptsmith export.
    """
    if not isinstance(payload, dict):
        raise ValueError("export file must contain a JSON object")
    if payload.get("tool") != "promptsmith":
        raise ValueError("not a promptsmith export "
                         "(missing \"tool\": \"promptsmith\")")
    prompts = payload.get("prompts")
    if not isinstance(prompts, list):
        raise ValueError("export has no \"prompts\" list")
    existing = load_library(cwd)
    imported = 0
    skipped = 0
    names = []
    new_records = []
    for group in prompts:
        if not isinstance(group, dict):
            skipped += 1
            continue
        name = group.get("name")
        entries = group.get("entries")
        if not name or not isinstance(entries, list):
            skipped += 1
            continue
        known = {(r.get("prompt"), r.get("enhanced"))
                 for r in entries_for(name, existing)}
        version = len(entries_for(name, existing))
        touched = False
        for entry in sorted(entries, key=lambda e: e.get("version", 0)):
            if not isinstance(entry, dict):
                skipped += 1
                continue
            prompt = entry.get("prompt") or ""
            enhanced = entry.get("enhanced")
            if not prompt.strip():
                skipped += 1
                continue
            if (prompt, enhanced) in known:
                skipped += 1
                continue
            version += 1
            score = entry.get("score", 0)
            try:
                score = int(score)
            except (TypeError, ValueError):
                score = 0
            record = {
                "prompt": prompt,
                "enhanced": enhanced,
                "before_score": None,
                "intent": None,
                "confidence": None,
                "breakdown": None,
                "ts": entry.get("saved") or datetime.now(
                    timezone.utc).isoformat(timespec="seconds"),
                "name": name,
                "version": version,
                "score": score,
                "grade": entry.get("grade") or grade(score),
                "tags": entry.get("tags") or [],
            }
            new_records.append(record)
            known.add((prompt, enhanced))
            imported += 1
            touched = True
        if touched:
            names.append(name)
    if new_records:
        _append_records(new_records, cwd)
    return {"imported": imported, "skipped": skipped, "names": names}


def import_file(path, cwd=None):
    """Read a JSON export file and import it. Returns the report dict."""
    with open(path, encoding="utf-8") as f:
        try:
            payload = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"not valid JSON: {e}") from e
    return import_payload(payload, cwd)
