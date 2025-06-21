"""
Main driver script for the preprint recommendation pipeline.

This script performs the following steps:
1. Loads pre-fetched arXiv paper metadata (or fetches new data if needed).
2. Optionally downloads arXiv PDFs.
3. Optionally parses PDFs (user + arXiv) into structured plain text using GROBID.
4. Embeds title + abstract and full section text for both user and arXiv papers using a SentenceTransformer model.
5. Runs a hybrid similarity pipeline combining abstract and section similarity scores.
6. Prints out a ranked list of relevant arXiv papers for the user.

To run:
python main.py [similarity_threshold] [model_name] (default: medium, all-MiniLM-L6-v2)
"""

from fetch_arxiv import fetch_arxiv_papers
from download_arxiv_pdfs import download_arxiv_pdfs
from grobid_parser import process_folder
from embed_papers import embed_abstracts, embed_sections
from similarity_matcher import hybrid_similarity_pipeline
from config import *
import json

USER_PDF_FOLDER = "my_papers"
ARXIV_PDF_FOLDER = "arxiv_pipeline_data/arxiv_pdfs"
USER_PROCESSED = "arxiv_pipeline_data/processed_users"
ARXIV_PROCESSED = "arxiv_pipeline_data/processed_arxiv"



def main(threshold_label="medium", model_name=DEFAULT_MODEL_NAME):
    """
    Runs the end-to-end arXiv paper recommendation pipeline.

    Steps:
    1. Fetches new metadata or loads pre-fetched arXiv paper metadata.
    2. Optionally downloads arXiv PDFs and parses PDFs with GROBID.
    3. Embeds abstracts and section chunks from both user and arXiv papers.
    4. Performs a hybrid similarity search combining abstract and section-level similarities.
    5. Prints matched arXiv papers based on similarity threshold.

    Args:
        threshold_label (str): Similarity threshold label ('low', 'medium', 'high').
        model_name (str): Name of the embedding model to use.
    """
    
    print("\nFetching or Loading arXiv papers...")
    # Uncomment the below to fetch arXiv papers if metadata is not already available
    all_papers = fetch_arxiv_papers()


    # Otherwise if paper metadata is already fetched (if `arxiv_cs_papers.json` exists in your directory), load arXiv paper metadata from a pre-saved JSON file
    # with open("arxiv_pipeline_data/arxiv_cs_papers.json", "r", encoding="utf-8") as f:
    #     all_papers = json.load(f)
    # print(f"Found {len(all_papers)} arXiv papers.")

    # Uncomment the following lines if PDFs are not yet downloaded or parsed

    # # Download arXiv PDFs and save to disk
    print("\nDownloading PDFs...")
    download_arxiv_pdfs(all_papers, ARXIV_PDF_FOLDER)

    # # Parse user-uploaded PDFs using GROBID and store structured outputs
    print("\nParsing user papers with GROBID...")
    process_folder(USER_PDF_FOLDER, USER_PROCESSED)

    # # Parse arXiv PDFs using GROBID and store structured outputs
    print("\nParsing arXiv papers with GROBID...")
    process_folder(ARXIV_PDF_FOLDER, ARXIV_PROCESSED)

    # Step 1: Embed abstracts from user papers
    print("\nEmbedding user abstracts...")
    user_abs_texts, user_abs_embs, model, user_files = embed_abstracts(USER_PROCESSED, model_name)

    # Step 2: Embed abstracts from arXiv papers
    print("Embedding arXiv abstracts...")
    arxiv_abs_texts, arxiv_abs_embs, _, _ = embed_abstracts(ARXIV_PROCESSED, model_name)

    # Step 3: Embed full-text sections from user papers using the same model
    print("\nEmbedding user sections...")
    user_sections = embed_sections(USER_PROCESSED, model)

    # Step 4: Embed full-text sections from arXiv papers
    print("Embedding arXiv sections...")
    arxiv_sections = embed_sections(ARXIV_PROCESSED, model)

    # Step 5: Perform hybrid similarity search (abstract + sections)
    print("\nPerforming hybrid similarity search...")
    matches = hybrid_similarity_pipeline(
        user_abs_embs, arxiv_abs_embs,
        user_sections, arxiv_sections,
        all_papers, user_files,
        threshold_label
    )

    # Display the final matched papers
    print(f"\nFound {len(matches)} relevant papers:\n")
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match['title']}")
        print(f"   Link: {match['url']}")
        print(f"   Score: {match['score']:.3f}\n")

if __name__ == "__main__":
    import sys
    threshold = sys.argv[1] if len(sys.argv) > 1 else "medium"
    model_name = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MODEL_NAME
    main(threshold, model_name)
