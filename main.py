#!/usr/bin/env python
"""
End-to-End arXiv Preprint Recommender  ✨ 2025 refactor ✨
--------------------------------------------------------
Key differences from the previous main.py
1.  Uses `query_arxiv.fetch_and_parse()` (see below) instead of the old
    fetch-&-download pair that lived in fetch_arxiv + download_arxiv_pdfs.
2.  Leaves `extract_grobid.py` untouched for *user* PDFs only.
3.  Keeps the embedding + FAISS similarity logic exactly the same.
4.  Accepts CLI flags:  --category  --threshold  --model
"""

from pathlib import Path
import argparse
import json

import query_arxiv                                  # <— new unified fetch+parse
from extract_grobid import process_folder           # unchanged
from embed_papers import embed_abstracts, embed_sections
from similarity_matcher import hybrid_similarity_pipeline
from config import DATA_DIR, DEFAULT_MODEL_NAME

USER_PDF_FOLDER   = "my_papers"                     # user-supplied PDFs
USER_PROCESSED    = Path(DATA_DIR) / "processed_users"
ARXIV_PROCESSED   = Path(query_arxiv.SAVE_DIR)      # <-- produced by query_arxiv

def main(category: str,
         threshold_label: str = "medium",
         model_name: str = DEFAULT_MODEL_NAME):

    # 1. Fetch + parse fresh arXiv papers (single call)
    print(f"Fetching & parsing latest papers for category '{category}' …")
    all_papers = query_arxiv.fetch_and_parse(category)

    # 2. Parse the *user* PDFs via GROBID
    print("\nParsing user PDFs with GROBID …")
    process_folder(USER_PDF_FOLDER, USER_PROCESSED)       # unchanged file

    # 3. Embeddings
    print("\nEmbedding abstracts …")
    user_abs_txt,  user_abs_embs,  model, user_files  = embed_abstracts(USER_PROCESSED,  model_name)
    arxiv_abs_txt, arxiv_abs_embs, _    , _          = embed_abstracts(ARXIV_PROCESSED, model_name)

    print("Embedding sections …")
    user_sections  = embed_sections(USER_PROCESSED,  model)
    arxiv_sections = embed_sections(ARXIV_PROCESSED, model)

    # 4. Similarity search
    print("\nMatching similar papers …")
    matches = hybrid_similarity_pipeline(
        user_abs_embs, arxiv_abs_embs,
        user_sections, arxiv_sections,
        all_papers, user_files,
        threshold_label
    )

    # 5. Pretty print results
    print(f"\n{len(matches)} matches found (threshold='{threshold_label}'):\n")
    for i, m in enumerate(matches, 1):
        print(f"{i}. {m['title']}\n   {m['url']}\n   score={m['score']:.3f}\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--category",  default="cs.CL", help="arXiv category code (e.g. cs.CL, astro-ph)")
    p.add_argument("--threshold", default="medium", choices=["low","medium","high"])
    p.add_argument("--model",     default=DEFAULT_MODEL_NAME)
    args = p.parse_args()
    main(args.category, args.threshold, args.model)
