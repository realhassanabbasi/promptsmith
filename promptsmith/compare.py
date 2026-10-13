"""Head-to-head prompt comparison: did the rewrite actually help?

Scores two prompts on the same 5-check rubric, shows per-check deltas,
and names the winner — plus the loser's top fixes.
"""

from .scorer import grade, score_prompt


def compare_prompts(prompt_a, prompt_b):
    """Compare two prompts on the rubric.

    Returns a dict with each side's score/grade/breakdown/feedback, the
    per-check deltas (b minus a), the winner ('a', 'b' or 'tie'),
    and the margin in points.
    """
    total_a, breakdown_a, feedback_a = score_prompt(prompt_a)
    total_b, breakdown_b, feedback_b = score_prompt(prompt_b)
    deltas = {k: breakdown_b[k] - breakdown_a[k] for k in breakdown_a}

    if total_b > total_a:
        winner, margin = "b", total_b - total_a
    elif total_a > total_b:
        winner, margin = "a", total_a - total_b
    else:
        winner, margin = "tie", 0

    return {
        "a": {"prompt": prompt_a, "score": total_a, "grade": grade(total_a),
              "breakdown": breakdown_a, "feedback": feedback_a},
        "b": {"prompt": prompt_b, "score": total_b, "grade": grade(total_b),
              "breakdown": breakdown_b, "feedback": feedback_b},
        "deltas": deltas,
        "winner": winner,
        "margin": margin,
    }
