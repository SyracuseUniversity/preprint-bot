#!/usr/bin/env python3
"""
End-to-End arXiv Preprint Recommender

This single script stitches together all the separate building blocks you already wrote—fetching, PDF download, GROBID parsing, summarisation, embedding and similarity matching—into one coherent command-line pipeline.

Main stages
-----------
Fetch the most recent pre-prints for a chosen arXiv category (via the helper in query_arxiv.py).

Download their PDFs and store them on disk (re-uses download_arxiv_pdfs.py).

Parse every PDF through GROBID and save a plain-text _output.txt for each (grobid_parser.py).

Summarise each parsed paper with a transformer model (functions from summarization_script.py).

Embed abstracts and section chunks for both the user’s uploaded papers and the fresh arXiv papers (embed_papers.py).

Match user vs arXiv papers with a hybrid FAISS search and rank them (similarity_matcher.py).

Report the recommendations – title, link, transformer summary (or abstract fallback) and similarity score.

Usage
-----
python pipeline.py --category cs.LG --threshold medium --model all-MiniLM-L6-v2

Skipping expensive steps:
Add the below in your command line to skip downloading, parsing, summarising or embedding steps:
--skip_download	- Skips downloading arXiv PDFs
--skip_parse - Skips parsing PDFs through GROBID
--skip_summarize - Skips summarizing parsed texts
--skip_embed - Skips generating embeddings for all papers

Prerequisites
-------------
• GROBID running locally on http://localhost:8070
• transformers, sentence-transformers, faiss, nltk, etc. installed
• Rename summarization-script.py to summarization_script.py so it can be imported as a Python module
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import feedparser  # only needed for very quick metadata conversion

# Local project imports
from .config import DATA_DIR, DEFAULT_MODEL_NAME
from .download_arxiv_pdfs import download_arxiv_pdfs
from .embed_papers import embed_abstracts, embed_sections
from .extract_grobid import process_folder as grobid_process_folder
from .query_arxiv import get_recent_arxiv_entries
from .similarity_matcher import hybrid_similarity_pipeline
from .summarization_script import process_folder

# Folder layout (overrides welcome via environment variables)
USER_PDF_FOLDER      = os.getenv("USER_PDF_FOLDER", "user_pdfs")
ARXIV_PDF_FOLDER     = os.path.join(DATA_DIR, "arxiv_pdfs")
USER_PROCESSED       = os.path.join(DATA_DIR, "processed_users")
ARXIV_PROCESSED      = os.path.join(DATA_DIR, "processed_arxiv")
ARXIV_SUMMARY_FOLDER = os.path.join(DATA_DIR, "summaries_arxiv")

for p in [ARXIV_PDF_FOLDER, USER_PROCESSED, ARXIV_PROCESSED, ARXIV_SUMMARY_FOLDER]:
    os.makedirs(p, exist_ok=True)

# Helpers
import tkinter as tk
from tkinter import filedialog

def browse_for_folder(prompt="Select a folder containing your PDFs"):
    """Displays a pop-up which allows the user to select the folder in which the research papers are"""
    root = tk.Tk()
    root.withdraw()  # hide the main window
    folder_selected = filedialog.askdirectory(title=prompt)
    return folder_selected


def fetch_and_parse_arxiv(category: str, max_results: int = 5, *, skip_download: bool = False, skip_parse: bool = False):
    """Return a list of metadata dicts for freshly‑fetched arXiv papers.

    Each dict has keys: id (e.g. 2406.12345v1), title, summary (abstract),
    published, arxiv_url.  PDFs are downloaded to *ARXIV_PDF_FOLDER* and parsed
    to *ARXIV_PROCESSED*.
    """
    print(f"\n▶ Fetching {max_results} most recent papers from {category}…")
    entries = get_recent_arxiv_entries(category=category, max_results=max_results)

    # Convert feedparser entries → simple dicts expected by downstream code.
    papers = []
    for e in entries:
        arxiv_id = e.id.split("/")[-1]  # e.g. 2406.12345v1
        papers.append({
            "title":      e.title.strip(),
            "summary":    e.summary.strip(),
            "published":  getattr(e, "published", ""),
            "arxiv_url":  e.id,
            "arxiv_id":   arxiv_id,
        })

    if skip_download and skip_parse:
        return papers

    # 1) Download PDFs 
    if not skip_download:
        download_arxiv_pdfs(papers, output_folder=ARXIV_PDF_FOLDER, delay_seconds=2)
    else:
        print("Skipping PDF download (assumed complete).")

    # 2) Parse PDFs through GROBID 
    if not skip_parse:
        print("\n▶ Parsing arXiv PDFs with GROBID…")
        grobid_process_folder(ARXIV_PDF_FOLDER, ARXIV_PROCESSED)
    else:
        print("Skipping GROBID parsing (assumed complete).")

    return papers


def summarise_arxiv(skip_summarize: bool = False):
    """Generate transformer summaries for every *_summary.txt in ARXIV_PROCESSED."""
    if skip_summarize:
        print("Skipping summarisation step.")
        return

    print("\n▶ Generating transformer summaries (this can be slow)…")
    process_folder(ARXIV_PROCESSED, ARXIV_SUMMARY_FOLDER, max_length=180)


def load_summary_map() -> dict[str, str]:
    """Return {arxiv_id: summary_text}. Falls back to empty dict if none."""
    mapping = {}
    for fp in Path(ARXIV_SUMMARY_FOLDER).glob("*_summary.txt"):
        raw_id = fp.stem.replace("_summary", "")
        arxiv_id = raw_id.split("v")[0]  # normalize ID by removing version
        try:
            mapping[arxiv_id] = fp.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"Could not read summary {fp}: {e}")
    return mapping


def embed_corpora(model_name: str, method: str, *, skip_embed: bool = False):
    """
    Return embeddings + model + filenames for both user and arXiv corpora.
    Ensures embeddings are compatible with the chosen method.
    """
    print("\n▶ Embedding abstracts…")
    if skip_embed:
        print("Skipping embedding, loading existing embeddings from disk…")
    user_abs_texts, user_abs_embs, model, user_files = embed_abstracts(USER_PROCESSED, model_name)
    arxiv_abs_texts, arxiv_abs_embs, _, _     = embed_abstracts(ARXIV_PROCESSED, model_name)

    print("▶ Embedding section chunks…")
    user_sections  = embed_sections(USER_PROCESSED,  model)
    arxiv_sections = embed_sections(ARXIV_PROCESSED, model)

    # Normalize only for FAISS
    if method == "faiss":
        import numpy as np
        for key in user_sections:
            user_sections[key] = np.array(user_sections[key], dtype="float32")
            user_sections[key] /= np.linalg.norm(user_sections[key], axis=1, keepdims=True) + 1e-10
        for key in arxiv_sections:
            arxiv_sections[key] = np.array(arxiv_sections[key], dtype="float32")
            arxiv_sections[key] /= np.linalg.norm(arxiv_sections[key], axis=1, keepdims=True) + 1e-10

    return (user_abs_embs, arxiv_abs_embs, user_sections, arxiv_sections, user_files)


def normalize_arxiv_id(arxiv_id_with_version: str) -> str:
    """Strip version suffix from arXiv ID, e.g. '2507.13255v1' → '2507.13255'"""
    return arxiv_id_with_version.split("v")[0]


# Main driver

def main():
    parser = argparse.ArgumentParser(description="Run the full arXiv→recommendation pipeline.")
    parser.add_argument("--category",  default="cs.CL")
    parser.add_argument("--threshold", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--model",     default=DEFAULT_MODEL_NAME)
    parser.add_argument("--method",    default="faiss", choices=["faiss", "cosine", "qdrant"], help="Similarity backend")
    parser.add_argument("--skip-download",   action="store_true")
    parser.add_argument("--skip-parse",      action="store_true")
    parser.add_argument("--skip-summarize",  action="store_true")
    parser.add_argument("--skip-embed",      action="store_true")
    parser.add_argument("--user-folder",     help="Path to user PDFs (if not set, a browse dialog will appear)")

    args = parser.parse_args()

    # If no folder provided, show browse dialog
    user_pdf_folder = args.user_folder or browse_for_folder()

    if not user_pdf_folder:
        print("❌ No folder selected, exiting.")
        sys.exit(1)

    global USER_PDF_FOLDER
    USER_PDF_FOLDER = user_pdf_folder

    if not os.listdir(USER_PROCESSED):
        print("\nParsing user PDFs with GROBID…")
        grobid_process_folder(USER_PDF_FOLDER, USER_PROCESSED)
    else:
        print("User PDFs already parsed → skipping.")

    papers_meta = fetch_and_parse_arxiv(
        category=args.category,
        skip_download=args.skip_download,
        skip_parse=args.skip_parse,
    )

    summarise_arxiv(skip_summarize=args.skip_summarize)
    summary_map = load_summary_map()

    user_abs_embs, arxiv_abs_embs, user_sections, arxiv_sections, user_files = embed_corpora(
        model_name=args.model,
        method=args.method,
        skip_embed=args.skip_embed
    )

    print(f"\n▶ Performing hybrid similarity search with method = {args.method} …")
    matches = hybrid_similarity_pipeline(
        user_abs_embs, arxiv_abs_embs,
        user_sections, arxiv_sections,
        papers_meta, user_files,
        threshold_label=args.threshold,
        method=args.method,
    )

    if not matches:
        print("\nNo matches above threshold. Try lowering --threshold?\n")
        sys.exit(0)

    print(f"\nFound {len(matches)} relevant papers:\n")

    unique_matches = {}
    for m in matches:
        arxiv_id_with_version = m["url"].split("/")[-1]
        arxiv_id = normalize_arxiv_id(arxiv_id_with_version)
        summary = summary_map.get(arxiv_id, m["summary"])

        if (m["url"] not in unique_matches) or (m["score"] > unique_matches[m["url"]]["score"]):
            unique_matches[m["url"]] = {
                "title": m["title"],
                "summary": summary,
                "url": m["url"],
                "published": m.get("published", ""),
                "score": m["score"],
            }

    output_matches = list(unique_matches.values())
    output_matches.sort(key=lambda x: x["score"], reverse=True)

    output_path = "pdf_processes/ranked_matches.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_matches, f, indent=2)

    print(f"\n✅ Saved ranked matches to: {output_path}")


if __name__ == "__main__":
    main()