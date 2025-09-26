from __future__ import annotations # This has to stay at the top most position
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

#!/usr/bin/env python3
"""
End-to-End arXiv Preprint Recommender with flexible summary mode

Summary mode (--summary-mode) can be:
- abstract: summarize only paper abstracts (default)
- full: summarize full paper text sections
"""

import argparse
import json
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import feedparser

# Local project imports
from .config import DATA_DIR, DEFAULT_MODEL_NAME, MAX_RESULTS
from .download_arxiv_pdfs import download_arxiv_pdfs
from .embed_papers import embed_abstracts, embed_sections
from .extract_grobid import process_folder as grobid_process_folder
from .query_arxiv import get_recent_arxiv_entries, write_all_json
from .similarity_matcher import hybrid_similarity_pipeline
from .summarization_script import (
    process_folder, TransformerSummarizer, LlamaSummarizer, process_metadata
)

# Folder layout
USER_PDF_FOLDER      = os.getenv("USER_PDF_FOLDER", "user_pdfs")
ARXIV_PDF_FOLDER     = os.path.join(DATA_DIR, "arxiv_pdfs")
USER_PROCESSED       = os.path.join(DATA_DIR, "processed_users")
ARXIV_PROCESSED      = os.path.join(DATA_DIR, "processed_arxiv")
ARXIV_SUMMARY_FOLDER = os.path.join(DATA_DIR, "summaries_arxiv")

for p in [ARXIV_PDF_FOLDER, USER_PROCESSED, ARXIV_PROCESSED, ARXIV_SUMMARY_FOLDER]:
    os.makedirs(p, exist_ok=True)

# Helper
def browse_for_folder(prompt="Select a folder containing your PDFs"):
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title=prompt)

def fetch_and_parse_arxiv(category: str, max_results=MAX_RESULTS, *, skip_download=False, skip_parse=False):
    print(f"\n▶ Fetching {max_results} most recent papers from {category}…")
    entries = get_recent_arxiv_entries(category=category, max_results=max_results)

    papers = []
    for e in entries:
        arxiv_id = e.id.split("/")[-1]
        papers.append({
            "title": e.title.strip(),
            "summary": e.summary.strip(),
            "published": getattr(e, "published", ""),
            "arxiv_url": e.id,
            "arxiv_id": arxiv_id,
        })

    write_all_json(papers, filename="metadata.json")
    print(f"\nSaved {len(papers)} papers into {os.path.join(DATA_DIR, 'metadata.json')}")

    if skip_download and skip_parse:
        return papers

    if not skip_download:
        download_arxiv_pdfs(papers, output_folder=ARXIV_PDF_FOLDER, delay_seconds=2)
    else:
        print("Skipping PDF download (assumed complete).")

    if not skip_parse:
        print("\n▶ Parsing arXiv PDFs with GROBID…")
        grobid_process_folder(ARXIV_PDF_FOLDER, ARXIV_PROCESSED)
    else:
        print("Skipping GROBID parsing (assumed complete).")

    return papers

# Summarization
def summarise_arxiv(summarizer=None, skip_summarize=False, mode="abstract"):
    if skip_summarize:
        print("Skipping summarisation step.")
        return

    if summarizer is None:
        summarizer = TransformerSummarizer()

    print(f"\n▶ Generating summaries (mode={mode}, this can be slow)…")
    if mode == "full":
        process_folder(ARXIV_PROCESSED, ARXIV_SUMMARY_FOLDER, summarizer, max_length=180)
    else:
        # for abstracts, use metadata LLM summaries
        process_metadata(
            metadata_path=os.path.join(DATA_DIR, "metadata.json"),
            output_path=os.path.join(DATA_DIR, "metadata_with_summaries.json"),
            summarizer=summarizer,
            max_length=120,
            mode="abstract"
        )

def load_summary_map() -> dict[str, str]:
    mapping = {}
    for fp in Path(ARXIV_SUMMARY_FOLDER).glob("*_summary.txt"):
        raw_id = fp.stem.replace("_summary", "")
        arxiv_id = raw_id.split("v")[0]
        try:
            mapping[arxiv_id] = fp.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"Could not read summary {fp}: {e}")
    # Also try metadata_with_summaries.json if abstracts
    metadata_summary_path = os.path.join(DATA_DIR, "metadata_with_summaries.json")
    if os.path.exists(metadata_summary_path):
        try:
            with open(metadata_summary_path, "r", encoding="utf-8") as f:
                papers = json.load(f)
            for p in papers:
                mapping[p["arxiv_id"].split("v")[0]] = p.get("llm_summary", p.get("summary", ""))
        except Exception as e:
            print(f"Could not read metadata summaries: {e}")
    return mapping

# Embedding
def embed_corpora(model_name: str, method: str, *, skip_embed=False):
    print("\n▶ Embedding abstracts…")
    if skip_embed:
        print("Skipping embedding, loading existing embeddings from disk…")
    user_abs_texts, user_abs_embs, model, user_files = embed_abstracts(USER_PROCESSED, model_name)
    arxiv_abs_texts, arxiv_abs_embs, _, _ = embed_abstracts(ARXIV_PROCESSED, model_name)

    print("▶ Embedding section chunks…")
    user_sections  = embed_sections(USER_PROCESSED, model)
    arxiv_sections = embed_sections(ARXIV_PROCESSED, model)

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
    return arxiv_id_with_version.split("v")[0]

# Main drive
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
    parser.add_argument("--summarizer", type=str, choices=["transformer", "llama"], default="transformer")
    parser.add_argument("--summary-mode", type=str, choices=["abstract", "full"], default="abstract",
                        help="Whether to summarize abstracts or full papers")
    parser.add_argument("--models_dir", type=str, help="Required if summarizer=llama: folder with GGUF model files")

    args = parser.parse_args()

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

    # Summarizer selection
    LLAMA_MODEL_PATH = Path("models") / "llama-3.2-1b-instruct-q4_k_m.gguf"

    if args.summarizer == "transformer":
        summarizer = TransformerSummarizer()
    else:
        if not LLAMA_MODEL_PATH.exists():
            raise FileNotFoundError(f"LLaMA model not found: {LLAMA_MODEL_PATH}")
        print(f"Using LLaMA model at: {LLAMA_MODEL_PATH}")
        summarizer = LlamaSummarizer(LLAMA_MODEL_PATH)

    # Run summarization according to mode
    summarise_arxiv(summarizer=summarizer, skip_summarize=args.skip_summarize, mode=args.summary_mode)

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
