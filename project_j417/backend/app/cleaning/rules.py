"""The hand-written rules. They are the FALLBACK (used until the models are trained) and the BASELINE every
trained model is compared against."""

import re

from app.cleaning.ml import words_of

_FILLER = re.compile(r"\b(?:u+m+|u+h+|u+hm+|e+r+m*|a+h+m*|h+m+)\b[,.]?\s*", re.I)
_PADDING = re.compile(r"(?:^|(?<=[,.?!]))\s*(?:you know|i mean|you see)\s*,\s*|\b(?:basically|literally|honestly)\b,?\s*", re.I)
_REPEAT = re.compile(r"\b((?:\w+\s+){0,2}\w+)(?:\s+\1\b)+", re.I)
_SPACES = re.compile(r"\s+")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_BOILERPLATE = re.compile(
    r"like and subscribe|subscribe to (?:the|my|our) (?:channel|newsletter)|hit the (?:bell|like)|smash (?:that|the) like|"
    r"links? (?:is|are)? ?(?:down )?(?:in|below)(?: the)? (?:description|comments)|thanks? (?:so much )?for watching|"
    r"see you (?:in the )?next (?:time|video)|welcome back to (?:the|my|our) channel|(?:this video is )?sponsored by|"
    r"patreon|don'?t forget to (?:like|subscribe|share)|use (?:the )?(?:code|promo)",
    re.I,
)

DUPLICATE_SIMILARITY = 0.85  # word-set overlap above which two sentences count as the same


def is_boilerplate(sentence: str) -> bool:
    return bool(_BOILERPLATE.search(sentence))


def clean_words(text: str) -> str:
    """Remove filler words, padding phrases and stuttered repeats."""
    out = _FILLER.sub("", text)
    out = _PADDING.sub(" ", out)
    out = _REPEAT.sub(r"\1", out)
    return _SPACES.sub(" ", out).strip(" ,")


def is_duplicate(a: list[str], b: list[str], similarity: float = DUPLICATE_SIMILARITY) -> bool:
    sa, sb = set(a), set(b)
    union = len(sa | sb)
    return bool(union) and len(sa & sb) / union >= similarity


def same_words(a: str, b: str) -> bool:
    return words_of(a) == words_of(b)
