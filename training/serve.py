"""Serve the trained model for the Node server (ANALYZER=model).

    uvicorn serve:app --port 8001          # MODEL_DIR=model_out by default
"""
import os

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModel, AutoTokenizer

from model_def import EMOTIONS, MAX_LEN, SENTIMENTS, FeedbackModel

MODEL_DIR = os.getenv("MODEL_DIR", "model_out")
device = "cuda" if torch.cuda.is_available() else "cpu"

tok = AutoTokenizer.from_pretrained(MODEL_DIR)
model = FeedbackModel(encoder=AutoModel.from_pretrained(MODEL_DIR))
model.load_state_dict(torch.load(f"{MODEL_DIR}/heads.pt", map_location="cpu"), strict=False)
model.to(device).eval()

app = FastAPI(title="feedback model")


class Item(BaseModel):
    id: str
    text: str


class Batch(BaseModel):
    items: list[Item]


@app.get("/health")
def health():
    return {"ok": True, "device": device}


@app.post("/predict")
@torch.no_grad()
def predict(batch: Batch):
    results = []
    for i in range(0, len(batch.items), 64):
        chunk = batch.items[i : i + 64]
        enc = tok([c.text for c in chunk], truncation=True, max_length=MAX_LEN, padding=True, return_tensors="pt").to(device)
        s, q, e = model(enc["input_ids"], enc["attention_mask"])
        s_idx = s.argmax(-1).cpu().tolist()
        q_p = (torch.sigmoid(q) > 0.5).cpu().tolist()
        e_p = (torch.sigmoid(e) > 0.5).cpu().tolist()
        for c, si, qi, ei in zip(chunk, s_idx, q_p, e_p):
            results.append({
                "id": c.id,
                "sentiment": SENTIMENTS[si],
                "emotions": [EMOTIONS[j] for j, on in enumerate(ei) if on],
                "isQuestion": bool(qi),
            })
    return {"results": results}
