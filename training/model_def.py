"""Multi-task model shared by train.py and serve.py.

One XLM-RoBERTa encoder, three heads: sentiment (3-way), is_question (binary),
emotions (multi-label). Only emotions with enough training data are modelled.
"""
import torch
import torch.nn as nn
from transformers import AutoModel

BASE_MODEL = "xlm-roberta-base"
SENTIMENTS = ["positive", "negative", "neutral"]
# Agreement / Disagreement / Confusion / Frustration have too few labelled examples (<50) to learn.
EMOTIONS = ["Enthusiasm", "Curiosity"]
MAX_LEN = 128


class FeedbackModel(nn.Module):
    def __init__(self, base=BASE_MODEL, encoder=None):
        super().__init__()
        self.encoder = encoder or AutoModel.from_pretrained(base)
        hidden = self.encoder.config.hidden_size
        self.dropout = nn.Dropout(0.1)
        self.sentiment = nn.Linear(hidden, len(SENTIMENTS))
        self.question = nn.Linear(hidden, 1)
        self.emotions = nn.Linear(hidden, len(EMOTIONS))

    def forward(self, input_ids, attention_mask):
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        pooled = self.dropout(out.last_hidden_state[:, 0])
        return self.sentiment(pooled), self.question(pooled).squeeze(-1), self.emotions(pooled)

    def heads_state(self):
        return {k: v for k, v in self.state_dict().items() if not k.startswith("encoder.")}
