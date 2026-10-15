"""Score history — log scored runs and report trends over time.

Each `score` / `compare` run can append a record with `--log`. Records live in
`.promptsmith/history.jsonl` in the current working directory (one JSON object
per line), and `promptsmith report` turns them into per-prompt trend tables.
"""

import json
import os
from datetime import datetime, timezone

HISTORY_DIR = ".promptsmith"
HISTORY_FILE = "history.jsonl"
_BLOCKS = "▁▂▃▄▅▆▇"


def history_path(cwd=None):
    base = cwd or os.getcwd()
    return os.path.join(base, HISTORY_DIR, HISTORY_FILE)


def log_score(prompt, score, grade_name=None, breakdown=None, intent=None, cwd=None):
    """Append one scored run to the history file. Returns the record dict."""
    path = history_path(cwd)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prompt": prompt,
        "score": score,
        "grade": grade_name,
        "breakdown": breakdown or {},
        "intent": intent,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def load_history(cwd=None):
    """Read all records, oldest first. Missing file -> []. Bad lines skipped."""
    records = []
    try:
        with open(history_path(cwd), encoding="utf-8") as f:
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


def sparkline(scores):
    """Tiny unicode trend sparkline, e.g. [30, 50, 70] -> '▁▄▇'."""
    if not scores:
        return ""
    lo, hi = min(scores), max(scores)
    if hi == lo:
        return _BLOCKS[3] * len(scores)
    span = hi - lo
    return "".join(_BLOCKS[min(int((s - lo) / span * 6), 6)] for s in scores)


def trend(records):
    """Group records by prompt: runs, average, best, last, delta, sparkline."""
    groups = {}
    for r in records:
        groups.setdefault(r.get("prompt", ""), []).append(r)
    rows = []
    for prompt, rs in groups.items():
        scores = [r["score"] for r in rs]
        rows.append({
            "prompt": prompt,
            "runs": len(rs),
            "average": round(sum(scores) / len(scores), 1),
            "best": max(scores),
            "last": scores[-1],
            "delta": scores[-1] - scores[0],
            "spark": sparkline(scores),
        })
    rows.sort(key=lambda r: r["runs"], reverse=True)
    return rows


def verdict(row):
    """One-word read on a trend row."""
    if row["runs"] < 2:
        return "baseline"
    if row["delta"] > 0:
        return "improving"
    if row["delta"] < 0:
        return "slipping"
    return "steady"
