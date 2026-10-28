"""Delete a saved prompt (or one version) from the library.

`promptsmith delete NAME`            -> remove every version of NAME
`promptsmith delete NAME --version 2` -> remove only version 2 of NAME

The library keeps its version numbers: deleting v2 of a 3-version prompt
leaves v1 and v3, never renumbered — the same "history is never rewritten"
rule as rollback. A deleted version is gone for good (the library file is
plain JSONL, so a backup copy before deleting is the only undo).

Unknown names and unknown versions raise ValueError — the CLI turns those
into "Delete refused: ..." and exits 1, same refusal style as rollback.
"""

import json
import os

from .library import entries_for, library_path, load_library


def delete_entry(name, version=None, cwd=None):
    """Remove entries from the library file and return a report dict.

    Report: name, deleted (count), deleted_versions (list of version
    numbers removed), remaining_versions (list still saved for the name),
    remaining_total (entries left in the whole library).
    """
    records = load_library(cwd)
    mine = entries_for(name, records)
    if not mine:
        raise ValueError(f'No saved prompt named "{name}".')
    if version is None:
        doomed = mine
    else:
        doomed = [r for r in mine if r.get("version") == version]
        if not doomed:
            raise ValueError(f'No version {version} for "{name}".')
    doomed_ids = {id(r) for r in doomed}
    kept = [r for r in records if id(r) not in doomed_ids]
    path = library_path(cwd)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    remaining = entries_for(name, kept)
    return {
        "name": name,
        "deleted": len(doomed),
        "deleted_versions": [r["version"] for r in doomed],
        "remaining_versions": [r["version"] for r in remaining],
        "remaining_total": len(kept),
    }
