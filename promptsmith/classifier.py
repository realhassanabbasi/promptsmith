"""Intent classifier, built from scratch.

A tiny Multinomial Naive Bayes over word counts. No sklearn, no numpy —
just the math, so the whole tool stays dependency-free.
"""

import json
import math
import os
import re


def tokenize(text):
    # lowercase words only, drop tiny filler tokens
    return [w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 2]


class NaiveBayesIntent:
    def __init__(self):
        self.classes = []
        self.log_prior = {}
        self.log_likelihood = {}
        self.vocab = set()

    def train(self, labeled):
        # labeled: {intent: [example, ...]}
        self.classes = sorted(labeled.keys())
        doc_counts = {c: len(labeled[c]) for c in self.classes}
        total_docs = sum(doc_counts.values())
        # priors, smoothed a little so rare classes don't vanish
        self.log_prior = {
            c: math.log((doc_counts[c] + 1) / (total_docs + len(self.classes)))
            for c in self.classes
        }
        word_counts = {c: {} for c in self.classes}
        for c in self.classes:
            for ex in labeled[c]:
                for w in tokenize(ex):
                    self.vocab.add(w)
                    word_counts[c][w] = word_counts[c].get(w, 0) + 1
        v = len(self.vocab)
        self.log_likelihood = {}
        for c in self.classes:
            total_words = sum(word_counts[c].values())
            self.log_likelihood[c] = {
                w: math.log((word_counts[c].get(w, 0) + 1) / (total_words + v))
                for w in self.vocab
            }
            # probability mass for words never seen in training
            self.log_likelihood[c]["<UNK>"] = math.log(1 / (total_words + v))

    def predict(self, text):
        # returns (best_intent, confidence 0..1)
        words = tokenize(text)
        scores = {}
        for c in self.classes:
            s = self.log_prior[c]
            for w in words:
                s += self.log_likelihood[c].get(w, self.log_likelihood[c]["<UNK>"])
            scores[c] = s
        # softmax over log-scores for a readable confidence
        best = max(scores, key=scores.get)
        m = max(scores.values())
        exps = {c: math.exp(v - m) for c, v in scores.items()}
        total = sum(exps.values())
        return best, round(exps[best] / total, 2)


def load_default():
    path = os.path.join(os.path.dirname(__file__), "data", "training_prompts.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    clf = NaiveBayesIntent()
    clf.train(data["intents"])
    return clf


# Below this confidence the winning intent is a guess, not a read.
# Falling back to "chat" (the generic role) beats confidently
# enhancing with the wrong intent's role and format.
FALLBACK_CONFIDENCE = 0.35

_default_clf = None


def predict_intent(text):
    """(intent, confidence) with an honest fallback.

    Uses the trained classifier, but when confidence is shaky the
    intent falls back to "chat" instead of a wrong specific guess.
    """
    global _default_clf
    if _default_clf is None:
        _default_clf = load_default()
    intent, conf = _default_clf.predict(text)
    if conf < FALLBACK_CONFIDENCE:
        return "chat", conf
    return intent, conf
