"""Command line interface. `python -m promptsmith --help` to start."""

import argparse
import json
import sys

from . import __version__, enhance
from .classifier import predict_intent
from .compare import compare_prompts
from .history import load_history, log_score, trend, verdict
from .scorer import grade, score_prompt
from .skills import SKILL_NAME, render_skill, write_skill
from .templates import TEMPLATES, names, placeholders, render

# tiny color helpers, no dependencies needed
def _c(code, text):
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(t): return _c("1", t)
def green(t): return _c("32", t)
def yellow(t): return _c("33", t)
def cyan(t): return _c("36", t)


def _score_payload(prompt):
    total, breakdown, feedback = score_prompt(prompt)
    return {
        "prompt": prompt,
        "score": total,
        "grade": grade(total),
        "breakdown": breakdown,
        "feedback": feedback,
    }


def cmd_score(args):
    payload = _score_payload(args.prompt)
    if args.log:
        log_score(payload["prompt"], payload["score"],
                  payload["grade"], payload["breakdown"])
    if args.json:
        print(json.dumps(payload, indent=2))
        return
    total, breakdown, feedback = (payload["score"], payload["breakdown"],
                                  payload["feedback"])
    print(f"\n{bold('Prompt score:')} {total}/100 ({grade(total)})\n")
    for k, v in breakdown.items():
        bar = "█" * (v // 2) + "░" * (10 - v // 2)
        print(f"  {k:12} {bar} {v:>3}/20")
    if feedback:
        print(f"\n{bold('How to improve:')}")
        for f in feedback:
            print(f"  • {f}")
    print()


def cmd_enhance(args):
    result = enhance(args.prompt)
    if args.json:
        print(json.dumps({
            "prompt": args.prompt,
            "intent": result["intent"],
            "confidence": round(result["confidence"], 3),
            "before": result["before"],
            "after": result["after"],
            "gain": result["gain"],
            "enhanced": result["prompt"],
        }, indent=2))
        return
    print(f"\n{bold('Detected intent:')} {cyan(result['intent'])} "
          f"(confidence {result['confidence']})")
    print(f"{bold('Score:')} {yellow(str(result['before']))} → "
          f"{green(str(result['after']))}  (+{result['gain']})\n")
    print(bold("— Enhanced prompt (copy everything below) —") + "\n")
    print(result["prompt"])
    print()
    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            f.write(result["prompt"])
        print(f"Saved to {args.save}\n")


def cmd_batch(args):
    """Score every prompt in a file (one per line), optionally enhancing each."""
    try:
        with open(args.file, encoding="utf-8") as f:
            prompts = [line.strip() for line in f if line.strip()]
    except OSError as e:
        print(f"Error: can't read {args.file}: {e}", file=sys.stderr)
        sys.exit(1)
    if not prompts:
        print("No prompts found — the file needs one prompt per line.")
        return

    results = []
    for text in prompts:
        entry = _score_payload(text)
        if args.enhance:
            r = enhance(text)
            entry.update({
                "intent": r["intent"],
                "after": r["after"],
                "gain": r["gain"],
                "enhanced": r["prompt"],
            })
        results.append(entry)

    avg = sum(e["score"] for e in results) / len(results)
    worst = min(results, key=lambda e: e["score"])
    summary = {
        "count": len(results),
        "average_score": round(avg, 1),
        "weakest_prompt": worst["prompt"],
        "weakest_score": worst["score"],
    }
    if args.enhance:
        summary["average_after"] = round(
            sum(e["after"] for e in results) / len(results), 1)
        summary["average_gain"] = round(
            sum(e["gain"] for e in results) / len(results), 1)

    if args.json:
        print(json.dumps({"prompts": results, "summary": summary}, indent=2))
        return

    print(f"\n{bold(f'Scored {len(results)} prompts from {args.file}')}\n")
    for i, e in enumerate(results, 1):
        short = e["prompt"][:52] + ("…" if len(e["prompt"]) > 52 else "")
        extra = f"  → {e['after']} ({e['gain']:+d})" if args.enhance else ""
        print(f"  {i:>2}. {e['score']:>3}/100 ({e['grade']:8}) {short}{extra}")
    print(f"\n{bold('Average:')} {avg:.1f}/100")
    print(f"{bold('Weakest:')} \"{worst['prompt'][:60]}\" ({worst['score']}/100)")
    if args.enhance:
        print(f"{bold('Enhanced average:')} {summary['average_after']}/100"
              f"  (avg gain {summary['average_gain']:+.0f})")
        out = args.file + ".enhanced.md"
        with open(out, "w", encoding="utf-8") as f:
            for i, e in enumerate(results, 1):
                f.write(f"## {i}. {e['prompt']}\n\n{e['enhanced']}\n\n---\n\n")
        print(f"{bold('Enhanced prompts saved to:')} {out}")
    print()


def _read_prompt_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError as e:
        print(f"Error: can't read {path}: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_compare(args):
    """Score two prompt files against each other, check by check."""
    a = _read_prompt_file(args.file_a)
    b = _read_prompt_file(args.file_b)
    if not a or not b:
        print("Both files need at least one prompt in them.", file=sys.stderr)
        sys.exit(1)
    result = compare_prompts(a, b)
    if args.log:
        log_score(a, result["a"]["score"], result["a"]["grade"],
                  result["a"]["breakdown"])
        log_score(b, result["b"]["score"], result["b"]["grade"],
                  result["b"]["breakdown"])
    if args.json:
        print(json.dumps(result, indent=2))
        return

    ra, rb = result["a"], result["b"]
    print(f"\n{bold('Compare:')} {args.file_a}  vs  {args.file_b}\n")
    for name, text, side in (("A", a, ra), ("B", b, rb)):
        short = text[:54] + ("…" if len(text) > 54 else "")
        print(f"  {name}: {side['score']:>3}/100 ({side['grade']:9})  \"{short}\"")
    if result["winner"] == "tie":
        print(f"\n{bold('Verdict:')} dead heat — same score.")
    else:
        print(f"\n{bold('Verdict:')} {green(result['winner'].upper())} wins "
              f"by {result['margin']} points.")

    print(f"\n  {'check':12} {'A':>4} {'B':>4} {'delta':>6}")
    for check, delta in result["deltas"].items():
        print(f"  {check:12} {ra['breakdown'][check]:>4} "
              f"{rb['breakdown'][check]:>4} {delta:>+5}")

    losers = {"a": ("B", rb), "b": ("A", ra)}
    if result["winner"] in losers:
        name, side = losers[result["winner"]]
        if side["feedback"]:
            print(f"\n{bold(f'Fix {name} first:')}")
            for f in side["feedback"]:
                print(f"  • {f}")
    else:
        for name, side in (("A", ra), ("B", rb)):
            if side["feedback"]:
                print(f"\n{bold(f'{name} could still fix:')}")
                for f in side["feedback"]:
                    print(f"  • {f}")
    print()


def cmd_report(args):
    records = load_history()
    if not records:
        print("No score history yet — run `promptsmith score \"...\" --log` "
              "to start tracking.")
        return
    rows = trend(records)
    if args.json:
        print(json.dumps(rows, indent=2))
        return

    arrows = {"improving": "▲", "slipping": "▼",
              "steady": "▬", "baseline": "—"}
    print(f"\n{bold('Score history')} — {len(records)} runs, "
          f"{len(rows)} prompt(s) tracked\n")
    print(f"  {'prompt':42} {'runs':>4} {'avg':>5} {'best':>4} "
          f"{'last':>4} {'Δ':>4}  {'trend':6}  verdict")
    for r in rows:
        short = r["prompt"][:40] + ("…" if len(r["prompt"]) > 40 else "")
        v = verdict(r)
        print(f"  {short:42} {r['runs']:>4} {r['average']:>5.1f} "
              f"{r['best']:>4} {r['last']:>4} {r['delta']:>+4}  "
              f"{r['spark']:6}  {v} {arrows[v]}")
    print()


def cmd_templates(args):
    if args.show:
        print(f"\n{bold(args.show)} — {TEMPLATES[args.show]['about']}")
        print(f"Placeholders: {', '.join(placeholders(args.show))}\n")
        vals = dict.fromkeys(placeholders(args.show), "")
        filled = {k: input(f"  {k}: ").strip() or f"{{{k}}}" for k in placeholders(args.show)}
        print(f"\n{bold('— Your prompt —')}\n")
        print(render(args.show, **filled))
        print()


def cmd_skill(args):
    if args.out:
        path = write_skill(args.out)
        print(f"\n{bold('Skill written to:')} {path}\n")
        print("Install for Claude Code: copy it under ~/.claude/skills/")
        print("It also works with Codex and Cursor's skill folders.\n")
    else:
        print(render_skill())


def cmd_interactive(_args):
    print(bold("\nLet's build your prompt together.\n"))
    goal = input("What do you want the AI to do? ").strip()
    if not goal:
        print("Nothing to enhance — bye!")
        return
    intent, conf = predict_intent(goal)
    print(f"\nSounds like a {cyan(intent)} task (confidence {conf}).")
    ctx = input("Any background or context? (press Enter to skip) ").strip()
    fmt = input("How should the answer look? (bullets/table/code/steps, Enter=auto) ").strip()
    raw = goal + (f" Context: {ctx}." if ctx else "") + (f" Answer as {fmt}." if fmt else "")
    result = enhance(raw, intent=intent, confidence=conf)
    print(f"\n{bold('Score:')} {yellow(str(result['before']))} → {green(str(result['after']))}\n")
    print(bold("— Your engineered prompt —") + "\n")
    print(result["prompt"])
    print()


def build_parser():
    p = argparse.ArgumentParser(
        prog="promptsmith",
        description="Turn rough prompts into engineered ones. Offline, zero dependencies.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("score", help="Score a prompt 0-100 with feedback")
    s.add_argument("prompt", help="The prompt text in quotes")
    s.add_argument("--json", action="store_true",
                   help="Print the score as machine-readable JSON")
    s.add_argument("--log", action="store_true",
                   help="Append this run to .promptsmith/history.jsonl")
    s.set_defaults(func=cmd_score)

    e = sub.add_parser("enhance", help="Rewrite a rough prompt into an engineered one")
    e.add_argument("prompt", help="The prompt text in quotes")
    e.add_argument("--save", metavar="FILE", help="Also save the result to a file")
    e.add_argument("--json", action="store_true",
                   help="Print the result as machine-readable JSON")
    e.set_defaults(func=cmd_enhance)

    b = sub.add_parser("batch", help="Score every prompt in a file (one per line)")
    b.add_argument("file", help="Text file with one prompt per line")
    b.add_argument("--json", action="store_true",
                   help="Print results as machine-readable JSON")
    b.add_argument("--enhance", action="store_true",
                   help="Also enhance each prompt; saves FILE.enhanced.md")
    b.set_defaults(func=cmd_batch)

    t = sub.add_parser("templates", help="Browse and fill ready-made prompt templates")
    t.add_argument("--show", metavar="NAME", choices=names(), help="Fill a template step by step")
    t.set_defaults(func=cmd_templates)

    i = sub.add_parser("interactive", help="Build a prompt through guided questions")
    i.set_defaults(func=cmd_interactive)

    k = sub.add_parser("skill", help="Generate an installable agent skill (SKILL.md)")
    k.add_argument("--out", metavar="DIR",
                   help="Write DIR/promptsmith/SKILL.md instead of printing")
    k.set_defaults(func=cmd_skill)

    c = sub.add_parser("compare", help="Compare two prompt files head-to-head")
    c.add_argument("file_a", help="File holding prompt A (whole file = one prompt)")
    c.add_argument("file_b", help="File holding prompt B (whole file = one prompt)")
    c.add_argument("--json", action="store_true",
                   help="Print the comparison as machine-readable JSON")
    c.add_argument("--log", action="store_true",
                   help="Append both runs to .promptsmith/history.jsonl")
    c.set_defaults(func=cmd_compare)

    r = sub.add_parser("report", help="Show score history trends per prompt")
    r.add_argument("--json", action="store_true",
                   help="Print the trend table as machine-readable JSON")
    r.set_defaults(func=cmd_report)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
