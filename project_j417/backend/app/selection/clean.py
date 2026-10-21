"""Strip redundant words from ASR text before it is windowed, embedded and shown.

Removes: speech fillers (um, uh...), discourse padding (you know, I mean, basically...), stuttered
repeats ("the the", "I think I think") and channel boilerplate ("like and subscribe", sponsor reads).
Fewer tokens -> less embedding work, smaller stored vectors, and clips that read cleaner.
Timestamps are untouched: cleaning only rewrites each segment's text.
"""

import re

_FILLER = re.compile(r"\b(?:u+m+|u+h+|u+hm+|e+r+m*|a+h+m*|h+m+)\b[,.]?\s*", re.I)
_PADDING = re.compile(r"(?:^|(?<=[,.?!]))\s*(?:you know|i mean|you see)\s*,\s*|\b(?:basically|literally|honestly)\b,?\s*", re.I)
_REPEAT = re.compile(r"\b((?:\w+\s+){0,2}\w+)(?:\s+\1\b)+", re.I)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_BOILERPLATE = re.compile(
    r"like and subscribe|subscribe to (?:the|my|our) (?:channel|newsletter)|hit the (?:bell|like)|smash (?:that|the) like|"
    r"links? (?:is|are)? ?(?:down )?(?:in|below)(?: the)? (?:description|comments)|thanks? (?:so much )?for watching|"
    r"see you (?:in the )?next (?:time|video)|welcome back to (?:the|my|our) channel|(?:this video is )?sponsored by|"
    r"patreon|don'?t forget to (?:like|subscribe|share)|use (?:the )?(?:code|promo)",
    re.I,
)
_SPACES = re.compile(r"\s+")


def clean_text(text: str) -> str:
    kept = [s for s in _SENTENCE.split(text) if not _BOILERPLATE.search(s)]
    out = " ".join(kept)
    out = _FILLER.sub("", out)
    out = _PADDING.sub(" ", out)
    out = _REPEAT.sub(r"\1", out)
    out = _SPACES.sub(" ", out).strip(" ,")
    return out


def clean_segments(segments: list[dict], min_words: int = 3) -> list[dict]:
    """Return segments with cleaned text; ones left with fewer than `min_words` words are dropped."""
    result = []
    for s in segments:
        text = clean_text(s["text"])
        if len(text.split()) >= min_words:
            result.append({**s, "text": text})
    return result
