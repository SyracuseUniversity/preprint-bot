"""
Module to define global constants and create necessary directories
for the arXiv preprint recommendation pipeline.

This configuration includes:
- Supported arXiv categories
- Similarity thresholds for filtering relevant papers
- Default embedding model
- Directory setup for storing data outputs
"""

import os

# List of arXiv subject categories to query. Add more categories this as needed.
ARXIV_CATEGORIES = [
    # Astrophysics category from arXiv
    "cs.LG", 
]

# Predefined similarity thresholds for filtering paper recommendations
# These represent cosine similarity scores between embedding vectors
SIMILARITY_THRESHOLDS = {
    "low": 0.5,     # Broad match
    "medium": 0.6,  # Balanced relevance
    "high": 0.75   # Very high relevance
}

# Maximum number of results to retrieve per query from arXiv
MAX_RESULTS = 10

# Default SentenceTransformer model used for embedding abstracts and sections
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

# Root directory for saving intermediate and final outputs from the pipeline
DATA_DIR = "pdf_processes"

# Create the data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)
