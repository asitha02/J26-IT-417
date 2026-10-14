"""Fine-tune XLM-RoBERTa on the exported comments (run on Google Colab / any GPU).

    python train.py --data data/comments.jsonl --out model_out

Splits 80/10/10 (stratified on sentiment), uses class-weighted losses because the data is
~76% neutral, picks the best epoch on validation macro-F1 and reports test metrics.
"""
import argparse
import json
import random
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader
from transformers import AutoTokenizer, get_linear_schedule_with_warmup

from model_def import BASE_MODEL, EMOTIONS, MAX_LEN, SENTIMENTS, FeedbackModel


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def encode_labels(row):
    return {
        "sentiment": SENTIMENTS.index(row["sentiment"]),
        "question": float(row["isQuestion"]),
        "emotions": [float(e in row["emotions"]) for e in EMOTIONS],
    }


def make_collate(tok):
    def collate(rows):
        enc = tok([r["text"] for r in rows], truncation=True, max_length=MAX_LEN, padding=True, return_tensors="pt")
        lab = [encode_labels(r) for r in rows]
        enc["sentiment"] = torch.tensor([l["sentiment"] for l in lab])
        enc["question"] = torch.tensor([l["question"] for l in lab])
        enc["emotions"] = torch.tensor([l["emotions"] for l in lab])
        return enc

    return collate


@torch.no_grad()
def predict(model, loader, device):
    model.eval()
    s_true, s_pred, q_true, q_pred, e_true, e_pred = [], [], [], [], [], []
    for b in loader:
        s, q, e = model(b["input_ids"].to(device), b["attention_mask"].to(device))
        s_true += b["sentiment"].tolist()
        s_pred += s.argmax(-1).cpu().tolist()
        q_true += b["question"].tolist()
        q_pred += (torch.sigmoid(q) > 0.5).int().cpu().tolist()
        e_true += b["emotions"].int().tolist()
        e_pred += (torch.sigmoid(e) > 0.5).int().cpu().tolist()
    return s_true, s_pred, q_true, q_pred, np.array(e_true), np.array(e_pred)


def macro_scores(model, loader, device):
    s_t, s_p, q_t, q_p, e_t, e_p = predict(model, loader, device)
    f_s = f1_score(s_t, s_p, average="macro", labels=range(len(SENTIMENTS)), zero_division=0)
    f_q = f1_score(q_t, q_p, average="macro", zero_division=0)
    f_e = f1_score(e_t, e_p, average="macro", zero_division=0)
    return f_s, f_q, f_e, (s_t, s_p, q_t, q_p, e_t, e_p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/comments.jsonl")
    ap.add_argument("--out", default="model_out")
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("device:", device)

    rows = load(args.data)
    strat = [r["sentiment"] for r in rows]
    train, rest = train_test_split(rows, test_size=0.2, stratify=strat, random_state=args.seed)
    dev, test = train_test_split(rest, test_size=0.5, stratify=[r["sentiment"] for r in rest], random_state=args.seed)
    print(f"train {len(train)}  dev {len(dev)}  test {len(test)}")
    print("sentiment (train):", Counter(r["sentiment"] for r in train))

    tok = AutoTokenizer.from_pretrained(BASE_MODEL)
    collate = make_collate(tok)
    train_dl = DataLoader(train, batch_size=args.batch, shuffle=True, collate_fn=collate)
    dev_dl = DataLoader(dev, batch_size=64, collate_fn=collate)
    test_dl = DataLoader(test, batch_size=64, collate_fn=collate)

    # Class weights counter the neutral-heavy imbalance.
    s_counts = np.array([sum(r["sentiment"] == s for r in train) for s in SENTIMENTS], dtype=float)
    s_w = torch.tensor(len(train) / (len(SENTIMENTS) * np.maximum(s_counts, 1)), dtype=torch.float).to(device)
    q_pos = sum(r["isQuestion"] for r in train)
    q_w = torch.tensor((len(train) - q_pos) / max(q_pos, 1)).to(device)
    e_pos = np.array([sum(e in r["emotions"] for r in train) for e in EMOTIONS], dtype=float)
    e_w = torch.tensor((len(train) - e_pos) / np.maximum(e_pos, 1), dtype=torch.float).to(device)

    s_loss = nn.CrossEntropyLoss(weight=s_w)
    q_loss = nn.BCEWithLogitsLoss(pos_weight=q_w)
    e_loss = nn.BCEWithLogitsLoss(pos_weight=e_w)

    model = FeedbackModel().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = len(train_dl) * args.epochs
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    scaler = torch.amp.GradScaler(enabled=device == "cuda")

    best, best_state = -1, None
    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for b in train_dl:
            opt.zero_grad()
            with torch.autocast(device_type=device, enabled=device == "cuda"):
                s, q, e = model(b["input_ids"].to(device), b["attention_mask"].to(device))
                loss = (
                    s_loss(s.float(), b["sentiment"].to(device))
                    + q_loss(q.float(), b["question"].to(device))
                    + e_loss(e.float(), b["emotions"].to(device))
                )
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            total += loss.item()
        f_s, f_q, f_e, _ = macro_scores(model, dev_dl, device)
        score = (f_s + f_q + f_e) / 3
        print(f"epoch {epoch}: loss {total / len(train_dl):.3f}  dev macro-F1 sentiment {f_s:.3f}  question {f_q:.3f}  emotions {f_e:.3f}")
        if score > best:
            best = score
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    f_s, f_q, f_e, (s_t, s_p, q_t, q_p, e_t, e_p) = macro_scores(model, test_dl, device)
    print("\n=== TEST (best epoch) ===")
    print(f"macro-F1  sentiment {f_s:.3f}  is_question {f_q:.3f}  emotions {f_e:.3f}")
    print(classification_report(s_t, s_p, target_names=SENTIMENTS, labels=range(len(SENTIMENTS)), zero_division=0))
    print(classification_report(q_t, q_p, target_names=["not question", "question"], zero_division=0))
    print(classification_report(e_t, e_p, target_names=EMOTIONS, zero_division=0))

    model.encoder.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    torch.save(model.heads_state(), f"{args.out}/heads.pt")
    with open(f"{args.out}/test_metrics.json", "w") as f:
        json.dump({"sentiment_macro_f1": f_s, "question_macro_f1": f_q, "emotion_macro_f1": f_e,
                   "n_train": len(train), "n_test": len(test)}, f, indent=2)
    print("saved to", args.out)


if __name__ == "__main__":
    main()
