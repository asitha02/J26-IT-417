import numpy as np
from app.services.embedding import embed_texts, similarity_matrix

texts = [
    "Gradient descent minimizes a loss function.",
    "Gradient descent is an optimization algorithm used to reduce the loss.",
    "The capital of France is Paris.",
    "Neural networks are trained using backpropagation.",
    # add a Sinhala translation of sentence 1 here to test cross-language similarity
]

sim = similarity_matrix(embed_texts(texts))
np.set_printoptions(precision=2, suppress=True)
print(sim)