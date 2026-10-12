import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.embedding import embed_texts


def resolve_data_path(raw_path: str | None) -> Path:
    if raw_path:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidates = [Path.cwd() / candidate, ROOT / candidate]
            for option in candidates:
                if option.exists():
                    return option.resolve()
            return (ROOT / candidate).resolve()
        return candidate.resolve()

    candidates = [
        ROOT / "app" / "evaluation" / "evaluation" / "pairs.csv",
        ROOT / "evaluation" / "pairs.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def main() -> None:
    path = resolve_data_path(sys.argv[1] if len(sys.argv) > 1 else None)
    model = sys.argv[2] if len(sys.argv) > 2 else None

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise ValueError(f"No rows found in evaluation file: {path}")

    a = embed_texts([r["text_a"] for r in rows], model_name=model)
    b = embed_texts([r["text_b"] for r in rows], model_name=model)
    scores = (a * b).sum(axis=1)
    labels = np.array([int(r["label"]) for r in rows])

    print(f"model: {model or 'default'}   pairs: {len(rows)}")
    print("threshold  precision  recall   f1")
    for t in np.arange(0.70, 0.96, 0.05):
        pred = scores >= t
        tp = int((pred & (labels == 1)).sum())
        fp = int((pred & (labels == 0)).sum())
        fn = int((~pred & (labels == 1)).sum())
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        print(f"{t:.2f}       {p:.3f}      {r:.3f}    {f:.3f}")


if __name__ == "__main__":
    main()