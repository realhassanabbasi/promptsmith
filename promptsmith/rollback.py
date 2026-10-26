"""Rollback — restore any saved library version as a new version.

The library keeps every version you save, but until now you could only
*read* old versions (`promptsmith library NAME`). A version you can't go
back to is half a feature: if a rewrite turns out worse, the good version
stays buried in history.

`promptsmith rollback NAME`            -> restores the previous version
`promptsmith rollback NAME --to 2`     -> restores version 2 specifically

The restored text becomes a NEW version (history is never rewritten), so
rolling back is always undoable — roll forward again with another
rollback. The restored prompt is scored fresh under the current rubric,
and the target version's tags carry over.
"""

from .check import keeper_text
from .library import entries_for, save_entry


def rollback_entry(name, version=None, cwd=None):
    """Restore one saved version of `name` as a new version.

    Returns a result dict: name, from_version (the restored version),
    to_version (the new version number), score, grade, restored text,
    and the target version's recorded score. Raises ValueError when
    there is nothing to roll back to.
    """
    versions = entries_for(name, cwd=cwd)
    if not versions:
        raise ValueError(f'No saved prompt named "{name}".')
    if version is None:
        if len(versions) < 2:
            raise ValueError(
                f'"{name}" has only one version — nothing to roll back to.')
        target = versions[-2]
    else:
        target = None
        for v in versions:
            if v["version"] == version:
                target = v
                break
        if target is None:
            raise ValueError(
                f'No version {version} for "{name}" '
                f"(has {len(versions)} version(s)).")
        if target is versions[-1]:
            raise ValueError(
                f'"{name}" is already at version {version} — '
                "nothing to roll back to.")
    keeper = keeper_text(target)
    if not keeper.strip():
        raise ValueError(
            f'Version {target["version"]} of "{name}" is empty — '
            "nothing to restore.")
    record = save_entry(name, keeper, tags=list(target.get("tags") or []),
                        cwd=cwd)
    return {
        "name": name,
        "from_version": target["version"],
        "to_version": record["version"],
        "score": record["score"],
        "grade": record["grade"],
        "restored": keeper,
        "target_score": target["score"],
    }
