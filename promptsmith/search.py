"""Search the saved prompt library — find a prompt by word or tag.

`promptsmith search QUERY`            -> every saved name whose name, prompt
                                         text, improved text, or tags contain
                                         the query (case-insensitive)
`promptsmith search QUERY --tags a,b` -> the same, but only names carrying
                                         at least one of the given tags

The library answers "which version is best?" — search answers "where did I
put that prompt?" One row per matching name, best score first, same order
as `library`. An empty query lists everything (the match fields still say
what each row contains).
"""

from .library import load_library


def search_library(query, tags=None, cwd=None):
    """Search saved names. Returns one row per matching name.

    Row: name, versions, last, best, delta, tags, matched (which fields the
    query hit: name / prompt / improved / tag). Tag filter narrows to names
    carrying at least one given tag. Empty library -> [].
    """
    q = (query or "").strip().lower()
    wanted_tags = [t.strip().lower() for t in (tags or []) if t.strip()]
    records = load_library(cwd)
    groups = {}
    for r in records:
        groups.setdefault(r.get("name", ""), []).append(r)
    rows = []
    for name, rs in groups.items():
        tags = []
        for r in rs:
            for t in r.get("tags") or []:
                if t not in tags:
                    tags.append(t)
        if wanted_tags and not any(t.lower() in wanted_tags for t in tags):
            continue
        matched = []
        if q in name.lower():
            matched.append("name")
        if any(q in (r.get("prompt") or "").lower() for r in rs):
            matched.append("prompt")
        if any(q in (r.get("enhanced") or "").lower() for r in rs):
            matched.append("improved")
        if any(q in t.lower() for t in tags):
            matched.append("tag")
        if q and not matched:
            continue
        scores = [r["score"] for r in rs]
        rows.append({
            "name": name,
            "versions": len(rs),
            "last": scores[-1],
            "best": max(scores),
            "delta": scores[-1] - scores[0],
            "tags": tags,
            "matched": matched,
            "saved": rs[-1].get("ts"),
        })
    rows.sort(key=lambda r: r["best"], reverse=True)
    return rows
