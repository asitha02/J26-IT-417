"""
Is the 'split letter' problem in the TEXT or only in how the screen draws it?
Put in project_j417/scripts/ and run from project_j417:   py -m scripts.inspect_sinhala
"""
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")

from app.services.translator import translate_sentences

TEXTS = ["Machine learning is a field of study.",
         "Gradient descent minimizes a loss function.",
         "A neural network is made of layers of connected nodes."]

for en, si in zip(TEXTS, translate_sentences(TEXTS, "en", "si")):
    print("\nEN:", en)
    print("SI:", si)
    # show the code points around every virama (U+0DCA) and zero-width joiner (U+200D)
    for i, ch in enumerate(si):
        if ch in ("්", "‍"):
            window = si[max(0, i - 2): i + 3]
            print(f"  {unicodedata.name(ch)} at {i}: " +
                  " ".join(f"U+{ord(c):04X}" for c in window))
    gaps = [i for i in range(1, len(si) - 1) if si[i] == " " and si[i - 1] == "්"]
    print("  space right after a virama (possible real split):", len(gaps))
