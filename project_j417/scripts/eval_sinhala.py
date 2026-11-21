"""
Step 1 of the Sinhala accuracy work: measure how good the Sinhala is TODAY.

Put in project_j417/scripts/ and run from project_j417:

  py -m pip install sacrebleu
  py -m scripts.eval_sinhala --test data/mt/test_refs.csv

test_refs.csv (save from Excel as "CSV UTF-8") has two columns:
  english, reference_si          <- reference_si = a fluent Sinhala speaker's own translation

It translates every sentence with
  nllb    your current pipeline (app.services.translator)
  gemini  Gemini translating directly to Sinhala
scores each against the human reference (chrF++, higher = better), lists the worst NLLB sentences, and writes
  data/mt/eval_outputs.csv   all outputs side by side
  data/mt/rating_sheet.csv   for human raters: columns A / B in random order (blind)
  data/mt/rating_key.csv     which system was A or B (keep this away from the raters)
"""
import argparse
import csv
import json
import os
import random
import sys
import time
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip()


def read_refs(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f)]
    out = [(nfc(r["english"]), nfc(r["reference_si"])) for r in rows
           if r.get("english", "").strip() and r.get("reference_si", "").strip()]
    if len(out) < 20:
        print(f"WARNING: only {len(out)} usable rows. Use at least 60 for a result you can trust.")
    return out


def run_nllb(sentences):
    from app.services.translator import translate_sentences
    return [nfc(x) for x in translate_sentences(sentences, "en", "si")]


def run_gemini(sentences, batch=10):
    from dotenv import load_dotenv
    from google import genai
    from google.genai import types

    load_dotenv()
    client = genai.Client(api_key=os.getenv("LLM_API_KEY"))
    model = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
    cfg = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)

    def ask(chunk):
        prompt = ("Translate each English sentence into natural, clear written Sinhala for university students. "
                  "Keep the meaning exact, keep tense and negation, keep numbers and names unchanged. "
                  "Return ONLY a JSON array of strings, same length and order.\n\n"
                  + json.dumps(chunk, ensure_ascii=False))
        for attempt in range(5):
            try:
                arr = json.loads(client.models.generate_content(model=model, contents=prompt, config=cfg).text)
                if isinstance(arr, list) and len(arr) == len(chunk):
                    return [nfc(str(x)) for x in arr]
                raise ValueError("length mismatch")
            except Exception as e:
                wait = 5 * (attempt + 1)
                print(f"  gemini retry in {wait}s ({type(e).__name__})")
                time.sleep(wait)
        return [""] * len(chunk)

    out = []
    for i in range(0, len(sentences), batch):
        out += ask(sentences[i:i + batch])
        time.sleep(2)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", default="data/mt/test_refs.csv")
    ap.add_argument("--outdir", default="data/mt")
    ap.add_argument("--systems", default="nllb,gemini", help="comma list: nllb,gemini")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    from sacrebleu.metrics import CHRF
    chrf = CHRF(word_order=2)                      # chrF++

    pairs = read_refs(a.test)
    src = [p[0] for p in pairs]
    ref = [p[1] for p in pairs]
    systems = [s.strip() for s in a.systems.split(",") if s.strip()]

    outputs = {}
    for name in systems:
        print(f"Translating {len(src)} sentences with {name} ...")
        outputs[name] = {"nllb": run_nllb, "gemini": run_gemini}[name](src)

    print("\n=== chrF++ against the human reference (higher is better, max 100) ===")
    for name in systems:
        print(f"{name:8s} {chrf.corpus_score(outputs[name], [ref]).score:6.2f}")

    if "nllb" in outputs:
        worst = sorted(range(len(src)),
                       key=lambda i: chrf.sentence_score(outputs["nllb"][i], [ref[i]]).score)[:5]
        print("\n=== 5 weakest NLLB sentences (look for the pattern: terms? tense? long sentences?) ===")
        for i in worst:
            print(f"EN : {src[i]}\nREF: {ref[i]}\nNLLB: {outputs['nllb'][i]}\n")

    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "eval_outputs.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["english", "reference_si"] + systems)
        for i in range(len(src)):
            w.writerow([src[i], ref[i]] + [outputs[s][i] for s in systems])

    if len(systems) >= 2:                          # blind sheet for human raters
        rng = random.Random(a.seed)
        with open(out / "rating_sheet.csv", "w", encoding="utf-8-sig", newline="") as fs, \
             open(out / "rating_key.csv", "w", encoding="utf-8-sig", newline="") as fk:
            ws, wk = csv.writer(fs), csv.writer(fk)
            ws.writerow(["english", "A", "B", "A_meaning_1to5", "A_fluency_1to5", "B_meaning_1to5", "B_fluency_1to5"])
            wk.writerow(["row", "A_is", "B_is"])
            for i in range(len(src)):
                order = systems[:2]
                rng.shuffle(order)
                ws.writerow([src[i], outputs[order[0]][i], outputs[order[1]][i], "", "", "", ""])
                wk.writerow([i + 2, order[0], order[1]])
    print(f"\nSaved to {out}: eval_outputs.csv, rating_sheet.csv, rating_key.csv")


if __name__ == "__main__":
    main()
