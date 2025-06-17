import os

ARXIV_CATEGORIES = [
    # Astrophysics
    "astro-ph", 
]


SIMILARITY_THRESHOLDS = {
    "low": 0.5,
    "medium": 0.7,
    "high": 0.85
}

MAX_RESULTS = 50
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DATA_DIR = "arxiv_pipeline_data"

os.makedirs(DATA_DIR, exist_ok=True)
