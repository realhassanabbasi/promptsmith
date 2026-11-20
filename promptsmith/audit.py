"""Library audit — find the rot in your saved prompt library.

`promptsmith check` guards regressions (re-scoring against recorded
bests). `promptsmith audit` looks for the four kinds of mess that check
never sees:

* **duplicates** — the same prompt text saved under two or more names.
  `save` refuses an exact duplicate under the *same* name, but nothing
  stops the same text living under two different names.
* **weak keepers** — a name whose *best* version still grades weak
  (below `--weak`, default 50, the rubric's own weak/okay boundary).
  Those prompts need a rebuild, not another version of the same draft.
* **untagged** — names with no tag on any version. Tags are how the
  library is searched and filtered; an untagged prompt is unfindable
  by tag.
* **never improved** — names with no version saved via `--improve`.
  The library holds the raw draft and nothing better.

`promptsmith audit`            -> findings grouped by kind, with the
                                  fix for each one
`promptsmith audit --weak 70`   -> treat "good" as the bar instead
`promptsmith audit --fail`      -> exit 1 when anything is found
                                  (useful in CI, like check's
                                  --fail-on-regression)
`--json`                        -> machine-readable results
"""

import re

from .check import keeper_text
from .library import load_library

DEFAULT_WEAK = 50


def normalize_text(text):
    """Collapse whitespace and case so the same prompt written two ways
    still counts as one prompt."""
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def find_duplicates(records=None, cwd=None):
    """Same keeper text under two or more names. Returns one row per
    duplicated text: the names carrying it, how many versions, and a
    short preview. A name appearing twice with the same text is not a
    duplicate — the group only counts when the names differ."""
    if records is None:
        records = load_library(cwd)
    groups = {}
    for r in records:
        key = normalize_text(keeper_text(r))
        if not key:
            continue
        groups.setdefault(key, {"names": [], "versions": 0, "preview": key})
        if r.get("name") not in groups[key]["names"]:
            groups[key]["names"].append(r.get("name", ""))
        groups[key]["versions"] += 1
    rows = [g for g in groups.values() if len(g["names"]) > 1]
    rows.sort(key=lambda g: (-len(g["names"]), g["names"][0]))
    return rows


def weak_names(records=None, cwd=None, threshold=DEFAULT_WEAK):
    """Names whose best recorded score is below `threshold`. A prompt
    whose best version is still weak needs a rebuild, not another
    version of the same draft."""
    if records is None:
        records = load_library(cwd)
    best = {}
    versions = {}
    for r in records:
        name = r.get("name", "")
        if not name:
            continue
        score = r.get("score")
        if score is None:
            continue
        if name not in best or score > best[name]:
            best[name] = score
        versions[name] = versions.get(name, 0) + 1
    rows = [{"name": name, "best": best[name], "versions": versions[name]}
            for name in best if best[name] < threshold]
    rows.sort(key=lambda r: (r["best"], r["name"]))
    return rows


def untagged_names(records=None, cwd=None):
    """Names with no tag on any version — unfindable by tag search."""
    if records is None:
        records = load_library(cwd)
    tags = {}
    versions = {}
    for r in records:
        name = r.get("name", "")
        if not name:
            continue
        versions[name] = versions.get(name, 0) + 1
        for t in r.get("tags") or []:
            if t.strip():
                tags.setdefault(name, set()).add(t.strip())
    rows = [{"name": name, "versions": versions[name]}
            for name in versions if name not in tags]
    rows.sort(key=lambda r: r["name"])
    return rows


def never_improved_names(records=None, cwd=None):
    """Names with no version saved via `--improve` — the library holds
    the raw draft and nothing better."""
    if records is None:
        records = load_library(cwd)
    improved = set()
    versions = {}
    for r in records:
        name = r.get("name", "")
        if not name:
            continue
        versions[name] = versions.get(name, 0) + 1
        if r.get("enhanced"):
            improved.add(name)
    rows = [{"name": name, "versions": versions[name]}
            for name in versions if name not in improved]
    rows.sort(key=lambda r: r["name"])
    return rows


def audit_library(records=None, cwd=None, weak_threshold=DEFAULT_WEAK):
    """Audit the whole library. Empty library -> zeroed result with
    verdict "clean" is wrong, so the caller checks emptiness first;
    here an empty input simply reports no names and no issues."""
    if records is None:
        records = load_library(cwd)
    names = []
    for r in records:
        n = r.get("name", "")
        if n and n not in names:
            names.append(n)
    duplicates = find_duplicates(records)
    weak = weak_names(records, threshold=weak_threshold)
    untagged = untagged_names(records)
    never_improved = never_improved_names(records)
    issues = (len(duplicates) + len(weak) + len(untagged)
              + len(never_improved))
    return {
        "names": len(names),
        "versions": len(records),
        "duplicates": duplicates,
        "weak": weak,
        "untagged": untagged,
        "never_improved": never_improved,
        "issues": issues,
        "verdict": "clean" if issues == 0 else "needs attention",
    }


def audit_payload(result):
    """Machine-readable envelope: the audit result plus per-kind counts."""
    return {
        **result,
        "counts": {
            "duplicates": len(result["duplicates"]),
            "weak": len(result["weak"]),
            "untagged": len(result["untagged"]),
            "never_improved": len(result["never_improved"]),
        },
    }
