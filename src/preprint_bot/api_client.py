"""
Module to define global constants and create necessary directories
for the arXiv preprint recommendation pipeline.
"""

import os
from pathlib import Path

# List of arXiv subject categories to query
ARXIV_CATEGORIES = [
    "cs.LG", 
]

# Predefined similarity thresholds for filtering paper recommendations
SIMILARITY_THRESHOLDS = {
    "low": 0.5,
    "medium": 0.6,
    "high": 0.75
}

# Maximum number of results to retrieve per query from arXiv
MAX_RESULTS = 50

# Default SentenceTransformer model used for embedding abstracts and sections
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

# Root directory for storing files (NOT metadata - that goes to DB)
DATA_DIR = Path("hometutor_data")

# Subdirectories for different file types
PDF_DIR = DATA_DIR / "pdfs"
PROCESSED_TEXT_DIR = DATA_DIR / "processed_texts"
USER_PDF_DIR = DATA_DIR / "user_pdfs"
USER_PROCESSED_DIR = DATA_DIR / "user_processed"

# Create all necessary directories
for directory in [DATA_DIR, PDF_DIR, PROCESSED_TEXT_DIR, USER_PDF_DIR, USER_PROCESSED_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# Default user for system operations
SYSTEM_USER_EMAIL = os.getenv("SYSTEM_USER_EMAIL", "system@hometutor.local")
SYSTEM_USER_NAME = "HomeTutor System"

# Corpus names
ARXIV_CORPUS_NAME = "arxiv_papers"