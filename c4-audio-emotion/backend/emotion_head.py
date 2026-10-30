"""
My trained emotion head: BiLSTM + attention on top of CLAP embeddings.

This class MUST stay identical to EmotionHead in notebooks/02_train_emotion_head.ipynb:
PyTorch saves only the numbers (weights), not the code, so the backend has to
rebuild exactly the same network before it can load c4_emotion_head.pt.

- BiLSTM: reads the windows forwards and backwards, so each window's prediction
  can use what comes before and after it.
- Attention: each window can look directly at the most relevant other windows.
- tanh: squeezes the 2 outputs (valence, arousal) into [-1, 1].
"""
import torch
import torch.nn as nn


class EmotionHead(nn.Module):
    def __init__(self, input_dim=512, hidden=128, use_attention=True, dropout=0.3):
        super().__init__()
        self.use_attention = use_attention
        self.dropout = nn.Dropout(dropout)
        self.bilstm = nn.LSTM(input_dim, hidden, batch_first=True, bidirectional=True)
        if use_attention:
            self.attention = nn.MultiheadAttention(2 * hidden, num_heads=1, batch_first=True)
            self.norm = nn.LayerNorm(2 * hidden)
        self.out = nn.Linear(2 * hidden, 2)          # 2 outputs: valence, arousal

    def forward(self, x, mask):
        # x: (batch, windows, 512), mask: (batch, windows) True = real window
        h, _ = self.bilstm(self.dropout(x))          # (batch, windows, 2*hidden)
        if self.use_attention:
            context, weights = self.attention(h, h, h, key_padding_mask=~mask)
            h = self.norm(h + context)               # keep the BiLSTM info and add the attention summary
        return torch.tanh(self.out(self.dropout(h)))
