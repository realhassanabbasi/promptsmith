"""Command line interface. `python -m promptsmith --help` to start."""

import argparse
import sys

from . import __version__, enhance
from .classifier import load_default
from .scorer import grade, score_prompt
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


def cmd_score(args):
    total, breakdown, feedback = score_prompt(args.prompt)
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


def cmd_templates(args):
    if args.show:
        print(f"\n{bold(args.show)} — {TEMPLATES[args.show]['about']}")
        print(f"Placeholders: {', '.join(placeholders(args.show))}\n")
        vals = dict.fromkeys(placeholders(args.show), "")
        filled = {k: input(f"  {k}: ").strip() or f"{{{k}}}" for k in placeholders(args.show)}
        print(f"\n{bold('— Your prompt —')}\n")
        print(render(args.show, **filled))
        print()
    else:
        print(f"\n{bold('Available templates:')}\n")
        for n in names():
            print(f"  {cyan(n):24} {TEMPLATES[n]['about']}")
        print(f"\nUse: promptsmith templates --show <name>\n")


def cmd_interactive(_args):
    print(bold("\nLet's build your prompt together.\n"))
    goal = input("What do you want the AI to do? ").strip()
    if not goal:
        print("Nothing to enhance — bye!")
        return
    clf = load_default()
    intent, conf = clf.predict(goal)
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
    s.set_defaults(func=cmd_score)

    e = sub.add_parser("enhance", help="Rewrite a rough prompt into an engineered one")
    e.add_argument("prompt", help="The prompt text in quotes")
    e.add_argument("--save", metavar="FILE", help="Also save the result to a file")
    e.set_defaults(func=cmd_enhance)

    t = sub.add_parser("templates", help="Browse and fill ready-made prompt templates")
    t.add_argument("--show", metavar="NAME", choices=names(), help="Fill a template step by step")
    t.set_defaults(func=cmd_templates)

    i = sub.add_parser("interactive", help="Build a prompt through guided questions")
    i.set_defaults(func=cmd_interactive)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
