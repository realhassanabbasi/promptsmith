"""Command line interface. `python -m promptsmith --help` to start."""

import argparse
import json
import sys

from . import __version__, enhance
from .check import check_library, check_name, check_payload
from .classifier import predict_intent
from .compare import compare_prompts
from .cost import MODEL_PRICES, cost_report
from .diff import diff_payload, diff_stats, render_diff
from .export import export_json, export_markdown
from .history import load_history, log_score, trend, verdict
from .improve import improve_prompt, what_improved
from .library import entries_for, library_path, load_library, save_entry, summarize
from .scorer import grade, score_prompt
from .skills import SKILL_NAME, render_skill, write_skill
from .templates import TEMPLATES, names, placeholders, render
from .tokens import estimate_tokens, token_report
from .cost import MODEL_PRICES, cost_report

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
    if args.diff:
        _print_change_block(args.prompt, result["prompt"])
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


def _print_change_block(before, after):
    """Show what changed, word by word, between two prompt texts."""
    stats = diff_stats(before, after)
    print(f"{bold('What changed:')} {stats['words_before']} → "
          f"{stats['words_after']} words "
          f"({green('+' + str(stats['added']))} / "
          f"{yellow('-' + str(stats['removed']))})\n")
    print(render_diff(before, after, color=sys.stdout.isatty()))
    print()


def cmd_diff(args):
    """Show the word-level changes between two prompt files."""
    a = _read_prompt_file(args.file_a)
    b = _read_prompt_file(args.file_b)
    if not a or not b:
        print("Both files need at least one prompt in them.", file=sys.stderr)
        sys.exit(1)
    if args.json:
        print(json.dumps({
            "a": args.file_a, "b": args.file_b,
            **diff_payload(a, b),
        }, indent=2))
        return
    print(f"\n{bold('Diff:')} {args.file_a}  →  {args.file_b}\n")
    _print_change_block(a, b)


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
    if args.diff:
        _print_change_block(a, b)
    print()


def cmd_improve(args):
    """Score, enhance, and re-score one prompt in a single step."""
    result = improve_prompt(args.prompt)
    if args.log:
        log_score(args.prompt, result["before"]["score"],
                  result["before"]["grade"], result["before"]["breakdown"],
                  intent=result["intent"])
        log_score(result["enhanced"], result["after"]["score"],
                  result["after"]["grade"], result["after"]["breakdown"],
                  intent=result["intent"])
    if args.json:
        print(json.dumps({
            "prompt": result["prompt"],
            "intent": result["intent"],
            "confidence": result["confidence"],
            "before": result["before"],
            "after": result["after"],
            "deltas": result["deltas"],
            "margin": result["margin"],
            "enhanced": result["enhanced"],
        }, indent=2))
        return

    before, after = result["before"], result["after"]
    print(f"\n{bold('Detected intent:')} {cyan(result['intent'])} "
          f"(confidence {result['confidence']})")
    print(f"{bold('Score:')} {yellow(str(before['score']))} "
          f"({before['grade']}) → {green(str(after['score']))} "
          f"({after['grade']})  (+{result['margin']})\n")

    print(f"  {'check':12} {'before':>6} {'after':>6} {'delta':>6}")
    for check, delta in result["deltas"].items():
        print(f"  {check:12} {before['breakdown'][check]:>6} "
              f"{after['breakdown'][check]:>6} {delta:>+6}")

    gains = what_improved(result["deltas"])
    if gains:
        print(f"\n{bold('What improved:')} "
              + ", ".join(f"{k} (+{v})" for k, v in gains))

    print(f"\n{bold('— Improved prompt (copy everything below) —')}\n")
    print(result["enhanced"])
    print()
    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            f.write(result["enhanced"])
        print(f"Saved to {args.save}\n")


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


def cmd_save(args):
    """Score (optionally improve) a prompt and save it to the library."""
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    record = save_entry(args.name, args.prompt, tags=tags,
                        enhance_it=args.improve)
    if args.json:
        print(json.dumps(record, indent=2))
        return
    ver = f"v{record['version']}"
    print(f"\n{bold('Saved:')} {cyan(args.name)} {ver} — "
          f"{record['score']}/100 ({record['grade']})")
    if record["enhanced"]:
        print(f"{bold('Improved version saved too:')} "
              f"{record['before_score']}/100 → {record['score']}/100.")
        short = record["enhanced"][:90]
        print(f"  \"{short}{'…' if len(record['enhanced']) > 90 else ''}\"")
    if record["tags"]:
        print(f"{bold('Tags:')} {', '.join(record['tags'])}")
    print(f"{bold('Library:')} {library_path()}\n")


def cmd_library(args):
    records = load_library()
    if not records:
        print("Library is empty — run `promptsmith save NAME \"...\"` "
              "to add your first prompt.")
        return
    if args.name:
        versions = entries_for(args.name, records)
        if not versions:
            print(f"No saved prompt named \"{args.name}\".")
            return
        if args.json:
            print(json.dumps(versions, indent=2))
            return
        print(f"\n{bold(args.name)} — {len(versions)} version(s)\n")
        print(f"  {'ver':>3} {'score':>5} {'grade':9} saved")
        for v in versions:
            ts = (v.get("ts") or "")[:10]
            print(f"  v{v['version']} {v['score']:>4}/100 "
                  f"({v['grade']:8}) {ts}")
            short = v["prompt"][:64] + ("…" if len(v["prompt"]) > 64 else "")
            print(f"       \"{short}\"")
            if v.get("enhanced"):
                e = v["enhanced"]
                short_e = e[:64] + ("…" if len(e) > 64 else "")
                print(f"       → improved: \"{short_e}\"")
        print()
        return
    rows = summarize(records)
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    arrows = {"improving": "▲", "slipping": "▼", "steady": "▬"}
    print(f"\n{bold('Prompt library')} — {len(records)} version(s), "
          f"{len(rows)} prompt(s) saved\n")
    print(f"  {'name':24} {'ver':>4} {'last':>4} {'best':>4} "
          f"{'Δ':>4}  tags")
    for r in rows:
        arrow = arrows["improving"] if r["delta"] > 0 else \
            arrows["slipping"] if r["delta"] < 0 else arrows["steady"]
        tags = ", ".join(r["tags"]) or "—"
        print(f"  {r['name'][:24]:24} {r['versions']:>4} {r['last']:>4} "
              f"{r['best']:>4} {r['delta']:>+4}{arrow}  {tags}")
    print()


def cmd_check(args):
    """Re-score the saved library against its own history; flag regressions."""
    records = load_library()
    if not records:
        print("Library is empty — run `promptsmith save NAME \"...\"` "
              "to add your first prompt.")
        return
    if args.name:
        result = check_name(args.name, records)
        if result is None:
            print(f"No saved prompt named \"{args.name}\".")
            return
        results = [result]
    else:
        results = check_library(records)
    if args.json:
        print(json.dumps(check_payload(results), indent=2))
    else:
        verdict_marks = {"regressed": "▼", "steady": "▬", "improved": "▲"}
        print(f"\n{bold('Prompt health')} — {len(results)} checked "
              f"(re-scored against recorded best)\n")
        print(f"  {'name':24} {'ver':>4} {'now':>4} {'best':>4} "
              f"{'Δ':>4}  verdict")
        for r in results:
            mark = verdict_marks[r["verdict"]]
            delta = f"{r['delta']:+d}{mark}"
            print(f"  {r['name'][:24]:24} {r['versions']:>4} "
                  f"{r['current']:>4} {r['best']:>4} {delta:>5}  "
                  f"{r['verdict']}")
        print()
        regressed = [r for r in results if r["verdict"] == "regressed"]
        if regressed:
            print(f"{bold(f'{len(regressed)} regressed')} — re-pass "
                  f"them before shipping: improve, verify, re-save.\n")
    if args.fail_on_regression and \
            any(r["verdict"] == "regressed" for r in results):
        sys.exit(1)


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


def cmd_tokens(args):
    report = token_report(args.prompt, args.model)
    if args.json:
        print(json.dumps(report, indent=2))
        return
    share_pct = report["context_share"] * 100
    print(f"\n{bold('Tokens:')} ~{report['tokens']} "
          f"({report['words']} words, {report['characters']} chars)\n")
    print(f"  Model: {report['model']} "
          f"(window {report['context_window']:,} tokens)")
    print(f"  Context used: {share_pct:.2f}%\n")
    print(f"  {yellow('Note:')} heuristic estimate (~4 chars/token).")
    print(f"  Use a real tokenizer for exact counts.\n")


def cmd_cost(args):
    if args.prices:
        print(f"\n{bold('Snapshot prices')} (USD per 1M tokens):\n")
        for name in sorted(MODEL_PRICES):
            p = MODEL_PRICES[name]
            print(f"  {name:<18} ${p['input']:<7.2f} in / ${p['output']:<7.2f} out"
                  f"  (checked {p['checked']})")
        print(f"\n  {yellow('Note:')} snapshot checked 2026-10-19 — verify with the")
        print(f"  provider before budgeting. Use --in-price/--out-price")
        print(f"  to pass your own rates.\n")
        return
    try:
        report = cost_report(args.prompt, model=args.model, calls=args.calls,
                             out_ratio=args.out_ratio, in_price=args.in_price,
                             out_price=args.out_price)
    except ValueError as e:
        print(f"\n{bold('Error:')} {e}\n")
        sys.exit(2)
    if args.json:
        print(json.dumps(report, indent=2))
        return
    rate_line = (f"${report['in_price_per_1m']:.2f} in / "
                 f"${report['out_price_per_1m']:.2f} out per 1M"
                 + (", custom rates" if report["prices_custom"]
                    else f", checked {report['prices_checked']}"))
    print(f"\n{bold('Cost:')} ~${report['cost_per_call_usd']:.6f} per call "
          f"({report['tokens']} in + {report['out_tokens_estimate']} out tokens)\n")
    print(f"  Model: {report['model']} ({rate_line})")
    print(f"  Output assumed: {report['out_ratio']}x input length "
          f"(--out-ratio to change)")
    print(f"  Budget: {report['calls']:,} calls ~ ${report['budget_usd']:.4f}\n")
    print(f"  {yellow('Note:')} tokens are the offline heuristic; prices are a")
    print(f"  2026-10-19 snapshot — verify with the provider before budgeting.\n")


def cmd_export(args):
    records = load_library()
    if args.format == "json":
        out = export_json(records, args.name)
    else:
        out = export_markdown(records, args.name)
    if out is None:
        print(f"No saved prompt named \"{args.name}\".")
        return
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print(f"Exported to {args.output}")
        return
    print(out)


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
    e.add_argument("--diff", action="store_true",
                   help="Also show what the rewrite changed, word by word")
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
    c.add_argument("--diff", action="store_true",
                   help="Also show the word-level changes between A and B")
    c.set_defaults(func=cmd_compare)

    d = sub.add_parser("diff", help="Show word-level changes between two prompts")
    d.add_argument("file_a", help="File holding prompt A (whole file = one prompt)")
    d.add_argument("file_b", help="File holding prompt B (whole file = one prompt)")
    d.add_argument("--json", action="store_true",
                   help="Print the diff as machine-readable JSON")
    d.set_defaults(func=cmd_diff)

    r = sub.add_parser("report", help="Show score history trends per prompt")
    r.add_argument("--json", action="store_true",
                   help="Print the trend table as machine-readable JSON")
    r.set_defaults(func=cmd_report)

    m = sub.add_parser("improve", help="Score, enhance and re-score one prompt")
    m.add_argument("prompt", help="The prompt text in quotes")
    m.add_argument("--json", action="store_true",
                   help="Print the result as machine-readable JSON")
    m.add_argument("--log", action="store_true",
                   help="Append the before and after runs to .promptsmith/history.jsonl")
    m.add_argument("--save", metavar="FILE",
                   help="Also save the improved prompt to a file")
    m.set_defaults(func=cmd_improve)

    sv = sub.add_parser("save", help="Save a prompt to the library with a version")
    sv.add_argument("name", help="Name to save it under (re-saving adds a version)")
    sv.add_argument("prompt", help="The prompt text in quotes")
    sv.add_argument("--improve", action="store_true",
                    help="Also save the enhanced version alongside")
    sv.add_argument("--tags", metavar="TAGS",
                    help="Comma-separated tags, e.g. --tags coding,debug")
    sv.add_argument("--json", action="store_true",
                    help="Print the saved record as machine-readable JSON")
    sv.set_defaults(func=cmd_save)

    lb = sub.add_parser("library", help="List saved prompts or show one name's history")
    lb.add_argument("name", nargs="?", default=None,
                    help="Show the version history of this name (omit to list all)")
    lb.add_argument("--json", action="store_true",
                    help="Print as machine-readable JSON")
    lb.set_defaults(func=cmd_library)

    ck = sub.add_parser("check", help="Re-score the saved library; flag regressions")
    ck.add_argument("name", nargs="?", default=None,
                    help="Check only this saved name (omit for the whole library)")
    ck.add_argument("--fail-on-regression", action="store_true",
                    help="Exit 1 if any prompt scores below its recorded best "
                         "(useful in CI)")
    ck.add_argument("--json", action="store_true",
                    help="Print as machine-readable JSON")
    ck.set_defaults(func=cmd_check)

    tk = sub.add_parser("tokens", help="Estimate token count and context usage")
    tk.add_argument("prompt", help="The prompt to measure")
    tk.add_argument("--model", default="gpt-4o",
                    help="Model for context-window share (default: gpt-4o)")
    tk.add_argument("--json", action="store_true",
                    help="Print as machine-readable JSON")
    tk.set_defaults(func=cmd_tokens)

    ct = sub.add_parser("cost", help="Estimate API cost per call and for N calls")
    ct.add_argument("prompt", help="The prompt to price")
    ct.add_argument("--model", default="gpt-4o",
                    help="Model price table (default: gpt-4o; see --prices)")
    ct.add_argument("--calls", type=int, default=1,
                    help="Number of calls for the budget estimate (default: 1)")
    ct.add_argument("--out-ratio", type=float, default=1.0,
                    help="Assumed output length as a multiple of input (default: 1.0)")
    ct.add_argument("--in-price", type=float, default=None,
                    help="Custom input price per 1M tokens (overrides snapshot)")
    ct.add_argument("--out-price", type=float, default=None,
                    help="Custom output price per 1M tokens (overrides snapshot)")
    ct.add_argument("--json", action="store_true",
                    help="Print as machine-readable JSON")
    ct.add_argument("--prices", action="store_true",
                    help="Print the snapshot price table and exit")
    ct.set_defaults(func=cmd_cost)

    ex = sub.add_parser("export", help="Export the prompt library to Markdown or JSON")
    ex.add_argument("name", nargs="?", default=None,
                    help="Export only this saved name (omit for the whole library)")
    ex.add_argument("--format", choices=["md", "json"], default="md",
                    help="Output format (default: md)")
    ex.add_argument("-o", "--output", default=None,
                    help="Write to FILE instead of stdout")
    ex.set_defaults(func=cmd_export)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
