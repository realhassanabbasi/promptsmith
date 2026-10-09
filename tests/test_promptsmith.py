"""Run: python -m unittest discover -s tests -v"""

import contextlib
import io
import json
import os
import tempfile
import unittest

from promptsmith.classifier import load_default
from promptsmith.enhancer import enhance
from promptsmith.scorer import grade, score_prompt
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


if __name__ == "__main__":
    unittest.main()
