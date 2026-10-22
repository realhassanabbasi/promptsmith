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

    def test_skill_teaches_the_loop(self):
        # v1.8.0: the skill must teach the full score→prove→keep loop,
        # not just the 5-check rubric
        md = render_skill()
        self.assertIn("## The improvement loop", md)
        self.assertIn("Prove it got better", md)
        self.assertIn("margin", md)
        self.assertIn("version history", md)
        self.assertIn("score` → `improve` → `compare`", md)

    def test_example_is_real_improve_output(self):
        # the worked example must come from the real improve() pipeline,
        # margin and per-check gains included
        from promptsmith.improve import improve_prompt, what_improved
        from promptsmith.skills import EXAMPLE_ROUGH
        md = render_skill()
        result = improve_prompt(EXAMPLE_ROUGH)
        self.assertGreater(result["after"]["score"], result["before"]["score"])
        self.assertIn(str(result["before"]["score"]), md)
        self.assertIn(str(result["after"]["score"]), md)
        self.assertIn(f"+{result['margin']}", md)
        self.assertIn(result["enhanced"].split("\n")[0], md)
        for check, delta in what_improved(result["deltas"], top=3):
            self.assertIn(f"{check} +{delta}", md)

    def test_frontmatter_describes_loop(self):
        md = render_skill()
        self.assertIn("improvement loop", md.split("---")[1])

    def test_version_is_1_14_0(self):
        import promptsmith
        self.assertEqual(promptsmith.__version__, "1.14.0")


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



class TestImprove(unittest.TestCase):
    WEAK = "help me with python"

    def test_before_after_and_margin(self):
        from promptsmith.improve import improve_prompt
        r = improve_prompt(self.WEAK)
        self.assertIn("intent", r)
        self.assertTrue(r["enhanced"])
        self.assertEqual(r["margin"],
                         r["after"]["score"] - r["before"]["score"])
        self.assertGreaterEqual(r["after"]["score"], r["before"]["score"])

    def test_deltas_match_compare(self):
        from promptsmith.improve import improve_prompt
        r = improve_prompt(self.WEAK)
        cmp = compare_prompts(self.WEAK, r["enhanced"])
        self.assertEqual(r["deltas"], cmp["deltas"])
        self.assertEqual(r["before"]["score"], cmp["a"]["score"])
        self.assertEqual(r["after"]["score"], cmp["b"]["score"])

    def test_confidence_rounded(self):
        from promptsmith.improve import improve_prompt
        r = improve_prompt(self.WEAK)
        self.assertLessEqual(r["confidence"], 1.0)
        self.assertEqual(r["confidence"], round(r["confidence"], 3))

    def test_what_improved_sorts_best_first(self):
        from promptsmith.improve import what_improved
        deltas = {"clarity": 8, "context": 0, "specificity": -2,
                  "format": 16, "guardrails": 5}
        self.assertEqual(what_improved(deltas, top=2),
                         [("format", 16), ("clarity", 8)])

    def _run(self, argv):
        from promptsmith.cli import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(argv)
        return buf.getvalue()

    def test_cli_text_shows_gain_table(self):
        out = self._run(["improve", self.WEAK])
        self.assertIn("Detected intent:", out)
        self.assertIn("Score:", out)
        self.assertIn("What improved:", out)
        self.assertIn("Improved prompt", out)

    def test_cli_json_schema(self):
        out = self._run(["improve", self.WEAK, "--json"])
        data = json.loads(out)
        self.assertEqual(set(data),
                         {"prompt", "intent", "confidence", "before",
                          "after", "deltas", "margin", "enhanced"})
        self.assertEqual(data["margin"],
                         data["after"]["score"] - data["before"]["score"])

    def test_cli_save_writes_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.md")
            out = self._run(["improve", self.WEAK, "--save", path])
            self.assertTrue(os.path.isfile(path))
            with open(path, encoding="utf-8") as f:
                self.assertIn("Task:", f.read())
            self.assertIn("Saved to", out)

    def test_cli_log_writes_both_runs(self):
        from promptsmith.history import load_history
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        prev = os.getcwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, prev)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            from promptsmith.cli import main
            main(["improve", self.WEAK, "--log"])
        recs = load_history()
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0]["prompt"], self.WEAK)
        self.assertNotEqual(recs[0]["prompt"], recs[1]["prompt"])

    def test_cli_diff_shows_change_block(self):
        out = self._run(["improve", self.WEAK, "--diff"])
        self.assertIn("What changed:", out)
        self.assertIn("words", out)
        # changed words are marked with -dashes- and +pluses+
        self.assertIn("+", out)

    def test_cli_no_diff_block_by_default(self):
        out = self._run(["improve", self.WEAK])
        self.assertNotIn("What changed:", out)

    def test_cli_json_diff_payload(self):
        out = self._run(["improve", self.WEAK, "--json", "--diff"])
        data = json.loads(out)
        self.assertIn("diff", data)
        self.assertIn("stats", data["diff"])
        self.assertIn("segments", data["diff"])
        self.assertTrue(data["diff"]["segments"])
        self.assertGreaterEqual(data["diff"]["stats"]["added"], 0)

    def test_cli_json_has_no_diff_key_without_flag(self):
        out = self._run(["improve", self.WEAK, "--json"])
        data = json.loads(out)
        self.assertNotIn("diff", data)


class TestLibrary(unittest.TestCase):
    WEAK = "help me with python"

    def _tmp_cwd(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        prev = os.getcwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, prev)

    def _run(self, argv):
        from promptsmith.cli import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(argv)
        return buf.getvalue()

    def test_save_writes_jsonl_with_version_one(self):
        from promptsmith.library import save_entry
        self._tmp_cwd()
        rec = save_entry("py-help", self.WEAK)
        self.assertTrue(os.path.isfile(".promptsmith/library.jsonl"))
        self.assertEqual(rec["version"], 1)
        self.assertEqual(rec["name"], "py-help")
        self.assertEqual(rec["score"], rec["score"])
        self.assertIsNone(rec["enhanced"])
        self.assertIn("ts", rec)

    def test_re_save_increments_version(self):
        from promptsmith.library import save_entry, entries_for
        self._tmp_cwd()
        save_entry("py-help", self.WEAK)
        rec2 = save_entry("py-help", "help me with python 3")
        self.assertEqual(rec2["version"], 2)
        self.assertEqual(len(entries_for("py-help")), 2)

    def test_save_improve_records_enhanced_and_before(self):
        from promptsmith.library import save_entry
        self._tmp_cwd()
        rec = save_entry("py-help", self.WEAK, enhance_it=True)
        self.assertTrue(rec["enhanced"])
        self.assertIsNotNone(rec["before_score"])
        self.assertGreaterEqual(rec["score"], rec["before_score"])

    def test_tags_roundtrip(self):
        from promptsmith.library import save_entry, load_library
        self._tmp_cwd()
        save_entry("py-help", self.WEAK, tags=["coding", "debug", "  "])
        recs = load_library()
        self.assertEqual(recs[0]["tags"], ["coding", "debug"])

    def test_corrupt_lines_skipped(self):
        from promptsmith.library import load_library
        self._tmp_cwd()
        os.makedirs(".promptsmith", exist_ok=True)
        with open(".promptsmith/library.jsonl", "w", encoding="utf-8") as f:
            f.write('{"name": "good", "version": 1, "score": 80}\n')
            f.write("not json at all\n")
            f.write('{"name": "good", "version": 2, "score": 90}\n')
        recs = load_library()
        self.assertEqual(len(recs), 2)
        self.assertEqual([r["score"] for r in recs], [80, 90])

    def test_summarize_math(self):
        from promptsmith.library import save_entry, summarize
        self._tmp_cwd()
        save_entry("a", self.WEAK)
        save_entry("a", "write a python function that sorts a list")
        rows = summarize()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["versions"], 2)
        self.assertEqual(rows[0]["best"], max(rows[0]["last"], rows[0]["best"]))
        self.assertIn("delta", rows[0])
        self.assertIn("tags", rows[0])

    def test_cli_save_prints_version(self):
        self._tmp_cwd()
        out = self._run(["save", "py-help", self.WEAK, "--tags", "coding"])
        self.assertIn("Saved:", out)
        self.assertIn("py-help", out)
        self.assertIn("v1", out)
        self.assertTrue(os.path.isfile(".promptsmith/library.jsonl"))

    def test_cli_library_list_and_history(self):
        self._tmp_cwd()
        self._run(["save", "py-help", self.WEAK])
        self._run(["save", "py-help", "write a python function that sorts a list"])
        out = self._run(["library"])
        self.assertIn("Prompt library", out)
        self.assertIn("py-help", out)
        out2 = self._run(["library", "py-help"])
        self.assertIn("version(s)", out2)
        self.assertIn("v1", out2)
        self.assertIn("v2", out2)

    def test_cli_library_json_schema(self):
        self._tmp_cwd()
        self._run(["save", "py-help", self.WEAK, "--tags", "coding"])
        data = json.loads(self._run(["library", "--json"]))
        self.assertEqual(len(data), 1)
        self.assertEqual(set(data[0]),
                         {"name", "versions", "last", "best",
                          "delta", "tags", "saved"})
        data2 = json.loads(self._run(["library", "py-help", "--json"]))
        self.assertEqual(data2[0]["name"], "py-help")
        self.assertEqual(data2[0]["version"], 1)

    def test_cli_library_empty_and_unknown_name(self):
        self._tmp_cwd()
        out = self._run(["library"])
        self.assertIn("Library is empty", out)
        self._run(["save", "py-help", self.WEAK])
        out2 = self._run(["library", "nope"])
        self.assertIn('No saved prompt named "nope"', out2)


class TestTokens(unittest.TestCase):
    def test_estimate_empty(self):
        from promptsmith.tokens import estimate_tokens
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("   "), 0)

    def test_estimate_basic(self):
        from promptsmith.tokens import estimate_tokens
        # ~4 chars per token heuristic
        t = estimate_tokens("Write a short poem about the sea.")
        self.assertGreater(t, 5)
        self.assertLess(t, 15)

    def test_estimate_long_words(self):
        from promptsmith.tokens import estimate_tokens
        short = estimate_tokens("cat dog bird")
        longw = estimate_tokens("antidisestablishmentarianism " * 5)
        self.assertGreater(longw, short)

    def test_token_report(self):
        from promptsmith.tokens import token_report
        r = token_report("Hello world, this is a test prompt.")
        self.assertIn("tokens", r)
        self.assertIn("context_share", r)
        self.assertEqual(r["model"], "gpt-4o")
        self.assertGreater(r["tokens"], 0)

    def test_token_report_json_schema(self):
        from promptsmith.tokens import token_report
        r = token_report("Test", model="claude-3-5-sonnet")
        self.assertEqual(set(r),
                         {"prompt", "tokens", "characters", "words",
                          "model", "context_window", "context_share", "note"})

    def test_context_share(self):
        from promptsmith.tokens import context_share
        self.assertAlmostEqual(context_share(64000, "gpt-4o"), 0.5)
        self.assertAlmostEqual(context_share(0, "gpt-4o"), 0.0)


class TestCost(unittest.TestCase):
    def test_cost_math_custom_prices(self):
        from promptsmith.cost import cost_estimate
        r = cost_estimate(1_000_000, 500_000, in_price=2.0, out_price=8.0)
        self.assertAlmostEqual(r["in_cost_usd"], 2.0)
        self.assertAlmostEqual(r["out_cost_usd"], 4.0)
        self.assertAlmostEqual(r["total_usd"], 6.0)
        self.assertTrue(r["prices_custom"])
        self.assertIsNone(r["prices_checked"])

    def test_cost_model_table(self):
        from promptsmith.cost import cost_estimate
        r = cost_estimate(1_000_000, 0, model="gpt-4o")
        self.assertEqual(r["in_cost_usd"], 2.50)
        self.assertEqual(r["model"], "gpt-4o")
        self.assertFalse(r["prices_custom"])
        self.assertEqual(r["prices_checked"], "2026-10-19")

    def test_cost_unknown_model(self):
        from promptsmith.cost import cost_estimate
        with self.assertRaises(ValueError) as ctx:
            cost_estimate(100, 100, model="does-not-exist")
        self.assertIn("gpt-4o", str(ctx.exception))

    def test_cost_zero_tokens(self):
        from promptsmith.cost import cost_estimate
        r = cost_estimate(0, 0, model="gpt-4o")
        self.assertEqual(r["total_usd"], 0)

    def test_cost_report_schema(self):
        from promptsmith.cost import cost_report
        r = cost_report("help me with python", model="claude-sonnet-5.5", calls=1000)
        expected = {"prompt", "tokens", "out_tokens_estimate", "out_ratio",
                    "calls", "cost_per_call_usd", "budget_usd", "model",
                    "in_price_per_1m", "out_price_per_1m", "prices_custom",
                    "prices_checked", "note"}
        self.assertEqual(set(r), expected)
        self.assertAlmostEqual(r["budget_usd"], r["cost_per_call_usd"] * 1000, places=3)
        self.assertEqual(r["model"], "claude-sonnet-5.5")

    def test_cost_report_out_ratio(self):
        from promptsmith.cost import cost_report
        r = cost_report("help me with python", out_ratio=0.5)
        self.assertEqual(r["out_tokens_estimate"], round(r["tokens"] * 0.5))
        with self.assertRaises(ValueError):
            cost_report("x", calls=0)

    def test_cli_cost_text(self):
        from promptsmith.cli import build_parser
        args = build_parser().parse_args(["cost", "help me with python",
                                          "--model", "gpt-4o", "--calls", "1000"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            args.func(args)
        out = buf.getvalue()
        self.assertIn("Cost:", out)
        self.assertIn("Budget:", out)
        self.assertIn("1,000 calls", out)

    def test_cli_cost_json_and_prices(self):
        from promptsmith.cli import build_parser
        args = build_parser().parse_args(["cost", "hello", "--json"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            args.func(args)
        data = json.loads(buf.getvalue())
        self.assertIn("cost_per_call_usd", data)
        self.assertEqual(data["model"], "gpt-4o")
        args = build_parser().parse_args(["cost", "--prices", "ignored"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            args.func(args)
        self.assertIn("gpt-4o", buf.getvalue())


class TestDiff(unittest.TestCase):
    def test_identical_texts_have_no_changes(self):
        from promptsmith.diff import word_diff, diff_stats
        segs = word_diff("help me with python", "help me with python")
        self.assertTrue(all(op == "keep" for op, _ in segs))
        stats = diff_stats("help me with python", "help me with python")
        self.assertEqual(stats["added"], 0)
        self.assertEqual(stats["removed"], 0)

    def test_addition_and_removal_counts(self):
        from promptsmith.diff import diff_stats
        stats = diff_stats("help me with python", "help me learn python today")
        self.assertEqual(stats["added"], 2)   # learn, today
        self.assertEqual(stats["removed"], 1)  # with
        self.assertEqual(stats["words_before"],
                         stats["unchanged"] + stats["removed"])
        self.assertEqual(stats["words_after"],
                         stats["unchanged"] + stats["added"])

    def test_render_diff_markers(self):
        from promptsmith.diff import render_diff
        out = render_diff("help me with python",
                          "help me learn python", color=False)
        self.assertIn("-with-", out)
        self.assertIn("+learn+", out)
        self.assertIn("help", out)  # unchanged words stay plain

    def test_diff_payload_schema(self):
        from promptsmith.diff import diff_payload
        p = diff_payload("one two", "one three four")
        self.assertEqual(set(p), {"stats", "segments"})
        self.assertEqual(set(p["stats"]),
                         {"words_before", "words_after", "added",
                          "removed", "unchanged"})
        for seg in p["segments"]:
            self.assertIn(seg["op"], {"keep", "del", "ins"})
            self.assertIsInstance(seg["text"], str)

    def test_cli_diff_text_and_json(self):
        from promptsmith.cli import build_parser
        paths = []
        for content in ("help me with python", "help me learn python today"):
            with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                             delete=False) as f:
                f.write(content)
                paths.append(f.name)
        try:
            args = build_parser().parse_args(["diff", paths[0], paths[1]])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                args.func(args)
            out = buf.getvalue()
            self.assertIn("What changed:", out)
            self.assertIn("-with-", out)
            self.assertIn("+learn+", out)
            args = build_parser().parse_args(
                ["diff", paths[0], paths[1], "--json"])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                args.func(args)
            data = json.loads(buf.getvalue())
            self.assertEqual(data["stats"]["removed"], 1)
            self.assertEqual(data["stats"]["added"], 2)
        finally:
            for p in paths:
                os.unlink(p)

    def test_cli_diff_missing_file_exits_1(self):
        from promptsmith.cli import build_parser
        args = build_parser().parse_args(["diff", "/no/such/file", "/nope"])
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()):
                args.func(args)
        self.assertEqual(ctx.exception.code, 1)

    def test_cli_enhance_diff_shows_changes(self):
        from promptsmith.cli import build_parser
        args = build_parser().parse_args(["enhance", "help me with python",
                                          "--diff"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            args.func(args)
        out = buf.getvalue()
        self.assertIn("What changed:", out)
        self.assertTrue("-" in out and "+" in out)

    def test_cli_compare_diff_shows_changes(self):
        from promptsmith.cli import build_parser
        paths = []
        for content in ("help me with python",
                        "Write a cover letter for a data science internship. "
                        "Keep it under 250 words."):
            with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                             delete=False) as f:
                f.write(content)
                paths.append(f.name)
        try:
            args = build_parser().parse_args(
                ["compare", paths[0], paths[1], "--diff"])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                args.func(args)
            self.assertIn("What changed:", buf.getvalue())
        finally:
            for p in paths:
                os.unlink(p)


class TestCheck(unittest.TestCase):
    WEAK = "help me with python"  # scores 37 on the current rubric

    def _tmp_cwd(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        prev = os.getcwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, prev)

    def _run(self, argv):
        from promptsmith.cli import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(argv)
        return buf.getvalue()

    def _write_records(self, records):
        os.makedirs(".promptsmith", exist_ok=True)
        with open(".promptsmith/library.jsonl", "w", encoding="utf-8") as f:
            for r in records:
                r.setdefault("tags", [])
                f.write(json.dumps(r) + "\n")

    def _record(self, name, score, prompt=None, enhanced=None):
        return {"name": name, "version": 1, "score": score,
                "prompt": prompt or self.WEAK, "enhanced": enhanced}

    def test_empty_library_returns_empty(self):
        from promptsmith.check import check_library
        self._tmp_cwd()
        self.assertEqual(check_library(), [])

    def test_saved_prompt_is_steady(self):
        from promptsmith.check import check_name
        from promptsmith.library import save_entry
        self._tmp_cwd()
        rec = save_entry("py-help", self.WEAK)
        r = check_name("py-help")
        self.assertEqual(r["verdict"], "steady")
        self.assertEqual(r["delta"], 0)
        self.assertEqual(r["current"], rec["score"])
        self.assertEqual(r["best"], rec["score"])
        self.assertEqual(r["versions"], 1)

    def test_regression_detected(self):
        # a record whose stored score (95) is higher than what the current
        # rubric gives the same text (37) must read as regressed
        from promptsmith.check import check_name
        self._tmp_cwd()
        self._write_records([self._record("py-help", 95)])
        r = check_name("py-help")
        self.assertEqual(r["verdict"], "regressed")
        self.assertLess(r["delta"], 0)
        self.assertEqual(r["delta"], r["current"] - 95)

    def test_improvement_detected(self):
        from promptsmith.check import check_name
        self._tmp_cwd()
        self._write_records([self._record("py-help", 10)])
        r = check_name("py-help")
        self.assertEqual(r["verdict"], "improved")
        self.assertGreater(r["delta"], 0)

    def test_keeper_prefers_enhanced_text(self):
        # --improve saves record the original prompt plus the enhanced text;
        # the check must re-score the enhanced text (the keeper), not the draft
        from promptsmith.check import check_name, keeper_text
        from promptsmith.library import save_entry
        from promptsmith.scorer import score_prompt
        self._tmp_cwd()
        rec = save_entry("py-help", self.WEAK, enhance_it=True)
        self.assertEqual(keeper_text(rec), rec["enhanced"])
        r = check_name("py-help")
        total, _b, _f = score_prompt(rec["enhanced"])
        self.assertEqual(r["current"], total)
        self.assertEqual(r["verdict"], "steady")

    def test_unknown_name_returns_none(self):
        from promptsmith.check import check_name
        self._tmp_cwd()
        self._write_records([self._record("py-help", 95)])
        self.assertIsNone(check_name("no-such-name"))

    def test_check_sorts_regressed_first(self):
        from promptsmith.check import check_library
        self._tmp_cwd()
        self._write_records([self._record("steady-one", 37),
                             self._record("bad-one", 95)])
        results = check_library()
        self.assertEqual([r["name"] for r in results],
                         ["bad-one", "steady-one"])

    def test_cli_check_text_output(self):
        from promptsmith.library import save_entry
        self._tmp_cwd()
        save_entry("py-help", self.WEAK)
        out = self._run(["check"])
        self.assertIn("py-help", out)
        self.assertIn("steady", out)

    def test_cli_check_unknown_name_message(self):
        self._tmp_cwd()
        self._write_records([self._record("py-help", 37)])
        out = self._run(["check", "no-such-name"])
        self.assertIn('No saved prompt named "no-such-name".', out)

    def test_cli_check_fail_on_regression_exits_1(self):
        from promptsmith.cli import main
        self._tmp_cwd()
        self._write_records([self._record("py-help", 95)])
        with self.assertRaises(SystemExit) as cm:
            with contextlib.redirect_stdout(io.StringIO()):
                main(["check", "--fail-on-regression"])
        self.assertEqual(cm.exception.code, 1)

    def test_cli_check_no_regression_exits_0(self):
        from promptsmith.library import save_entry
        self._tmp_cwd()
        save_entry("py-help", self.WEAK)
        with contextlib.redirect_stdout(io.StringIO()):
            from promptsmith.cli import main
            main(["check", "--fail-on-regression"])  # no exception = exit 0

    def test_cli_check_json_schema(self):
        from promptsmith.library import save_entry
        self._tmp_cwd()
        save_entry("py-help", self.WEAK)
        out = self._run(["check", "--json"])
        data = json.loads(out)
        self.assertEqual(data["checked"], 1)
        self.assertEqual(data["steady"], 1)
        self.assertEqual(data["regressed"], 0)
        self.assertEqual(data["improved"], 0)
        self.assertEqual(len(data["results"]), 1)
        r = data["results"][0]
        for key in ("name", "versions", "current", "best",
                    "delta", "verdict", "tags"):
            self.assertIn(key, r)


class TestExport(unittest.TestCase):
    WEAK = "help me with python"

    def _tmp_cwd(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        prev = os.getcwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, prev)

    def _run(self, argv):
        from promptsmith.cli import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(argv)
        return buf.getvalue()

    def test_empty_library_markdown_is_honest(self):
        from promptsmith.export import export_markdown
        self._tmp_cwd()
        out = export_markdown()
        self.assertIn("No saved prompts yet", out)
        self.assertIn("# Prompt Library", out)

    def test_empty_library_json_schema(self):
        from promptsmith.export import export_json
        self._tmp_cwd()
        data = json.loads(export_json())
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["prompts"], [])
        self.assertEqual(data["tool"], "promptsmith")

    def test_single_entry_markdown(self):
        from promptsmith.export import export_markdown
        from promptsmith.library import save_entry
        self._tmp_cwd()
        save_entry("py-help", self.WEAK)
        out = export_markdown()
        self.assertIn("## py-help", out)
        self.assertIn("### v1", out)
        self.assertIn(self.WEAK, out)

    def test_enhanced_text_included(self):
        from promptsmith.export import export_markdown
        from promptsmith.library import save_entry
        self._tmp_cwd()
        rec = save_entry("py-help", self.WEAK, enhance_it=True)
        out = export_markdown()
        self.assertIn("**Improved version:**", out)
        self.assertIn(rec["enhanced"][:30], out)

    def test_name_filter(self):
        from promptsmith.export import export_markdown
        from promptsmith.library import save_entry
        self._tmp_cwd()
        save_entry("py-help", self.WEAK)
        save_entry("other", "write a poem")
        out = export_markdown(name="py-help")
        self.assertIn("## py-help", out)
        self.assertNotIn("## other", out)

    def test_unknown_name_returns_none(self):
        from promptsmith.export import export_markdown, export_json
        from promptsmith.library import save_entry
        self._tmp_cwd()
        save_entry("py-help", self.WEAK)
        self.assertIsNone(export_markdown(name="nope"))
        self.assertIsNone(export_json(name="nope"))

    def test_versions_oldest_first(self):
        from promptsmith.export import export_payload
        from promptsmith.library import save_entry
        self._tmp_cwd()
        save_entry("py-help", self.WEAK)
        save_entry("py-help", "help me with python 3")
        payload = export_payload()
        entries = payload["prompts"][0]["entries"]
        self.assertEqual([e["version"] for e in entries], [1, 2])

    def test_cli_export_json(self):
        from promptsmith.library import save_entry
        self._tmp_cwd()
        save_entry("py-help", self.WEAK)
        out = self._run(["export", "--format", "json"])
        data = json.loads(out)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["prompts"][0]["name"], "py-help")

    def test_cli_export_unknown_name(self):
        self._tmp_cwd()
        out = self._run(["export", "nope"])
        self.assertIn('No saved prompt named "nope"', out)

    def test_cli_export_to_file(self):
        from promptsmith.library import save_entry
        self._tmp_cwd()
        save_entry("py-help", self.WEAK)
        out = self._run(["export", "-o", "lib.md"])
        self.assertIn("Exported to lib.md", out)
        self.assertTrue(os.path.isfile("lib.md"))
        with open("lib.md", encoding="utf-8") as f:
            self.assertIn("## py-help", f.read())


if __name__ == "__main__":
    unittest.main()
