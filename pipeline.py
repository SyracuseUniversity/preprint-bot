"""
End-to-End arXiv Preprint Recommender

This single script stitches together all the separate building blocks you already wrote—fetching, PDF download, GROBID parsing, summarisation, embedding and similarity matching—into one coherent command-line pipeline.

Main stages

Fetch the most recent pre-prints for a chosen arXiv category (via the helper in query_arxiv.py).

Download their PDFs and store them on disk (re-uses download_arxiv_pdfs.py).

Parse every PDF through GROBID and save a plain-text _output.txt for each (grobid_parser.py).

Summarise each parsed paper with a transformer model (functions from summarization_script.py).

Embed abstracts and section chunks for both the user’s uploaded papers and the fresh arXiv papers (embed_papers.py).

Match user vs arXiv papers with a hybrid FAISS search and rank them (similarity_matcher.py).

Report the recommendations – title, link, transformer summary (or abstract fallback) and similarity score.

Usage
python end_to_end_pipeline.py --category cs.CL --threshold medium --model all-MiniLM-L6-v2

SKipping expensive steps:
Add the below in your command line to skip downloading, parsing, summarising or embedding steps:
--skip_download	- Skips downloading arXiv PDFs
--skip_parse - Skips parsing PDFs through GROBID
--skip_summarize - Skips summarizing parsed texts
--skip_embed - Skips generating embeddings for all papers

Prerequisites
• GROBID running locally on http://localhost:8070
• transformers, sentence-transformers, faiss, nltk, etc. installed
• Rename summarization-script.py to summarization_script.py so it can be imported as a Python module
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import feedparser  # only needed for very quick metadata conversion

#Local project imports 
from config import DATA_DIR, DEFAULT_MODEL_NAME
from download_arxiv_pdfs import download_arxiv_pdfs
from embed_papers import embed_abstracts, embed_sections
from grobid_parser import extract_grobid_sections, process_folder as grobid_process_folder
from query_arxiv import get_recent_arxiv_entries
from similarity_matcher import hybrid_similarity_pipeline

# NB: the file was originally named summarization-script.py.  Make sure it has an
# underscore so Python can import it.
try:
    import summarization_script as summariser
except ModuleNotFoundError as e:
    print("Could not import `summarization_script`")
    raise e

# Folder layout (overrides welcome via environment variables)                   #
USER_PDF_FOLDER      = os.getenv("USER_PDF_FOLDER", "my_papers")
ARXIV_PDF_FOLDER     = os.path.join(DATA_DIR, "arxiv_pdfs")
USER_PROCESSED       = os.path.join(DATA_DIR, "processed_users")
ARXIV_PROCESSED      = os.path.join(DATA_DIR, "processed_arxiv")
ARXIV_SUMMARY_FOLDER = os.path.join(DATA_DIR, "summaries_arxiv")

for p in [ARXIV_PDF_FOLDER, USER_PROCESSED, ARXIV_PROCESSED, ARXIV_SUMMARY_FOLDER]:
    os.makedirs(p, exist_ok=True)

# Helpers                                                                       #

def fetch_and_parse_arxiv(category: str, max_results: int = 20 , *, skip_download: bool = False, skip_parse: bool = False):
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

    # 1) Download PDFs ----
    if not skip_download:
        download_arxiv_pdfs(papers, output_folder=ARXIV_PDF_FOLDER, delay_seconds=2)
    else:
        print("⏩  Skipping PDF download (assumed complete).")

    # 2) Parse PDFs through GROBID -------------------------------------------
    if not skip_parse:
        print("\n▶ Parsing arXiv PDFs with GROBID…")
        grobid_process_folder(ARXIV_PDF_FOLDER, ARXIV_PROCESSED)
    else:
        print("⏩  Skipping GROBID parsing (assumed complete).")

    return papers


def summarise_arxiv(skip_summarize: bool = False):
    """Generate transformer summaries for every *_output.txt in ARXIV_PROCESSED."""
    if skip_summarize:
        print("⏩  Skipping summarisation step.")
        return

    print("\n▶ Generating transformer summaries (this can be slow)…")
    summariser.process_folder(ARXIV_PROCESSED, ARXIV_SUMMARY_FOLDER, max_length=180)


def load_summary_map() -> dict[str, str]:
    """Return {arxiv_id: summary_text}.  Falls back to empty dict if none."""
    mapping = {}
    for fp in Path(ARXIV_SUMMARY_FOLDER).glob("*_summary.txt"):
        arxiv_id = fp.stem.replace("_summary", "")  # strip suffix
        try:
            mapping[arxiv_id] = fp.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"⚠️  Could not read summary {fp}: {e}")
    return mapping


def embed_corpora(model_name: str, *, skip_embed: bool = False):
    """Return embeddings + model + filenames for both user and arXiv corpora."""
    print("\n▶ Embedding abstracts…")
    user_abs_texts, user_abs_embs, model, user_files = embed_abstracts(USER_PROCESSED, model_name)
    arxiv_abs_texts, arxiv_abs_embs, _, _     = embed_abstracts(ARXIV_PROCESSED, model_name)

    print("▶ Embedding section chunks…")
    user_sections  = embed_sections(USER_PROCESSED,  model)
    arxiv_sections = embed_sections(ARXIV_PROCESSED, model)

    return (user_abs_embs, arxiv_abs_embs, user_sections, arxiv_sections, user_files)


# Main driver                                                                   #

def main():
    parser = argparse.ArgumentParser(description="Run the full arXiv→recommendation pipeline.")
    parser.add_argument("--category",  default="cs.CL", help="arXiv subject class, e.g. cs.CL, stat.ML …")
    parser.add_argument("--threshold", default="medium", choices=["low", "medium", "high"], help="Similarity threshold label (see config.py).")
    parser.add_argument("--model",     default=DEFAULT_MODEL_NAME, help="Sentence‑Transformer model name.")

    # Convenience flags to skip expensive work on dev re‑runs
    parser.add_argument("--skip-download",   action="store_true")
    parser.add_argument("--skip-parse",      action="store_true")
    parser.add_argument("--skip-summarize",  action="store_true")
    parser.add_argument("--skip-embed",      action="store_true")  # mostly not used; embed step is fast

    args = parser.parse_args()

    # Step 0 ‑ ensure user PDFs are parsed -----------------------------------
    if not os.listdir(USER_PROCESSED):
        print("\n▶ Parsing user PDFs with GROBID…")
        grobid_process_folder(USER_PDF_FOLDER, USER_PROCESSED)
    else:
        print("⏩  User PDFs already parsed → skipping.")

    # Step 1/2/3 ‑ fetch, download, parse ------------------------------------
    papers_meta = fetch_and_parse_arxiv(
        category=args.category,
        skip_download=args.skip_download,
        skip_parse=args.skip_parse,
    )

    # Step 4 ‑ summarise --
    summarise_arxiv(skip_summarize=args.skip_summarize)
    summary_map = load_summary_map()

    # Step 5 ‑ embed ------
    user_abs_embs, arxiv_abs_embs, user_sections, arxiv_sections, user_files = embed_corpora(
        model_name=args.model,
    )

    # Step 6 ‑ similarity search ---------------------------------------------
    print("\n▶ Performing hybrid similarity search…")
    matches = hybrid_similarity_pipeline(
        user_abs_embs, arxiv_abs_embs,
        user_sections, arxiv_sections,
        papers_meta, user_files,
        threshold_label=args.threshold,
    )

    # Step 7 ‑ collate & print results ---------------------------------------
    if not matches:
        print("\n😔  No matches above threshold.  Try lowering --threshold?\n")
        sys.exit(0)

    print(f"\n★ Found {len(matches)} relevant papers:\n")
    for rank, m in enumerate(matches, 1):
        arxiv_id = m["url"].split("/")[-1]
        summary   = summary_map.get(arxiv_id, m["summary"])  # transformer summary OR arXiv abstract

        print(f"{rank}. {m['title']}")
        print(f"   {m['url']}")
        print(f"   Similarity score: {m['score']:.3f}")
        print("   Summary:")
        print(f"   {summary}\n")


if __name__ == "__main__":
    main()
