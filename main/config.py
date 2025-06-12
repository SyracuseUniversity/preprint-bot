import os

ARXIV_CATEGORIES = [
    "astro-ph", "astro-ph.CO", "astro-ph.EP", "astro-ph.GA", "astro-ph.HE", "astro-ph.IM", "astro-ph.SR",
]

SIMILARITY_THRESHOLDS = {
    "low": 0.5,
    "medium": 0.7,
    "high": 0.85
}

MAX_RESULTS = 100
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DATA_DIR = "arxiv_pipeline_data"

os.makedirs(DATA_DIR, exist_ok=True)
