"""Run: python -m unittest discover -s tests -v"""

import contextlib
import io
import json
import os
import tempfile
import unittest

from promptsmith.classifier import load_default
from promptsmith.compare import compare_prompts
from promptsmith.enhancer import enhance, ROLES
from promptsmith.scorer import grade, score_prompt
from promptsmith.skills import render_skill, write_skill
from promptsmith.templates import names, placeholders, render


class TestClassifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clf = load_default()

    def test_code_intent(self):
        intent, conf = self.clf.predict("write a python function to sort numbers")
        self.assertEqual(intent, "code")
        self.assertGreaterEqual(conf, 0.5)

    def test_learn_intent(self):
        intent, _ = self.clf.predict("teach me the key terms of photography")
        self.assertEqual(intent, "learn")

    def test_explain_intent(self):
        intent, _ = self.clf.predict("explain how neural networks work simply")
        self.assertEqual(intent, "explain")

    def test_debug_intent(self):
        intent, _ = self.clf.predict("my program crashes, help me find the bug")
        self.assertEqual(intent, "debug")

    def test_confidence_range(self):
        _, conf = self.clf.predict("anything at all here")
        self.assertGreaterEqual(conf, 0)
        self.assertLessEqual(conf, 1)

    def test_chat_intent(self):
        intent, conf = self.clf.predict("translate good morning to urdu")
        self.assertEqual(intent, "chat")
        self.assertGreaterEqual(conf, 0.5)

    def test_learn_disambiguation(self):
        # "how do i learn X" used to misfire as debug; it must read as learn
        intent, _ = self.clf.predict("how do i learn french verbs fast")
        self.assertEqual(intent, "learn")

    def test_low_confidence_falls_back_to_chat(self):
        from promptsmith.classifier import predict_intent
        intent, conf = predict_intent("zxqw asdf jklm qwerty")
        self.assertLess(conf, 0.35)
        self.assertEqual(intent, "chat")

    def test_holdout_accuracy(self):
        # last example per intent held out, retrain, most must still classify
        from promptsmith.classifier import NaiveBayesIntent
        import json as _json, os as _os
        path = _os.path.join(_os.path.dirname(load_default.__code__.co_filename),
                             "data", "training_prompts.json")
        with open(path, encoding="utf-8") as _f:
            data = _json.load(_f)["intents"]
        clf = NaiveBayesIntent()
        clf.train({k: v[:-1] for k, v in data.items()})
        ok = sum(1 for k, v in data.items() if clf.predict(v[-1])[0] == k)
        self.assertGreaterEqual(ok / len(data), 0.7)


class TestScorer(unittest.TestCase):
    def test_weak_prompt_scores_low(self):
        total, _, _ = score_prompt("help me")
        self.assertLess(total, 50)

    def test_strong_prompt_scores_high(self):
        total, _, _ = score_prompt(
            "Write a cover letter for a data science internship. "
            "Keep it under 250 words in 3 short paragraphs. "
            "Tone: confident but humble. Do not use buzzwords."
        )
        self.assertGreaterEqual(total, 60)

    def test_breakdown_sums(self):
        total, breakdown, _ = score_prompt("explain recursion with an example")
        self.assertEqual(total, sum(breakdown.values()))
        self.assertEqual(set(breakdown), {"clarity", "context", "specificity", "format", "guardrails"})

    def test_grades(self):
        self.assertEqual(grade(90), "excellent")
        self.assertEqual(grade(75), "good")
        self.assertEqual(grade(55), "okay")
        self.assertEqual(grade(20), "weak")


class TestEnhancer(unittest.TestCase):
    def test_enhance_improves_score(self):
        r = enhance("help me with python")
        self.assertGreater(r["after"], r["before"])
        self.assertIn("Guardrails", r["prompt"])
        self.assertIn("Output format", r["prompt"])

    def test_enhance_detects_intent(self):
        r = enhance("teach me photography terms")
        self.assertEqual(r["intent"], "learn")

    def test_enhance_falls_back_on_shaky_intent(self):
        r = enhance("zxqw asdf jklm qwerty")
        self.assertEqual(r["intent"], "chat")
        self.assertLess(r["confidence"], 0.35)


class TestTemplates(unittest.TestCase):
    def test_all_render(self):
        for n in names():
            out = render(n)
            self.assertIn("{", out)  # unfilled placeholders stay visible

    def test_fill_values(self):
        out = render("explain-concept", concept="recursion", level="beginner")
        self.assertIn("recursion", out)
        self.assertNotIn("{concept}", out)

    def test_unknown_raises(self):
        with self.assertRaises(KeyError):
            render("nope-not-real")

    def test_placeholders_found(self):
        self.assertIn("concept", placeholders("explain-concept"))


class TestCLI(unittest.TestCase):
    def _run(self, argv):
        from promptsmith.cli import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(argv)
        return buf.getvalue()

    def test_score_json_parses(self):
        out = self._run(["score", "help me with python", "--json"])
        data = json.loads(out)
        self.assertEqual(set(data),
                         {"prompt", "score", "grade", "breakdown", "feedback"})
        self.assertLess(data["score"], 50)
        self.assertEqual(data["breakdown"]["clarity"] +
                         data["breakdown"]["context"] +
                         data["breakdown"]["specificity"] +
                         data["breakdown"]["format"] +
                         data["breakdown"]["guardrails"], data["score"])

    def test_enhance_json_parses(self):
        out = self._run(["enhance", "help me with python", "--json"])
        data = json.loads(out)
        self.assertEqual(set(data), {"prompt", "intent", "confidence",
                                     "before", "after", "gain", "enhanced"})
        self.assertGreater(data["after"], data["before"])
        self.assertEqual(data["gain"], data["after"] - data["before"])

    def test_batch_scores_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                         delete=False) as f:
            f.write("help me with python\n\n"
                    "Write a cover letter for a data science internship. "
                    "Keep it under 250 words. Tone: confident.\n")
            path = f.name
        try:
            out = self._run(["batch", path, "--json"])
            data = json.loads(out)
            self.assertEqual(len(data["prompts"]), 2)  # blank line skipped
            self.assertEqual(data["summary"]["count"], 2)
            self.assertLess(data["prompts"][0]["score"],
                            data["prompts"][1]["score"])
        finally:
            os.unlink(path)

    def test_batch_enhance_writes_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                         delete=False) as f:
            f.write("help me with python\nteach me photography terms\n")
            path = f.name
        try:
            self._run(["batch", path, "--enhance"])
            out_path = path + ".enhanced.md"
            self.assertTrue(os.path.exists(out_path))
            with open(out_path) as f:
                content = f.read()
            self.assertIn("## 1.", content)
            self.assertIn("## 2.", content)
            self.assertIn("Guardrails", content)
        finally:
            os.unlink(path)
            if os.path.exists(path + ".enhanced.md"):
                os.unlink(path + ".enhanced.md")


class TestPackaging(unittest.TestCase):
    """Regression test: the intent training data must ship inside the
    installed package, or `promptsmith enhance` crashes with
    FileNotFoundError for anyone installing via pip (found 2026-10-11)."""

    def test_pyproject_declares_package_data(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pyproject = os.path.join(root, "pyproject.toml")
        with open(pyproject, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("[tool.setuptools.package-data]", content)
        self.assertIn("data/*.json", content)

    def test_training_data_sits_inside_package(self):
        import promptsmith
        data_path = os.path.join(os.path.dirname(promptsmith.__file__),
                                 "data", "training_prompts.json")
        self.assertTrue(os.path.isfile(data_path),
                        f"missing from package: {data_path}")
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("intents", data)
        self.assertGreater(len(data["intents"]), 0)

    def test_end_to_end_enhance(self):
        # the exact path that crashed on pip installs before the fix
        result = enhance("write a story about a dog")
        self.assertGreater(result["after"], result["before"])


class TestSkill(unittest.TestCase):
    def test_frontmatter(self):
        md = render_skill()
        self.assertTrue(md.startswith("---\n"))
        self.assertIn("name: promptsmith", md)
        self.assertIn("description:", md)

    def test_covers_all_five_checks(self):
        md = render_skill()
        for check in ["clarity", "context", "specificity", "format", "guardrails"]:
            self.assertIn(check, md, f"skill missing check: {check}")
        self.assertIn("20 points each", md)

    def test_covers_all_intent_roles(self):
        md = render_skill()
        self.assertEqual(len(ROLES), 8)
        for intent in ROLES:
            self.assertIn(f"### {intent}", md, f"skill missing role: {intent}")

    def test_example_is_real_enhance_output(self):
        # the worked example must come from the real pipeline, gain included
        from promptsmith.skills import EXAMPLE_ROUGH
        md = render_skill()
        result = enhance(EXAMPLE_ROUGH)
        self.assertGreater(result["after"], result["before"])
        self.assertIn(str(result["before"]), md)
        self.assertIn(str(result["after"]), md)
        self.assertIn(result["prompt"].split("\n")[0], md)

    def test_write_skill_creates_layout(self):
        with tempfile.TemporaryDirectory() as d:
            path = write_skill(d)
            self.assertEqual(path, os.path.join(d, "promptsmith", "SKILL.md"))
            self.assertTrue(os.path.isfile(path))
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), render_skill())

    def test_skill_cli_prints_and_writes(self):
        from promptsmith.cli import main
        with tempfile.TemporaryDirectory() as d:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                main(["skill", "--out", d])
            self.assertIn("Skill written to:", out.getvalue())
            self.assertTrue(os.path.isfile(os.path.join(d, "promptsmith", "SKILL.md")))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            main(["skill"])
        self.assertTrue(out.getvalue().startswith("---\nname: promptsmith"))


class TestCompare(unittest.TestCase):
    WEAK = "help me with python"
    STRONG = ("Write a cover letter for a data science internship. "
              "Keep it under 250 words in 3 short paragraphs. "
              "Tone: confident but humble. Do not use buzzwords.")

    def test_totals_match_scorer(self):
        r = compare_prompts(self.WEAK, self.STRONG)
        ta, _, _ = score_prompt(self.WEAK)
        tb, _, _ = score_prompt(self.STRONG)
        self.assertEqual(r["a"]["score"], ta)
        self.assertEqual(r["b"]["score"], tb)

    def test_deltas_are_b_minus_a(self):
        r = compare_prompts(self.WEAK, self.STRONG)
        for check, delta in r["deltas"].items():
            self.assertEqual(delta, r["b"]["breakdown"][check] -
                             r["a"]["breakdown"][check])

    def test_winner_and_margin(self):
        r = compare_prompts(self.WEAK, self.STRONG)
        self.assertEqual(r["winner"], "b")
        self.assertEqual(r["margin"], r["b"]["score"] - r["a"]["score"])

        r2 = compare_prompts(self.STRONG, self.WEAK)
        self.assertEqual(r2["winner"], "a")
        self.assertEqual(r2["margin"], r2["a"]["score"] - r2["b"]["score"])

    def test_tie(self):
        r = compare_prompts(self.WEAK, self.WEAK)
        self.assertEqual(r["winner"], "tie")
        self.assertEqual(r["margin"], 0)
        self.assertTrue(all(d == 0 for d in r["deltas"].values()))

    def _run(self, argv):
        from promptsmith.cli import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(argv)
        return buf.getvalue()

    def test_cli_json_schema(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(self.WEAK)
            fa = f.name
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(self.STRONG)
            fb = f.name
        try:
            out = self._run(["compare", fa, fb, "--json"])
            data = json.loads(out)
            self.assertEqual(set(data),
                             {"a", "b", "deltas", "winner", "margin"})
            self.assertEqual(data["winner"], "b")
            self.assertEqual(data["margin"],
                             data["b"]["score"] - data["a"]["score"])
        finally:
            os.unlink(fa)
            os.unlink(fb)

    def test_cli_text_output(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(self.WEAK)
            fa = f.name
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(self.STRONG)
            fb = f.name
        try:
            out = self._run(["compare", fa, fb])
            self.assertIn("B wins", out)
            self.assertIn("check", out)
            self.assertIn("Fix A first:", out)
        finally:
            os.unlink(fa)
            os.unlink(fb)

    def test_cli_missing_file(self):
        from promptsmith.cli import main
        with self.assertRaises(SystemExit) as ctx:
            main(["compare", "/nope/missing_a.txt", "/nope/missing_b.txt"])
        self.assertEqual(ctx.exception.code, 1)


class TestHistory(unittest.TestCase):
    def _tmp_cwd(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        prev = os.getcwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, prev)

    def _history_file(self):
        return os.path.join(".promptsmith", "history.jsonl")

    def test_log_writes_jsonl(self):
        from promptsmith.history import log_score
        self._tmp_cwd()
        rec = log_score("help me with python", 37, "weak", {"clarity": 4})
        self.assertTrue(os.path.isfile(self._history_file()))
        self.assertEqual(rec["score"], 37)
        self.assertEqual(rec["prompt"], "help me with python")
        self.assertEqual(rec["grade"], "weak")
        self.assertIn("ts", rec)

    def test_load_roundtrip_keeps_order(self):
        from promptsmith.history import log_score, load_history
        self._tmp_cwd()
        log_score("p1", 30)
        log_score("p1", 50)
        log_score("p2", 80)
        recs = load_history()
        self.assertEqual([r["score"] for r in recs], [30, 50, 80])

    def test_load_missing_file_returns_empty(self):
        from promptsmith.history import load_history
        self._tmp_cwd()
        self.assertEqual(load_history(), [])

    def test_corrupt_lines_are_skipped(self):
        from promptsmith.history import log_score, load_history
        self._tmp_cwd()
        log_score("ok", 40)
        with open(self._history_file(), "a", encoding="utf-8") as f:
            f.write("this is not json\n")
        self.assertEqual(len(load_history()), 1)

    def test_trend_math(self):
        from promptsmith.history import log_score, load_history, trend
        self._tmp_cwd()
        log_score("p1", 30)
        log_score("p1", 50)
        log_score("p2", 90)
        rows = {r["prompt"]: r for r in trend(load_history())}
        self.assertEqual(rows["p1"]["runs"], 2)
        self.assertEqual(rows["p1"]["average"], 40.0)
        self.assertEqual(rows["p1"]["best"], 50)
        self.assertEqual(rows["p1"]["last"], 50)
        self.assertEqual(rows["p1"]["delta"], 20)
        self.assertEqual(rows["p2"]["runs"], 1)
        self.assertEqual(rows["p2"]["delta"], 0)

    def test_sparkline_shapes(self):
        from promptsmith.history import sparkline
        up = sparkline([10, 30, 60, 90])
        self.assertEqual(len(up), 4)
        self.assertLess(up[0], up[-1])  # block codepoints rise with score
        flat = sparkline([50, 50, 50])
        self.assertEqual(len(set(flat)), 1)
        self.assertEqual(sparkline([]), "")

    def test_score_log_flag_writes_file(self):
        from promptsmith.cli import main
        from promptsmith.history import load_history
        self._tmp_cwd()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["score", "help me with python", "--log"])
        recs = load_history()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["prompt"], "help me with python")

    def test_score_log_flag_works_with_json(self):
        from promptsmith.cli import main
        from promptsmith.history import load_history
        self._tmp_cwd()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["score", "help me with python", "--json", "--log"])
        data = json.loads(buf.getvalue())  # output still pure JSON
        self.assertEqual(len(load_history()), 1)
        self.assertEqual(load_history()[0]["score"], data["score"])

    def test_compare_log_writes_both_runs(self):
        from promptsmith.cli import main
        from promptsmith.history import load_history
        self._tmp_cwd()
        with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                         delete=False) as f:
            f.write("help me with python")
            fa = f.name
        with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                         delete=False) as f:
            f.write("Write a cover letter for a data science internship. "
                    "Keep it under 250 words. Tone: confident.")
            fb = f.name
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                main(["compare", fa, fb, "--log"])
            recs = load_history()
            self.assertEqual(len(recs), 2)
            self.assertLess(recs[0]["score"], recs[1]["score"])
        finally:
            os.unlink(fa)
            os.unlink(fb)

    def test_report_empty_history_message(self):
        from promptsmith.cli import main
        self._tmp_cwd()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["report"])
        self.assertIn("No score history yet", buf.getvalue())

    def test_report_shows_trends_and_verdicts(self):
        from promptsmith.cli import main
        from promptsmith.history import log_score
        self._tmp_cwd()
        log_score("up", 30)
        log_score("up", 70)
        log_score("down", 80)
        log_score("down", 40)
        log_score("flat", 50)
        log_score("flat", 50)
        log_score("new", 60)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["report"])
        out = buf.getvalue()
        for word in ("improving", "slipping", "steady", "baseline"):
            self.assertIn(word, out)
        self.assertIn("▁", out)  # sparkline glyphs render

    def test_report_json_schema(self):
        from promptsmith.cli import main
        from promptsmith.history import log_score
        self._tmp_cwd()
        log_score("iter prompt", 30)
        log_score("iter prompt", 70)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["report", "--json"])
        data = json.loads(buf.getvalue())
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(set(row), {"prompt", "runs", "average", "best",
                                   "last", "delta", "spark"})
        self.assertEqual(row["runs"], 2)
        self.assertEqual(row["delta"], 40)
        self.assertEqual(row["average"], 50.0)


if __name__ == "__main__":
    unittest.main()
