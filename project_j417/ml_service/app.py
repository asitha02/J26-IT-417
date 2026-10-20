"""RoBERTa sentiment service. The Node backend (ANALYZER=bert) posts comments here.

Run: py -m pip install -r ml_service/requirements.txt
     py -m uvicorn app:app --port 8001   (from inside ml_service/)
"""
import os
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline

MODEL = os.getenv("SENTIMENT_MODEL", "cardiffnlp/twitter-xlm-roberta-base-sentiment")

app = FastAPI(title="Sentiment service")
clf = pipeline("sentiment-analysis", model=MODEL, truncation=True, max_length=256)


class Item(BaseModel):
    id: str
    text: str


class Request(BaseModel):
    items: list[Item]


@app.get("/health")
def health():
    return {"model": MODEL}


@app.post("/sentiment")
def sentiment(req: Request):
    preds = clf([i.text for i in req.items], batch_size=16)
    return {
        "results": [
            {"id": i.id, "sentiment": p["label"].lower(), "score": float(p["score"])}
            for i, p in zip(req.items, preds)
        ]
    }
