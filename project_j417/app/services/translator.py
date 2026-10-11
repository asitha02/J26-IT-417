import re
from functools import lru_cache

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from app.core.config import NLLB_MODEL

LANG_CODES = {"en": "eng_Latn", "si": "sin_Sinh"}

PREFIX = re.compile(r"^\s*(?:#{1,6}\s+|[-*•]\s+|\d+[.)]\s+)?")
CITE = re.compile(r"\s*\[kb_\d+\]")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


@lru_cache(maxsize=1)
def _load():
    tok = AutoTokenizer.from_pretrained(NLLB_MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(NLLB_MODEL)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()
    return tok, model, device


def translate_sentences(sentences: list[str], source: str = "en", target: str = "si",
                        batch_size: int = 8) -> list[str]:
    if not sentences:
        return []
    tok, model, device = _load()
    tok.src_lang = LANG_CODES[source]
    target_id = tok.convert_tokens_to_ids(LANG_CODES[target])

    order = sorted(range(len(sentences)), key=lambda i: len(sentences[i]))  # less padding
    results = [""] * len(sentences)
    for start in range(0, len(order), batch_size):
        idx = order[start:start + batch_size]
        enc = tok([sentences[i] for i in idx], return_tensors="pt",
                  padding=True, truncation=True, max_length=200).to(device)
        with torch.no_grad():
            out = model.generate(**enc, forced_bos_token_id=target_id,
                                 num_beams=4, max_new_tokens=256)
        for i, text in zip(idx, tok.batch_decode(out, skip_special_tokens=True)):
            results[i] = text
    return results


def translate_with_pairs(text: str, target: str = "si", source: str = "en"):
    """Returns (translated_text, [(source_sentence, translated_sentence), ...])."""
    if target == source or not text.strip():
        return text, []

    lines = text.split("\n")
    plan, flat = [], []
    for line in lines:
        if not line.strip():
            plan.append(None)
            continue
        prefix = PREFIX.match(line).group(0)
        body = line[len(prefix):]
        cites = "".join(CITE.findall(body))
        body = CITE.sub("", body).strip()
        sents = [s for s in SENT_SPLIT.split(body) if s.strip()]
        plan.append((prefix, cites, len(sents)))
        flat.extend(sents)

    translated = translate_sentences(flat, source, target)

    out, k = [], 0
    for p in plan:
        if p is None:
            out.append("")
            continue
        prefix, cites, n = p
        out.append(prefix + " ".join(translated[k:k + n]) + cites)
        k += n
    return "\n".join(out), list(zip(flat, translated))


def translate(text: str, target: str = "si", source: str = "en") -> str:
    return translate_with_pairs(text, target, source)[0]