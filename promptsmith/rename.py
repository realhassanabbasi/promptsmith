"""Rename a saved prompt in the library.

`promptsmith rename OLD NEW` -> every version saved under OLD now lives
under NEW: same version numbers, same scores, same tags, same order.
Nothing is re-scored and nothing is renumbered — a rename is a label
change, not a new version.

Two refusals, both ValueError (the CLI turns them into
"Rename refused: ..." and exits 1, same refusal style as rollback and
delete):
- OLD has no saved versions.
- NEW already exists — renaming onto an existing name would merge two
  histories into one, and merged histories lie about which versions
  belong to which prompt. Rename to a fresh name instead.

Score history (`.promptsmith/history.jsonl`) is untouched: it is keyed
by prompt text, not by library name, so a rename changes no history.
"""

import json
import os

from .library import entries_for, library_path, load_library


def rename_entry(old, new, cwd=None):
    """Rename every version of OLD to NEW and return a report dict.

    Report: old, new, renamed (count), versions (version numbers moved),
    remaining_total (entries left in the whole library).
    """
    if old == new:
        raise ValueError(f'"{old}" is already the name.')
    records = load_library(cwd)
    mine = entries_for(old, records)
    if not mine:
        raise ValueError(f'No saved prompt named "{old}".')
    if entries_for(new, records):
        raise ValueError(
            f'A saved prompt named "{new}" already exists — '
            "renaming would merge two histories."
        )
    for r in mine:
        r["name"] = new
    path = library_path(cwd)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {
        "old": old,
        "new": new,
        "renamed": len(mine),
        "versions": [r["version"] for r in mine],
        "remaining_total": len(records),
    }
