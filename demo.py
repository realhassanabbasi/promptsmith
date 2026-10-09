"""End-to-end demo. Run: python demo.py"""

from promptsmith import enhance
from promptsmith.scorer import grade, score_prompt

EXAMPLES = [
    "help me with python",
    "write email to professor",
    "explain blockchain",
]

print("=" * 64)
print("  PromptSmith demo — rough prompts in, engineered prompts out")
print("=" * 64)

for raw in EXAMPLES:
    before, _, tips = score_prompt(raw)
    r = enhance(raw)
    print(f"\n>>> {raw!r}")
    print(f"    intent: {r['intent']} (confidence {r['confidence']})")
    print(f"    score:  {before} ({grade(before)}) -> {r['after']} ({grade(r['after'])})  +{r['gain']}")
    print("    tip:    " + (tips[0] if tips else "already solid"))
    print("    --- enhanced (first 3 lines) ---")
    for line in r["prompt"].splitlines()[:3]:
        print("    " + line)
    print("    ...")

print("\n" + "=" * 64)
print("  Try it yourself:  python -m promptsmith enhance \"your prompt\"")
print("                    python -m promptsmith interactive")
print("=" * 64)
