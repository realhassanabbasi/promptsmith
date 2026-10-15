"""PromptSmith — turn rough prompts into engineered ones.

Zero dependencies, works offline. Built by Hassan Abbasi.
"""

from .classifier import load_default, predict_intent
from .compare import compare_prompts
from .enhancer import enhance
from .history import load_history, log_score, sparkline, trend, verdict
from .scorer import grade, score_prompt
from .skills import render_skill, write_skill
from .templates import names, placeholders, render, TEMPLATES

__version__ = "1.5.0"
__all__ = ["load_default", "predict_intent", "enhance", "score_prompt", "grade", "compare_prompts", "render", "names", "placeholders", "TEMPLATES", "render_skill", "write_skill", "log_score", "load_history", "trend", "sparkline", "verdict"]
