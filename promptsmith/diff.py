"""Word-level change diffs between two prompts. Zero dependencies, offline."""

import difflib
import re

# split into words while keeping every whitespace run, so a diff renders
# back into the original text exactly
_WORD_RE = re.compile(r"(\s+)")


def _tokens(text):
    return [t for t in _WORD_RE.split(text) if t]


def word_diff(a, b):
    """Return a list of (op, text) segments: op is keep, del or ins.

    Whitespace-only segments are never reported as changes.
    """
    tokens_a = _tokens(a)
    tokens_b = _tokens(b)
    # matching runs only against real words; whitespace re-attaches below
    def words_only(tokens):
        return [t for t in tokens if not t.isspace()]

    sm = difflib.SequenceMatcher(None, words_only(tokens_a),
                                 words_only(tokens_b), autojunk=False)

    def drain(tokens, start, stop, op):
        chunk = "".join(tokens[start:stop])
        if chunk:
            segs.append((op, chunk))

    # map word indices back to full-token ranges
    def word_ranges(tokens):
        ranges, i = [], 0
        while i < len(tokens):
            if tokens[i].isspace():
                i += 1
                continue
            j = i
            i += 1
            while i < len(tokens) and tokens[i].isspace():
                i += 1
            ranges.append((j, i))
        return ranges

    # walk both token streams, carrying whitespace along with its segment
    segs = []
    ra, rb = word_ranges(tokens_a), word_ranges(tokens_b)
    for tag, lo_a, hi_a, lo_b, hi_b in sm.get_opcodes():
        if tag == "equal":
            drain(tokens_a, ra[lo_a][0], ra[hi_a - 1][1], "keep")
        elif tag == "delete":
            drain(tokens_a, ra[lo_a][0], ra[hi_a - 1][1], "del")
        elif tag == "insert":
            drain(tokens_b, rb[lo_b][0], rb[hi_b - 1][1], "ins")
        else:  # replace: deletion then insertion, in text order
            drain(tokens_a, ra[lo_a][0], ra[hi_a - 1][1], "del")
            drain(tokens_b, rb[lo_b][0], rb[hi_b - 1][1], "ins")

    # merge neighbours with the same op for cleaner output
    merged = []
    for op, text in segs:
        if merged and merged[-1][0] == op:
            merged[-1][1] += text
        else:
            merged.append([op, text])
    return [(op, text) for op, text in merged]


def diff_stats(a, b):
    """Count the changed words between two prompts."""
    added = removed = kept = 0
    for op, text in word_diff(a, b):
        words = [t for t in _tokens(text) if not t.isspace()]
        if op == "ins":
            added += len(words)
        elif op == "del":
            removed += len(words)
        else:
            kept += len(words)
    return {
        "words_before": kept + removed,
        "words_after": kept + added,
        "added": added,
        "removed": removed,
        "unchanged": kept,
    }


def render_diff(a, b, color=True):
    """Render the word diff as plain text.

    Removed words are wrapped in -dashes-, added words in +pluses+
    (ANSI red/green when color is true).
    """
    red = "\033[31m" if color else ""
    green = "\033[32m" if color else ""
    reset = "\033[0m" if color else ""
    parts = []
    for op, text in word_diff(a, b):
        if op == "keep":
            parts.append(text)
            continue
        marker = "-" if op == "del" else "+"
        col = red if op == "del" else green
        if "\n" in text:
            # block change: one marked line per text line
            for line in text.split("\n"):
                if line.strip():
                    parts.append(f"\n{col}{marker} {line.strip()}{reset}")
            parts.append("\n")
        else:
            parts.append(f"{col}{marker}{text.strip()}{marker}{reset} ")
    return "".join(parts).strip()


def diff_payload(a, b):
    """Machine-readable form of the diff for --json output."""
    return {
        "stats": diff_stats(a, b),
        "segments": [{"op": op, "text": text} for op, text in word_diff(a, b)],
    }
