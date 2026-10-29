"""Build assets/demo.svg from REAL promptsmith 1.21.0 output.
Run from the repo root:  python3 scripts/make_demo.py
Every line in the SVG was produced by the installed CLI."""
import subprocess, html, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = ["python3", "-m", "promptsmith"]
PROMPT = "write a story about a dog"

def run(*args):
    r = subprocess.run(EXE + list(args), capture_output=True, text=True, cwd=ROOT)
    return r.stdout.strip()

score_out = run("score", PROMPT)
enh_out = run("enhance", PROMPT)
enh_lines = [l for l in enh_out.splitlines() if l.strip()]

lines = [("$ promptsmith score \"write a story about a dog\"", "cmd"),
         ("", "blank")] + [(l, "dim") for l in score_out.splitlines() if l.strip()][:7]
lines += [("", "blank"), ("", "blank"),
          ("$ promptsmith enhance \"write a story about a dog\"", "cmd"),
          ("", "blank")] + [(l, "out") for l in enh_lines[:10]]

FONT = 14
LINE_H = 21
PAD_X = 24
TOP_PAD = 44          # below the window title bar
WIDTH = 780
HEIGHT = TOP_PAD + len(lines) * LINE_H + 26

COLORS = {"cmd": "#7dd3fc", "out": "#e5e7eb", "dim": "#9ca3af",
          "blank": "#e5e7eb"}

svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
    '<style>text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}</style>',
    f'<rect width="{WIDTH}" height="{HEIGHT}" rx="12" fill="#0d1117"/>',
    '<circle cx="24" cy="18" r="6" fill="#ff5f57"/>',
    '<circle cx="44" cy="18" r="6" fill="#febc2e"/>',
    '<circle cx="64" cy="18" r="6" fill="#28c840"/>',
    f'<text x="88" y="23" font-size="13" fill="#6b7280">promptsmith — live demo</text>',
]
for i, (text, cls) in enumerate(lines):
    y = TOP_PAD + i * LINE_H + 15
    t = html.escape(text)[:100]
    svg.append(f'<text x="{PAD_X}" y="{y}" font-size="{FONT}" fill="{COLORS[cls]}">{t}</text>')
svg.append("</svg>")

os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
out = os.path.join(ROOT, "assets", "demo.svg")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(svg))
print(f"wrote {out} ({WIDTH}x{HEIGHT}, {len(lines)} lines from real CLI output)")
