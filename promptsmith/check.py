"""Regression check — re-score your saved library against its own history.

`promptsmith check` re-scores each saved prompt's keeper text with the
current rubric and compares it to the best score that prompt ever recorded.
The scorer is deterministic, so any non-zero delta means something changed:
usually a PromptSmith upgrade made the rubric stricter (or fairer), and the
regressed prompts deserve a re-pass before they ship again.

`promptsmith check`              -> health table for the whole library
`promptsmith check NAME`         -> health of one saved prompt
`promptsmith check --fail-on-regression` -> exit 1 if any prompt regressed
`--json`                         -> machine-readable results (keeps script
                                    output pure when piped into CI)
"""

from .library import entries_for, load_library
from .scorer import score_prompt

VERDICTS = ("regressed", "steady", "improved")


def keeper_text(record):
    """The text a record actually stands for: the enhanced version when the
    record was saved with --improve, otherwise the original prompt."""
    return record.get("enhanced") or record.get("prompt") or ""


def verdict_for(delta):
    return "regressed" if delta < 0 else "improved" if delta > 0 else "steady"


def check_name(name, records=None, cwd=None):
    """Re-score one saved prompt's keeper text and compare with its recorded
    best. Returns a result dict, or None when nothing is saved under `name`."""
    versions = entries_for(name, records, cwd)
    if not versions:
        return None
    keeper = keeper_text(versions[-1])
    if not keeper.strip():
        return None
    current, _breakdown, _feedback = score_prompt(keeper)
    best = max(v.get("score", 0) for v in versions)
    delta = current - best
    tags = []
    for v in versions:
        for t in v.get("tags") or []:
            if t not in tags:
                tags.append(t)
    return {
        "name": name,
        "versions": len(versions),
        "current": current,
        "best": best,
        "delta": delta,
        "verdict": verdict_for(delta),
        "tags": tags,
    }


def check_library(records=None, cwd=None):
    """Health-check every saved prompt, regressed first. Empty library -> []."""
    if records is None:
        records = load_library(cwd)
    names = []
    for r in records:
        n = r.get("name", "")
        if n and n not in names:
            names.append(n)
    results = [check_name(n, records, cwd) for n in names]
    results = [r for r in results if r is not None]
    results.sort(key=lambda r: (r["delta"], -r["best"]))
    return results


def check_payload(results):
    """Machine-readable envelope: per-prompt results plus totals."""
    counts = {v: 0 for v in VERDICTS}
    for r in results:
        counts[r["verdict"]] += 1
    return {
        "results": results,
        "checked": len(results),
        **counts,
    }
