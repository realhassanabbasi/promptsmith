"""Folder doctor — check the `.promptsmith` data folder itself.

`audit` checks the *contents* of the library (duplicates, weak keepers).
`doctor` checks the *files* that hold those contents: `history.jsonl`
and `library.jsonl` are plain JSONL files a user can edit by hand, so
they can pick up damage — a half-written line from a killed process,
a stray edit that broke the JSON, a record missing its score, or a
random file dropped into the folder. `load_history()` and
`load_library()` silently skip bad lines, so the damage is invisible
until a trend or a version goes missing.

`promptsmith doctor`          -> per-file table: lines, valid, corrupt,
                                 incomplete; stray files listed
`promptsmith doctor --fix`    -> drops the bad lines (blank lines go
                                 too) after writing a `.bak` backup of
                                 each repaired file; healthy files and
                                 stray files are never touched
`promptsmith doctor --fail`   -> exit 1 when anything is still wrong
                                 (useful in CI, like `audit --fail`)
`--json`                      -> machine-readable results

A record is *complete* when it is a JSON object carrying every field
the loaders need: `prompt` + `score` for history, `name` + `prompt` +
`score` for the library, with `score` a number. Anything else that
parses as JSON but is not a complete record is *incomplete*; a line
that does not parse at all is *corrupt*. Blank lines are neither —
they are harmless, and `--fix` sweeps them out with the bad lines.
"""

import json
import os

DATA_DIR = ".promptsmith"

# file -> fields a record must carry to be usable by the loaders
KNOWN_FILES = {
    "history.jsonl": ("prompt", "score"),
    "library.jsonl": ("name", "prompt", "score"),
}


def doctor_dir(cwd=None):
    base = cwd or os.getcwd()
    return os.path.join(base, DATA_DIR)


def _is_complete(record, required):
    """A usable record: a JSON object with every required field present
    and a numeric score."""
    if not isinstance(record, dict):
        return False
    for field in required:
        if record.get(field) is None:
            return False
    score = record.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return False
    return True


def scan_file(name, cwd=None):
    """Inspect one data file line by line. Returns one row: how many
    lines it holds, how many are valid records, and where the bad
    ones are. A missing file is a row with exists False, not an error."""
    path = os.path.join(doctor_dir(cwd), name)
    row = {"file": name, "exists": False, "lines": 0, "valid": 0,
           "blank": 0, "corrupt": 0, "incomplete": 0,
           "corrupt_lines": [], "incomplete_lines": []}
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return row
    row["exists"] = True
    required = KNOWN_FILES[name]
    for number, raw in enumerate(lines, start=1):
        row["lines"] += 1
        if not raw.strip():
            row["blank"] += 1
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            row["corrupt"] += 1
            row["corrupt_lines"].append(number)
            continue
        if _is_complete(record, required):
            row["valid"] += 1
        else:
            row["incomplete"] += 1
            row["incomplete_lines"].append(number)
    return row


def doctor_report(cwd=None):
    """Check the whole folder. No folder at all -> verdict "empty"
    (the caller prints the honest one-liner); a folder with no bad
    lines and no stray files -> "healthy"; anything else ->
    "needs attention"."""
    folder = doctor_dir(cwd)
    if not os.path.isdir(folder):
        return {"folder_exists": False, "files": [], "stray": [],
                "issues": 0, "verdict": "empty"}
    files = [scan_file(name, cwd) for name in KNOWN_FILES]
    known = set(KNOWN_FILES) | {name + ".bak" for name in KNOWN_FILES}
    stray = sorted(f for f in os.listdir(folder)
                   if os.path.isfile(os.path.join(folder, f))
                   and f not in known)
    issues = sum(r["corrupt"] + r["incomplete"] for r in files) + len(stray)
    return {
        "folder_exists": True,
        "files": files,
        "stray": stray,
        "issues": issues,
        "verdict": "healthy" if issues == 0 else "needs attention",
    }


def doctor_fix(cwd=None):
    """Repair every damaged file: write a `.bak` backup of the original,
    then rewrite the file keeping only the valid records (blank lines
    go too). Healthy files are left untouched, stray files are never
    deleted — the report names them and the user decides. Returns what
    was fixed; a missing folder is a no-op with verdict "empty"."""
    report = doctor_report(cwd)
    if not report["folder_exists"]:
        return {"fixed": [], "issues_fixed": 0, "verdict": "empty"}
    fixed = []
    for row in report["files"]:
        bad = row["corrupt"] + row["incomplete"]
        if not row["exists"] or (bad == 0 and row["blank"] == 0):
            continue
        path = os.path.join(doctor_dir(cwd), row["file"])
        with open(path, encoding="utf-8") as f:
            original = f.read()
        backup = path + ".bak"
        with open(backup, "w", encoding="utf-8") as f:
            f.write(original)
        required = KNOWN_FILES[row["file"]]
        kept = []
        for raw in original.splitlines():
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if _is_complete(record, required):
                kept.append(raw)
        with open(path, "w", encoding="utf-8") as f:
            for line in kept:
                f.write(line + "\n")
        fixed.append({"file": row["file"], "dropped": bad,
                      "blank_dropped": row["blank"], "kept": len(kept),
                      "backup": os.path.basename(backup)})
    issues_fixed = sum(f["dropped"] for f in fixed)
    return {"fixed": fixed, "issues_fixed": issues_fixed,
            "verdict": "healthy" if issues_fixed else "needs attention"}


def doctor_payload(result):
    """Machine-readable envelope: the report plus per-kind counts."""
    counts = {"corrupt": 0, "incomplete": 0, "stray": len(result["stray"])}
    for row in result["files"]:
        counts["corrupt"] += row["corrupt"]
        counts["incomplete"] += row["incomplete"]
    return {**result, "counts": counts}
