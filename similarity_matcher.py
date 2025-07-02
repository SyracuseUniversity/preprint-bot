"""
A single‑file, end‑to‑end arXiv pre‑print recommender pipeline.

This script combines configuration, embedding utilities, hybrid similarity
matching, and a command‑line interface (CLI) into one place.  All you need
alongside it are the two _external_ helpers that you asked to keep intact:

* query_arxiv.py — must expose fetch_and_parse(category: str) and define
  SAVE_DIR where the parsed <arxiv_id>_output.txt files are written.
* extract_grobid.py — must expose process_folder(input_dir, output_dir)
  which parses PDFs into the same _output.txt format.

Pipeline stages
---------------
1. Fetch + parse latest arXiv PDFs for a chosen --category.
2. Parse the user’s own PDFs with GROBID so they share a common format.
3. Embed abstracts _and_ individual section chunks using a
   Sentence‑Transformers model (configurable via --model).
4. Match each user paper against every arXiv paper with a hybrid
   section‑wise FAISS search; keep matches above a cosine‑similarity threshold
   (--threshold).
5. Report ranked matches on stdout and write them to
   arxiv_pipeline_data/ranked_matches.json.

Quick start:
Recommend recent Computational Linguistics papers with default settings
python arxiv_recommender.py --category cs.CL --threshold medium

The script prints a numbered list of recommended arXiv titles, URLs and their
similarity scores.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import faiss  # type: ignore
import numpy as np
from sentence_transformers import SentenceTransformer

# Global configuration ─ modify these constants if needed
ARXIV_CATEGORIES: List[str] = [
    "astro-ph",  # example default; actual category chosen via CLI
]

SIMILARITY_THRESHOLDS: Dict[str, float] = {
    "low": 0.50,
    "medium": 0.70,
    "high": 0.85,
}

MAX_RESULTS: int = 400  # not used directly here but kept for completeness
DEFAULT_MODEL_NAME: str = "all-MiniLM-L6-v2"

# Where intermediate artefacts (e.g. ranked_matches.json) will be stored
DATA_DIR: str = "arxiv_pipeline_data"
os.makedirs(DATA_DIR, exist_ok=True)

# Embedding helpers

def load_model(model_name: str) -> SentenceTransformer:
    """Return a loaded `SentenceTransformer` model.

    Parameters
    ----------
    model_name : str
        HuggingFace model id, e.g. "all-MiniLM-L6-v2".

    Returns
    -------
    SentenceTransformer
        The ready‑to‑use embedding model.
    """
    return SentenceTransformer(model_name)


def embed_abstracts(
    processed_folder: str | Path,
    model_name: str,
) -> Tuple[List[str], np.ndarray, SentenceTransformer, List[str]]:
    """Embed the *title + abstract* of every parsed paper in a folder.

    The first two lines of each *_output.txt file are expected to be
    "Title: …" and "Abstract: …".  These lines are concatenated and
    encoded into a single semantic vector.
    """
    model = load_model(model_name)

    texts: List[str] = []
    filenames: List[str] = []

    for file in os.listdir(processed_folder):
        if not file.endswith("_output.txt"):
            continue
        file_path = Path(processed_folder) / file
        with file_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) < 2:
            print(f"Skipping malformed file: {file}")
            continue
        title = lines[0].replace("Title: ", "").strip()
        abstract = lines[1].replace("Abstract: ", "").strip()
        texts.append(f"{title}. {abstract}")
        filenames.append(file)

    if not texts:
        raise ValueError(
            f"No valid abstracts found in `{processed_folder}`. "
            "Ensure GROBID produced at least the title and abstract lines."
        )

    embeddings = model.encode(texts, convert_to_tensor=False, normalize_embeddings=True)  # type: ignore[arg-type]
    return texts, np.asarray(embeddings, dtype="float32"), model, filenames


def embed_sections(
    processed_folder: str | Path,
    model: SentenceTransformer,
) -> Dict[str, np.ndarray]:
    """Embed section chunks for each parsed paper individually.

    The function scans each *_output.txt file for lines starting with the
    pattern "- SectionName:".  Each section’s text is concatenated until the
    next header.  Sections shorter than 20 characters are ignored to avoid noise.
    """
    paper_sections: Dict[str, np.ndarray] = {}

    for file in os.listdir(processed_folder):
        if not file.endswith("_output.txt"):
            continue
        file_path = Path(processed_folder) / file
        with file_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        sections: List[Tuple[str, str]] = []
        current_header: str | None = None
        current_text: str = ""

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("- ") and ":" in stripped:
                # flush previous section
                if current_header and current_text:
                    sections.append((current_header, current_text.strip()))
                header, remainder = stripped.split(":", 1)
                current_header = header[2:].strip()  # drop the leading "- "
                current_text = remainder.strip()
            elif stripped:
                current_text += " " + stripped
        # append last
        if current_header and current_text:
            sections.append((current_header, current_text.strip()))

        chunk_embeddings: List[np.ndarray] = []
        for header, text in sections:
            if len(text) <= 20:
                continue  # skip trivial chunks
            emb = model.encode(text, convert_to_tensor=False, normalize_embeddings=True)  # type: ignore[arg-type]
            chunk_embeddings.append(emb)

        if chunk_embeddings:
            paper_sections[file] = np.asarray(chunk_embeddings, dtype="float32")

    return paper_sections

# Hybrid section‑wise similarity matching

def hybrid_similarity_pipeline(
    user_abs_embs: np.ndarray,
    arxiv_abs_embs: np.ndarray,
    user_sections_dict: Dict[str, np.ndarray],
    arxiv_sections_dict: Dict[str, np.ndarray],
    all_arxiv_papers: List[dict],
    user_files: List[str],
    threshold_label: str = "medium",
) -> List[dict]:
    """Compare user papers to arXiv papers using a *section‑level* FAISS search.

    For every arXiv paper we build an in‑memory FAISS index from its section
    vectors.  Every section of each user paper is queried against that index;
    the highest cosine similarity across all pairs becomes the *paper‑to‑paper*
    score.  Papers whose score exceeds the selected threshold are kept.

    Parameters
    ----------
    user_abs_embs, arxiv_abs_embs
        Unused in the current implementation but kept for extensibility
        (e.g. you may want to blend abstract‑level scores later).
    user_sections_dict, arxiv_sections_dict
        Mapping filename -> np.ndarray of section embeddings.
    all_arxiv_papers : list[dict]
        Metadata list returned by query_arxiv.fetch_and_parse; each dict must
        include keys title, summary, arxiv_url, published.
    user_files : list[str]
        Filenames (keys into *user_sections_dict*) corresponding to each user
        paper, used to align matches.
    threshold_label : {"low","medium","high"}
        Selects a predefined cosine‑similarity cut‑off.

    Returns
    -------
    list[dict]
        Sorted list of matches with keys title, summary, url,
        published and score.
    """

    threshold = SIMILARITY_THRESHOLDS.get(threshold_label, 0.70)
    matches: List[dict] = []

    for paper in all_arxiv_papers:
        arxiv_id_version = paper["arxiv_url"].split("/")[-1]
        arxiv_key = f"{arxiv_id_version}_output.txt"
        arxiv_chunks = arxiv_sections_dict.get(arxiv_key)
        if arxiv_chunks is None or len(arxiv_chunks) == 0:
            continue

        # Prepare FAISS index for this arXiv paper
        arxiv_chunks = arxiv_chunks.astype("float32")
        faiss.normalize_L2(arxiv_chunks)
        dim = arxiv_chunks.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(arxiv_chunks)

        for user_file in user_files:
            user_chunks = user_sections_dict.get(user_file)
            if user_chunks is None or len(user_chunks) == 0:
                continue
            user_chunks = user_chunks.astype("float32")
            faiss.normalize_L2(user_chunks)
            scores, _ = index.search(user_chunks, k=1)
            best_score = float(np.max(scores))
            if best_score >= threshold:
                matches.append(
                    {
                        "title": paper["title"],
                        "summary": paper["summary"],
                        "url": paper["arxiv_url"],
                        "published": paper["published"],
                        "score": best_score,
                    }
                )

    matches.sort(key=lambda m: m["score"], reverse=True)

    with Path(DATA_DIR, "ranked_matches.json").open("w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2)

    return matches

# Main orchestration entrypoint

def main(
    category: str,
    threshold_label: str = "medium",
    model_name: str = DEFAULT_MODEL_NAME,
) -> None:
    """Run the full recommendation pipeline.

    This function glues together fetching, parsing, embedding and matching.
    The heavy‑lifting helpers are imported only inside this function so that the
    module can still be imported without their presence (useful for unit tests).

    Parameters
    ----------
    category : str
        arXiv subject category code, e.g. "cs.CL" or "astro-ph".
    threshold_label : {"low","medium","high"}
        Similarity cut‑off to use.
    model_name : str
        Sentence‑Transformers model id.
    """

    import query_arxiv  # local module (kept intact)
    from extract_grobid import process_folder  # local module (kept intact)

    user_pdf_folder = "my_papers"
    user_processed = Path(DATA_DIR) / "processed_users"
    arxiv_processed = Path(query_arxiv.SAVE_DIR)

    # 1. Fetch + parse arXiv
    print(f"\nFetching + parsing latest arXiv papers in '{category}' …")
    all_papers = query_arxiv.fetch_and_parse(category)

    # 2. Parse user PDFs with GROBID
    print("\nParsing user PDFs with GROBID …")
    process_folder(user_pdf_folder, user_processed)

    # 3. Embed abstracts
    print("\nEmbedding abstracts …")
    _, user_abs_embs, model, user_files = embed_abstracts(user_processed, model_name)
    _, arxiv_abs_embs, _, _ = embed_abstracts(arxiv_processed, model_name)

    # 4. Embed sections
    print("Embedding section chunks …")
    user_sections = embed_sections(user_processed, model)
    arxiv_sections = embed_sections(arxiv_processed, model)

    # 5. Similarity matching
    print("\nMatching papers …")
    matches = hybrid_similarity_pipeline(
        user_abs_embs,
        arxiv_abs_embs,
        user_sections,
        arxiv_sections,
        all_papers,
        user_files,
        threshold_label,
    )

    # 6. Report
    print(f"\n{len(matches)} match(es) found (threshold = '{threshold_label}'):\n")
    for i, m in enumerate(matches, start=1):
        print(f"{i}. {m['title']}\n   {m['url']}\n   score = {m['score']:.3f}\n")

# CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recommend recently uploaded arXiv papers relevant to your PDFs",
    )
    parser.add_argument(
        "--category",
        default="cs.CL",
        help="arXiv category code, e.g. cs.CL, astro-ph",
    )
    parser.add_argument(
        "--threshold",
        default="medium",
        choices=list(SIMILARITY_THRESHOLDS.keys()),
        help="Similarity threshold label: low | medium | high",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_NAME,
        help="Sentence-Transformers model id",
    )
    cli_args = parser.parse_args()
    main(cli_args.category, cli_args.threshold, cli_args.model)
