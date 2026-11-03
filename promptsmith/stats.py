"""Project stats — one global view over score history and the library.

`report` shows per-prompt trends; `stats` answers the whole-project
questions: how much have I tracked, what is my average, what is my best
and worst, and how big is the library. History records and library
entries are the single source of truth — nothing is re-scored here.

`stats --tags` scopes both halves with the shared any-match,
case-insensitive rule: the library is filtered version-by-version (a name
counts only with its tagged versions), and history is scoped by prompt
text — a logged run counts when its prompt text matches a saved version
carrying the tag. History records carry no tags of their own, so the
prompt-text match is the honest link between a run and a tag.
"""

from .history import load_history
from .library import filter_by_tags, load_library, summarize


def _short(prompt, limit=40):
    if prompt is None:
        return None
    return prompt[:limit] + ("…" if len(prompt) > limit else "")


def stats_payload(cwd=None, tags=None):
    """Aggregate history + library into one machine-readable dict.

    `tags` (a list) scopes both halves as described in the module
    docstring; blank/empty tags mean no filtering. When tags are given,
    the payload gains a "tags" key naming the scope; unscoped payloads
    keep the original three keys.
    """
    wanted = [t.strip() for t in (tags or []) if t.strip()]
    lib_records = load_library(cwd)
    if wanted:
        lib_records = filter_by_tags(lib_records, wanted)
        tagged_prompts = {r.get("prompt") for r in lib_records}
        records = [r for r in load_history(cwd)
                   if r.get("prompt") in tagged_prompts]
    else:
        records = load_history(cwd)
    lib_rows = summarize(lib_records, cwd)

    scores = [r["score"] for r in records if "score" in r]
    by_intent = {}
    for r in records:
        intent = r.get("intent")
        if intent is None:
            continue
        by_intent.setdefault(intent, []).append(r["score"])
    by_intent = {
        intent: {
            "runs": len(ss),
            "average": round(sum(ss) / len(ss), 1),
        }
        for intent, ss in sorted(by_intent.items())
    }

    best_rec = max(records, key=lambda r: r["score"]) if scores else None
    worst_rec = min(records, key=lambda r: r["score"]) if scores else None
    best_lib = lib_rows[0] if lib_rows else None

    history = {
        "runs": len(records),
        "prompts": len({r.get("prompt", "") for r in records}),
        "average": round(sum(scores) / len(scores), 1) if scores else None,
        "best": best_rec["score"] if best_rec else None,
        "best_prompt": _short(best_rec["prompt"]) if best_rec else None,
        "worst": worst_rec["score"] if worst_rec else None,
        "worst_prompt": _short(worst_rec["prompt"]) if worst_rec else None,
        "by_intent": by_intent,
    }
    library = {
        "names": len(lib_rows),
        "versions": sum(row["versions"] for row in lib_rows),
        "best": best_lib["best"] if best_lib else None,
        "best_name": best_lib["name"] if best_lib else None,
    }
    payload = {
        "history": history,
        "library": library,
        "has_data": bool(records or lib_rows),
    }
    if wanted:
        payload["tags"] = wanted
    return payload
