import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "project_j417")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.0"))
MIN_UNIT_CHARS = int(os.getenv("MIN_UNIT_CHARS", "15"))

SIM_THRESHOLD = float(os.getenv("SIM_THRESHOLD", "0.85"))