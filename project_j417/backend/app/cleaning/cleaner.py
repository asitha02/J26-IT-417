"""The cleaner: removes redundant sentences, error words and duplicates.

Each of the three jobs uses its TRAINED model when it has been trained and passed its own test, and otherwise
falls back to the hand-written rules.
"""

import json
from pathlib import Path

from app.cleaning import rules
from app.cleaning.duplicate_model import DuplicateModel
from app.cleaning.sentence_model import SentenceModel
from app.cleaning.word_model import WordModel


class Cleaner:
    def __init__(self, sentence: SentenceModel | None = None, words: WordModel | None = None,
                 duplicate: DuplicateModel | None = None):
        self.sentence, self.words, self.duplicate = sentence, words, duplicate

    @property
    def in_use(self) -> dict[str, bool]:
        """Which jobs are done by a trained model (the rest use the rules)."""
        return {"sentences": self.sentence is not None, "words": self.words is not None,
                "duplicates": self.duplicate is not None}

    def clean_text(self, text: str) -> tuple[str, int, int]:
        """(cleaned text, redundant sentences dropped, error words removed)."""
        drop = self.sentence.is_redundant if self.sentence else rules.is_boilerplate
        sentences = rules.SENTENCE_SPLIT.split(text)
        kept = [s for s in sentences if not drop(s)]
        out = " ".join(kept)
        before = len(out.split())
        out = self.words.apply(out) if self.words else rules.clean_words(out)
        return out, len(sentences) - len(kept), max(before - len(out.split()), 0)

    def is_duplicate(self, a: list[str], b: list[str]) -> bool:
        return self.duplicate.is_duplicate(a, b) if self.duplicate else rules.is_duplicate(a, b)


# ---------------------------------------------------------------- saving and loading the trained models
def models_dir(data_dir: Path) -> Path:
    return data_dir / "models" / "cleaning"


def save(data_dir: Path, sentence: SentenceModel, words: WordModel, duplicate: DuplicateModel, report: dict) -> None:
    d = models_dir(data_dir)
    d.mkdir(parents=True, exist_ok=True)
    for name, model in (("sentences", sentence), ("words", words), ("duplicates", duplicate)):
        (d / f"{name}.json").write_text(json.dumps(model.to_json()), encoding="utf-8")
    (d / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def load_report(data_dir: Path) -> dict | None:
    path = models_dir(data_dir) / "report.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


_cache: dict[str, tuple[float, Cleaner]] = {}


def load_cleaner(data_dir: Path) -> Cleaner:
    """The cleaner built from the trained models that passed their tests (re-read when they are retrained)."""
    d = models_dir(data_dir)
    report = load_report(data_dir)
    if not report:
        return Cleaner()
    mtime = (d / "report.json").stat().st_mtime
    hit = _cache.get(str(d))
    if hit is None or hit[0] != mtime:
        def load(name, cls, key):
            path = d / f"{name}.json"
            return cls.from_json(json.loads(path.read_text(encoding="utf-8"))) if report[key]["activated"] and path.exists() else None

        _cache[str(d)] = (mtime, Cleaner(load("sentences", SentenceModel, "sentences"), load("words", WordModel, "words"),
                                         load("duplicates", DuplicateModel, "duplicates")))
    return _cache[str(d)][1]
