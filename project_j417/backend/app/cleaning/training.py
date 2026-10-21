"""Train the three cleaning models on the stored transcripts and test each one."""

from datetime import datetime, timezone

from app.cleaning import data, duplicate_model, sentence_model, word_model
from app.cleaning.cleaner import Cleaner


class TrainingError(ValueError):
    pass


def train_all(docs: list[dict]):
    """Returns (sentence model, word model, duplicate model, report). Each model has its own held-out test in the report."""
    real = data.real_sentences(docs)
    base = data.base_sentences(real)
    try:
        sentences, sentence_report = sentence_model.train(real)
        words, word_report = word_model.train(base)
        duplicates, duplicate_report = duplicate_model.train(base)
    except (sentence_model.TrainingError, word_model.TrainingError, duplicate_model.TrainingError) as exc:
        raise TrainingError(str(exc)) from exc
    report = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "real_sentences": len(real),
        "sentences": sentence_report,
        "words": word_report,
        "duplicates": duplicate_report,
    }
    return sentences, words, duplicates, report


def cleaner_from(sentences, words, duplicates, report: dict) -> Cleaner:
    """The cleaner that uses only the models that passed their own test."""
    return Cleaner(
        sentences if report["sentences"]["activated"] else None,
        words if report["words"]["activated"] else None,
        duplicates if report["duplicates"]["activated"] else None,
    )
