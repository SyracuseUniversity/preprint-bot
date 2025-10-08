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
preprint_bot --category cs.LG --threshold medium --model all-MiniLM-L6-v2

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


import argparse
import json
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# Local imports (assumes running as `python pipeline.py` in project root)
from .config import DATA_DIR, DEFAULT_MODEL_NAME, MAX_RESULTS
from .download_arxiv_pdfs import download_arxiv_pdfs
from .embed_papers import embed_abstracts, embed_sections
from .extract_grobid import process_folder as grobid_process_folder
from .query_arxiv import get_arxiv_entries, write_all_json, get_yesterday_entries
from .similarity_matcher import hybrid_similarity_pipeline
from .summarization_script import (
    process_folder,
    TransformerSummarizer,
    LlamaSummarizer,
    process_metadata,
)

# Folder layout
USER_PDF_FOLDER = os.getenv("USER_PDF_FOLDER", "user_pdfs")
ARXIV_PDF_FOLDER = os.path.join(DATA_DIR, "arxiv_pdfs")
USER_PROCESSED = os.path.join(DATA_DIR, "processed_users")
ARXIV_PROCESSED = os.path.join(DATA_DIR, "processed_arxiv")
ARXIV_SUMMARY_FOLDER = os.path.join(DATA_DIR, "summaries_arxiv")

for p in [ARXIV_PDF_FOLDER, USER_PROCESSED, ARXIV_PROCESSED, ARXIV_SUMMARY_FOLDER]:
    os.makedirs(p, exist_ok=True)


from sentence_transformers import SentenceTransformer

def load_embedding_model(model_name: str):
    """
    Load a SentenceTransformer embedding model.
    """
    try:
        model = SentenceTransformer(model_name)
        return model
    except Exception as e:
        print(f"Error loading embedding model '{model_name}': {e}")
        sys.exit(1)



# Helpers
def browse_for_folder(prompt="Select a folder containing your PDFs"):
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title=prompt)


def fetch_and_parse_arxiv(category: str, *, skip_download=False, skip_parse=False, rate_limit: float = 3.0):
    if category == "all":
        print(f"\n▶ Fetching ALL preprints from yesterday (paginated, rate_limit={rate_limit}s)…")
        entries = get_yesterday_entries(rate_limit=rate_limit)
    else:
        print(f"\n▶ Fetching {MAX_RESULTS} most recent papers from {category}…")
        entries = get_arxiv_entries(category=category, max_results=MAX_RESULTS)

    papers = []
    for e in entries:
        arxiv_id = e.id.split("/")[-1]
        papers.append(
            {
                "title": e.title.strip(),
                "summary": e.summary.strip(),
                "published": getattr(e, "published", ""),
                "arxiv_url": e.id,
                "arxiv_id": arxiv_id,
            }
        )

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
        process_metadata(
            metadata_path=os.path.join(DATA_DIR, "metadata.json"),
            output_path=os.path.join(DATA_DIR, "metadata_with_summaries.json"),
            summarizer=summarizer,
            max_length=120,
            mode="abstract",
        )


def embed_corpora(
    model_name: str,
    method: str,
    embed_users: bool = False,
    embed_arxiv: bool = False,
    skip_embed: bool = False,
    user_processed_path: str | None = None
):
    """
    Embed abstracts and section texts for user and/or arXiv corpora.
    """

    user_abs_embs = arxiv_abs_embs = None
    user_sections = arxiv_sections = None
    user_files = None

    print(f"▶ Loading embedding model: {model_name}")
    model = load_embedding_model(model_name)  # ✅ actual SentenceTransformer object

    if embed_users:
        folder_to_embed = user_processed_path or USER_PROCESSED
        print(f"▶ Embedding user abstracts and sections from: {folder_to_embed}")

        if not os.path.exists(folder_to_embed) or not os.listdir(folder_to_embed):
            raise ValueError(f"No parsed PDFs found in {folder_to_embed}. Run GROBID first.")

        if skip_embed:
            print("⏭️ Skipping user embedding (using existing cached files if available)…")

        # ✅ Pass model object, not model_name
        user_abs_texts, user_abs_embs, _, user_files = embed_abstracts(folder_to_embed, model)
        user_sections = embed_sections(folder_to_embed, model)

        print(f"User embeddings complete for {len(user_abs_texts)} abstracts.")

    if embed_arxiv:
        print(f"▶ Embedding arXiv abstracts and sections from: {ARXIV_PROCESSED}")
        if not os.path.exists(ARXIV_PROCESSED) or not os.listdir(ARXIV_PROCESSED):
            raise ValueError(f"No processed arXiv files found in {ARXIV_PROCESSED}. Run corpus mode first.")

        if skip_embed:
            print("⏭️ Skipping arXiv embedding (using existing cached files if available)…")

        # ✅ Pass model object here too
        arxiv_abs_texts, arxiv_abs_embs, _, _ = embed_abstracts(ARXIV_PROCESSED, model)
        arxiv_sections = embed_sections(ARXIV_PROCESSED, model)

        print(f"ArXiv embeddings complete for {len(arxiv_abs_texts)} abstracts.")

    return (
        user_abs_embs,
        arxiv_abs_embs,
        user_sections,
        arxiv_sections,
        user_files
    )


# Modes
def run_corpus_mode(args):
    # Fetch, parse, summarize
    papers_meta = fetch_and_parse_arxiv(
        category=args.category,
        skip_download=args.skip_download,
        skip_parse=args.skip_parse,
    )

    # Summarizer
    if args.summarizer == "transformer":
        summarizer = TransformerSummarizer()
    else:
        if not args.models_dir:
            raise ValueError("--models_dir required for llama summarizer")
        llama_path = Path(args.models_dir) / "Llama-3.2-1B-Instruct.fp16.gguf"
        if not llama_path.exists():
            raise FileNotFoundError(f"LLaMA model not found: {llama_path}")
        summarizer = LlamaSummarizer(llama_path)

    summarise_arxiv(summarizer, skip_summarize=args.skip_summarize, mode=args.summary_mode)

    # Only embed ArXiv side
    _, arxiv_abs_embs, _, arxiv_sections, _ = embed_corpora(
        model_name=args.model,
        method=args.method,
        embed_users=False,   # prevent touching processed_users
        embed_arxiv=True,
        skip_embed=args.skip_embed
    )

    # Save corpus
    corpus_out = os.path.join(DATA_DIR, "arxiv_corpus.json")
    with open(corpus_out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "papers_meta": papers_meta,
                "abs_embs": arxiv_abs_embs.tolist(),
                "sections": {k: v.tolist() for k, v in arxiv_sections.items()},
            },
            f,
        )
    print(f"\n Corpus saved to {corpus_out}")

    # Save corpus
    corpus_out = os.path.join(DATA_DIR, "arxiv_corpus.json")
    with open(corpus_out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "papers_meta": papers_meta,
                "abs_embs": arxiv_abs_embs.tolist(),
                "sections": {k: v.tolist() for k, v in arxiv_sections.items()},
            },
            f,
        )
    print(f"\nCorpus saved to {corpus_out}")


def run_user_mode(args):
    """
    Run the user mode for one or multiple users.
    Each user folder will be processed separately to generate ranked matches.
    """
    base_folder = args.user_folder or USER_PDF_FOLDER

    if not os.path.exists(base_folder):
        print(f"Folder not found: {base_folder}")
        sys.exit(1)

    # Detect subfolders
    subfolders = [
        os.path.join(base_folder, d)
        for d in os.listdir(base_folder)
        if os.path.isdir(os.path.join(base_folder, d))
    ]
    if not subfolders:
        subfolders = [base_folder]

    print(f"\n▶ Found {len(subfolders)} user folder(s): {[os.path.basename(f) for f in subfolders]}")

    # Load precomputed arXiv corpus
    corpus_path = os.path.join(DATA_DIR, "arxiv_corpus.json")
    if not os.path.exists(corpus_path):
        print(f"Corpus file not found at {corpus_path}. Run --mode corpus first.")
        sys.exit(1)

    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    arxiv_abs_embs = corpus["abs_embs"]
    arxiv_sections = corpus["sections"]
    papers_meta = corpus["papers_meta"]

    # Optional: load summaries
    summary_map = {}
    summary_file = os.path.join(DATA_DIR, "metadata_with_summaries.json")
    if os.path.exists(summary_file):
        with open(summary_file, "r", encoding="utf-8") as f:
            for p in json.load(f):
                base_id = p["arxiv_id"].split("v")[0]
                summary_map[base_id] = p.get("llm_summary", p.get("summary", ""))

    # Process each user independently
    for user_path in subfolders:
        user_id = os.path.basename(user_path)
        print(f"▶ Processing user: {user_id}")

        user_processed = os.path.join(USER_PROCESSED, user_id)
        os.makedirs(user_processed, exist_ok=True)

        # GROBID parsing
        if not os.listdir(user_processed):
            print("▶ Parsing user PDFs with GROBID…")
            grobid_process_folder(user_path, user_processed)
        else:
            print("User PDFs already parsed → skipping.")

        try:
            # Embed
            print(f"▶ Embedding from: {user_processed}")
            user_abs_embs, _, user_sections, _, user_files = embed_corpora(
                model_name=args.model,
                method=args.method,
                embed_users=True,
                embed_arxiv=False,
                skip_embed=args.skip_embed,
                user_processed_path=user_processed,
            )

            # Similarity match
            print(f"▶ Running similarity search for {user_id}…")
            matches = hybrid_similarity_pipeline(
                user_abs_embs,
                arxiv_abs_embs,
                user_sections,
                arxiv_sections,
                papers_meta,
                user_files,
                threshold_label=args.threshold,
                method=args.method,
            )

            if not matches:
                print(f"No matches found for user {user_id}.")
                continue

            # Apply summaries
            for m in matches:
                arxiv_id = m["url"].split("/")[-1].split("v")[0]
                if arxiv_id in summary_map:
                    m["summary"] = summary_map[arxiv_id]

            # Save per-user
            output_path = os.path.join(DATA_DIR, f"ranked_matches_{user_id}.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(matches, f, indent=2)

            print(f"Matches saved for user {user_id} → {output_path}")

        except Exception as e:
            print(f"Error processing user {user_id}: {e}")
            continue  # proceed to next user


# Main
def main():
    parser = argparse.ArgumentParser(description="Run the arXiv recommender pipeline.")
    parser.add_argument("--mode", choices=["corpus", "user"], required=True)

    parser.add_argument("--category", default="cs.LG")
    parser.add_argument("--threshold", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--method", default="faiss", choices=["faiss", "cosine", "qdrant"])
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-parse", action="store_true")
    parser.add_argument("--skip-summarize", action="store_true")
    parser.add_argument("--skip-embed", action="store_true")
    parser.add_argument("--user-folder", help="Path to user PDFs (required in user mode)")
    parser.add_argument("--summarizer", choices=["transformer", "llama"], default="transformer")
    parser.add_argument("--summary-mode", choices=["abstract", "full"], default="abstract")
    parser.add_argument("--models_dir", type=str, help="Required if summarizer=llama")

    args = parser.parse_args()

    if args.mode == "corpus":
        run_corpus_mode(args)
    elif args.mode == "user":
        run_user_mode(args)


if __name__ == "__main__":
    main()