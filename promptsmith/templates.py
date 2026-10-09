"""Ready-made prompt templates. Fill the {placeholders}, copy, paste."""

TEMPLATES = {
    "debug-code": {
        "about": "Get help fixing broken code",
        "template": (
            "You are a patient debugging expert. Diagnose first, then fix.\n\n"
            "My code: {language}\n{code}\n\n"
            "Error message: {error}\n\n"
            "What I already tried: {tried}\n\n"
            "Give: 1) the likely cause, 2) how to confirm it, 3) the fixed code.\n"
            "Guardrails: explain the fix in plain words; don't just paste code."
        ),
    },
    "explain-concept": {
        "about": "Understand a hard idea fast",
        "template": (
            "You are a teacher who explains hard ideas with simple words.\n\n"
            "Explain: {concept}\n"
            "My level: {level}\n\n"
            "Use short paragraphs, one everyday example, and end with a one-line recap.\n"
            "Guardrails: avoid jargon; define any technical word you must use."
        ),
    },
    "learn-vocabulary": {
        "about": "Learn a field's key terms (great before prompting AI about it)",
        "template": (
            "You are a friendly tutor.\n\n"
            "Teach me the {count} most important terms of {field}.\n"
            "My level: {level}\n\n"
            "For each term: definition in plain words, then a real-life example.\n"
            "Order them from basic to advanced.\n"
            "End with 3 practice questions to test me."
        ),
    },
    "code-from-scratch": {
        "about": "Generate clean code for a task",
        "template": (
            "You are a senior software engineer who writes clean, well-commented code.\n\n"
            "Task: {task}\n"
            "Language: {language}\n"
            "Constraints: {constraints}\n\n"
            "Provide the code first, then a short explanation of how it works.\n"
            "Guardrails: handle edge cases; comment the tricky parts."
        ),
    },
    "analyze-data": {
        "about": "Get real insight from data or text",
        "template": (
            "You are a sharp analyst.\n\n"
            "Analyze this: {data}\n"
            "Question I want answered: {question}\n\n"
            "Use bullet points for findings and end with a clear recommendation.\n"
            "Guardrails: separate facts from interpretation; say what the data can't tell us."
        ),
    },
    "write-better": {
        "about": "Draft anything in your voice",
        "template": (
            "You are a professional writer with a clear, natural voice.\n\n"
            "Write: {what}\n"
            "Tone: {tone}\n"
            "Length: {length}\n\n"
            "Keep paragraphs short. No filler phrases.\n"
            "Give me 2 versions to choose from."
        ),
    },
    "study-plan": {
        "about": "A realistic plan for exams or learning",
        "template": (
            "You are a practical planner.\n\n"
            "Goal: {goal}\n"
            "Deadline: {deadline}\n"
            "Hours I can study per day: {hours}\n\n"
            "Present as numbered steps with rough time estimates.\n"
            "Put the hardest topics when my energy is highest.\n"
            "Guardrails: keep it realistic — I have a life outside studying."
        ),
    },
    "compare-options": {
        "about": "Make a decision between options",
        "template": (
            "You are a sharp analyst.\n\n"
            "Help me choose between: {options}\n"
            "My situation: {situation}\n"
            "What matters most to me: {priorities}\n\n"
            "Compare in a table, then give a clear recommendation with reasons.\n"
            "Guardrails: be honest about trade-offs; don't just pick the popular one."
        ),
    },
}


def names():
    return sorted(TEMPLATES.keys())


def render(name, **values):
    """Fill a template's {placeholders}. Missing ones stay visible as {name}."""
    if name not in TEMPLATES:
        raise KeyError(f"unknown template: {name}. Try: {', '.join(names())}")
    tpl = TEMPLATES[name]["template"]

    class KeepMissing(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    return tpl.format_map(KeepMissing(values))


def placeholders(name):
    import re
    return re.findall(r"{(\w+)}", TEMPLATES[name]["template"])
