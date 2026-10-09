"""PromptSmith — turn rough prompts into engineered ones.

Zero dependencies, works offline. Built by Hassan Abbasi.
"""

from .classifier import load_default
from .enhancer import enhance
from .scorer import grade, score_prompt
from .templates import names, placeholders, render, TEMPLATES

__version__ = "1.0.0"
__all__ = ["load_default", "enhance", "score_prompt", "grade", "render", "names", "placeholders", "TEMPLATES"]
