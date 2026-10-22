"""Export the prompt library — shareable Markdown or machine-readable JSON.

The library lives in `.promptsmith/library.jsonl` (one JSON record per line,
see library.py). Export turns it into something you can share with a team,
paste into docs, or back up:

`promptsmith export`                  -> Markdown to stdout (whole library)
`promptsmith export NAME`             -> Markdown for one saved name
`promptsmith export --format json`    -> JSON instead of Markdown
`promptsmith export -o library.md`    -> write to a file instead of stdout
"""

import json
from datetime import datetime, timezone

from .library import entries_for, load_library


def _best_text(record):
    """The keeper text: enhanced version when saved with --improve, else prompt."""
    return record.get("enhanced") or record.get("prompt", "")


def export_payload(records=None, name=None):
    """Machine-readable export: metadata + entries. Pure data, no I/O."""
    if records is None:
        records = load_library()
    if name:
        records = entries_for(name, records)
        if not records:
            return None
    groups = {}
    for r in records:
        groups.setdefault(r.get("name", ""), []).append(r)
    prompts = []
    for pname, versions in sorted(groups.items()):
        versions = sorted(versions, key=lambda v: v.get("version", 0))
        scores = [v.get("score", 0) for v in versions]
        prompts.append({
            "name": pname,
            "versions": len(versions),
            "best": max(scores) if scores else 0,
            "entries": [
                {
                    "version": v.get("version"),
                    "score": v.get("score"),
                    "grade": v.get("grade"),
                    "saved": v.get("ts"),
                    "tags": v.get("tags") or [],
                    "prompt": v.get("prompt", ""),
                    "enhanced": v.get("enhanced"),
                }
                for v in versions
            ],
        })
    return {
        "exported": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool": "promptsmith",
        "prompts": prompts,
        "count": len(prompts),
    }


def export_json(records=None, name=None):
    """JSON string of the library export. None when the name is unknown."""
    payload = export_payload(records, name)
    if payload is None:
        return None
    return json.dumps(payload, indent=2, ensure_ascii=False)


def export_markdown(records=None, name=None):
    """Render the library as a shareable Markdown document.

    Returns None when `name` matches nothing. Empty library yields an
    honest one-line document, not an exception.
    """
    payload = export_payload(records, name)
    if payload is None:
        return None
    lines = ["# Prompt Library", ""]
    lines.append(f"_Exported {payload['exported'][:10]} with promptsmith._")
    lines.append("")
    if not payload["prompts"]:
        lines.append("No saved prompts yet — run "
                     "`promptsmith save NAME \"...\"` to add your first.")
        lines.append("")
        return "\n".join(lines)
    for p in payload["prompts"]:
        lines.append(f"## {p['name']} "
                     f"({p['versions']} version(s), best {p['best']}/100)")
        lines.append("")
        for e in p["entries"]:
            saved = (e.get("saved") or "")[:10]
            lines.append(f"### v{e['version']} — {e['score']}/100 "
                         f"({e['grade']}) — {saved}")
            lines.append("")
            lines.append(f"> {e['prompt']}")
            lines.append("")
            if e.get("enhanced"):
                lines.append("**Improved version:**")
                lines.append("")
                lines.append(f"> {e['enhanced']}")
                lines.append("")
            if e.get("tags"):
                lines.append(f"_Tags: {', '.join(e['tags'])}_")
                lines.append("")
    return "\n".join(lines)
