"""Prune the library and the score history — keep the best, drop the rest.

`refresh` grows the library: every rebuild that beats the recorded best is
saved as a new version. Nothing ever trims it back. `prune` is the other
half of that pair — it keeps the library lean without rewriting history.

`promptsmith prune`                     -> keep the 2 best versions of every
                                           saved name, drop history records
                                           older than 30 days
`promptsmith prune --keep 1`            -> keep only each name's best version
`promptsmith prune --history-days 7`    -> drop history older than 7 days
`promptsmith prune --library-only`      -> leave the history alone
`promptsmith prune --history-only`      -> leave the library alone
`promptsmith prune --dry-run`           -> show what would go, delete nothing

Rules, stated plainly:

- Library: versions are ranked by score, best first; ties go to the
  LATEST version (the fresher text at the same score wins). The versions
  left behind keep their numbers — the same "history is never rewritten"
  rule as delete and rollback.
- History: a record is dropped only when its timestamp parses AND is
  older than the cutoff. A record with a missing or unparseable timestamp
  is KEPT — prune never deletes what it cannot date.
- `--dry-run` changes nothing; the report says so on every line.
- `keep` below 1 and negative `--history-days` raise ValueError — the CLI
  turns those into a refusal and exits 1.
"""

import json
import os
from datetime import datetime, timedelta, timezone

from .history import history_path, load_history
from .library import library_path, load_library

DEFAULT_KEEP = 2
DEFAULT_HISTORY_DAYS = 30


def _parse_ts(value):
    """Parse an ISO timestamp into an aware datetime, or None.

    Naive timestamps (no offset) are read as UTC — every record this tool
    writes carries an offset, so a naive one came from somewhere else and
    UTC is the honest reading. Unparseable values return None instead of
    raising: the caller decides what to do with undatable records.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def prune_library(keep=DEFAULT_KEEP, dry_run=False, cwd=None):
    """Keep the `keep` best versions of every saved name, drop the rest.

    Returns one row per name that had versions: name, kept_versions and
    dropped_versions (version numbers, ascending), kept and dropped
    counts. Names with `keep` or fewer versions report zero dropped —
    nothing is deleted that does not need deleting. The file is rewritten
    as JSONL in the original order, minus the dropped records.
    """
    if keep < 1:
        raise ValueError(f"--keep must be at least 1, got {keep}.")
    records = load_library(cwd)
    groups = {}
    for r in records:
        groups.setdefault(r.get("name", ""), []).append(r)
    rows = []
    dropped_ids = set()
    for name, versions in groups.items():
        ranked = sorted(
            versions,
            key=lambda r: (r.get("score") or 0, r.get("version") or 0),
            reverse=True,
        )
        kept = ranked[:keep]
        dropped = ranked[keep:]
        dropped_ids.update(id(r) for r in dropped)
        rows.append({
            "name": name,
            "kept_versions": sorted(r.get("version") for r in kept),
            "dropped_versions": sorted(r.get("version") for r in dropped),
            "kept": len(kept),
            "dropped": len(dropped),
        })
    rows.sort(key=lambda r: r["name"])
    if dropped_ids and not dry_run:
        kept_records = [r for r in records if id(r) not in dropped_ids]
        path = library_path(cwd)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for r in kept_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows


def prune_history(days=DEFAULT_HISTORY_DAYS, dry_run=False, cwd=None):
    """Drop history records older than `days`; undatable records are kept.

    Returns dropped and kept counts. `days` of 0 keeps only today's
    records — anything older than right now goes.
    """
    if days < 0:
        raise ValueError(f"--history-days cannot be negative, got {days}.")
    records = load_history(cwd)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kept = []
    dropped = 0
    for r in records:
        ts = _parse_ts(r.get("ts"))
        if ts is not None and ts < cutoff:
            dropped += 1
        else:
            kept.append(r)
    if dropped and not dry_run:
        path = history_path(cwd)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for r in kept:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"dropped": dropped, "kept": len(kept)}


def prune_payload(library_rows, history_result):
    """Machine-readable envelope: per-name rows, history counts, totals."""
    dropped_total = sum(r["dropped"] for r in library_rows)
    if history_result is not None:
        dropped_total += history_result["dropped"]
    return {
        "library": library_rows,
        "history": history_result,
        "dropped_total": dropped_total,
    }
