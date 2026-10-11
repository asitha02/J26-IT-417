import json
import sys
from pathlib import Path

import numpy as np
from sacrebleu.metrics import CHRF

from app.core.config import CONSISTENCY_MODEL
from app.services.embedding import embed_texts
from app.services.translator import translate_sentences, translate_with_pairs

sys.stdout.reconfigure(encoding="utf-8")   # lets PowerShell print Sinhala

SENTENCES = [
    "Gradient descent minimizes a loss function.",
    "A neural network is made of layers of connected nodes.",
    "Backpropagation computes the gradient of the loss with respect to each weight.",
    "Overfitting happens when a model memorizes the training data.",
    "The learning rate controls the size of each update step.",
    "A validation set is used to tune hyperparameters.",
]

DOC = """## Study Notes
- Gradient descent minimizes a loss function. [kb_00001]
- Backpropagation computes gradients in neural networks. [kb_00002]

Overfitting happens when a model memorizes the training data. [kb_00003]"""

# A: structure and citations survive translation
si_doc, _ = translate_with_pairs(DOC)
print("=== A: document translation ===")
print(si_doc, "\n")
for tag in ["[kb_00001]", "[kb_00002]", "[kb_00003]", "## ", "- "]:
    print(f"  {'PASS' if tag in si_doc else 'FAIL'}  keeps {tag!r}")

# B: sentence translations
si = translate_sentences(SENTENCES)
print("\n=== B: sentence pairs ===")
for en, s in zip(SENTENCES, si):
    print(f"  EN: {en}\n  SI: {s}\n")

# C: does the consistency model understand Sinhala?
src = embed_texts(SENTENCES, model_name=CONSISTENCY_MODEL)
tgt = embed_texts(si, model_name=CONSISTENCY_MODEL)
sim = src @ tgt.T
matched = np.diag(sim)
mismatched = sim[~np.eye(len(SENTENCES), dtype=bool)]
top1 = (sim.argmax(axis=1) == np.arange(len(SENTENCES))).mean()
print("=== C: consistency model sanity check ===")
print(f"  matched pairs mean:    {matched.mean():.3f}")
print(f"  mismatched pairs mean: {mismatched.mean():.3f}")
print(f"  top-1 retrieval:       {top1:.0%}")

# D: round-trip (EN -> SI -> EN) chrF, a rough proxy for meaning preserved
back = translate_sentences(si, source="si", target="en")
chrf = CHRF().corpus_score(back, [SENTENCES]).score
print(f"\n=== D: round-trip chrF: {chrf:.1f} ===")

# E: save to a UTF-8 file so you can read Sinhala in VS Code
out = Path("evaluation/outputs")
out.mkdir(parents=True, exist_ok=True)
(out / "sinhala_test.json").write_text(
    json.dumps([{"en": e, "si": s, "back": b} for e, s, b in zip(SENTENCES, si, back)],
               ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("\nSaved evaluation/outputs/sinhala_test.json")