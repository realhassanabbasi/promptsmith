"""PromptSmith — turn rough prompts into engineered ones.

Zero dependencies, works offline. Built by Hassan Abbasi.
"""

from .check import check_library, check_name, check_payload
from .classifier import load_default, predict_intent
from .compare import compare_prompts
from .cost import cost_estimate, cost_report, known_models
from .delete import delete_entry
from .diff import diff_payload, diff_stats, render_diff, word_diff
from .enhancer import enhance
from .export import export_json, export_markdown, export_payload
from .importing import import_file, import_payload
from .init import init_project
from .history import load_history, log_score, sparkline, trend, verdict
from .improve import improve_prompt, what_improved
from .library import entries_for, load_library, save_entry, summarize
from .rename import rename_entry
from .rollback import rollback_entry
from .search import search_library
from .scorer import grade, score_prompt
from .stats import stats_payload
from .skills import render_skill, write_skill
from .templates import names, placeholders, render, TEMPLATES
from .tokens import context_share, estimate_tokens, token_report

__version__ = "1.22.0"
__all__ = ["load_default", "predict_intent", "check_library", "check_name", "check_payload", "enhance", "improve_prompt", "what_improved", "score_prompt", "grade", "compare_prompts", "cost_estimate", "cost_report", "known_models", "word_diff", "diff_stats", "render_diff", "diff_payload", "export_json", "export_markdown", "export_payload", "render", "names", "placeholders", "TEMPLATES", "render_skill", "write_skill", "log_score", "load_history", "trend", "sparkline", "verdict", "save_entry", "load_library", "entries_for", "summarize", "init_project", "estimate_tokens", "token_report", "context_share",
    "import_file", "import_payload", "stats_payload", "rollback_entry",
    "search_library", "delete_entry", "rename_entry"]
