#!/usr/bin/env python3
"""
preprint_bot_summarization.py

Fetches arXiv papers, saves text/metadata, and summarizes abstracts using transformer models.
"""

import argparse
from pathlib import Path
from urllib.parse import quote
import feedparser
import re
import csv
from summarization_script import summarize_with_transformer  # Transformer-based summarization function

# ------------------------
# Folders for input/output
# ------------------------
INPUT_FOLDER = Path("input_folder")     # Folder to store raw paper text files
OUTPUT_FOLDER = Path("summaries")       # Folder to store summarized outputs

def create_folders():
    """Create input and output folders if they don't already exist."""
    INPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# ------------------------
# Text cleaning helpers
# ------------------------
def clean_whitespace(text):
    """Remove non-breaking spaces, tabs, and extra spaces from text."""
    text = text.replace("\xa0", " ")
    return re.sub(r'\s+', ' ', text).strip()

def clean_text(text):
    """
    Clean text by removing boilerplate, repeated sentences,
    extra periods, and normalizing whitespace.
    """
    text = re.sub(r'Continued on this page(\.*)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = text.split('. ')
    seen = set()
    unique_sentences = []
    for s in sentences:
        s_clean = s.strip()
        if s_clean and s_clean not in seen:
            seen.add(s_clean)
            unique_sentences.append(s_clean)
    return '. '.join(unique_sentences)

# ------------------------
# Fetch arXiv papers
# ------------------------
def fetch_arxiv_papers(query, max_results=5):
    """Query arXiv API and return a list of paper entries."""
    base_url = "http://export.arxiv.org/api/query?"
    encoded_query = quote(query)
    search_query = f"search_query=all:{encoded_query}&start=0&max_results={max_results}"
    feed = feedparser.parse(base_url + search_query)
    return feed.entries

# ------------------------
# Save paper text files
# ------------------------
def save_paper_txt(paper, index):
    """Save a single paper's title and abstract to a TXT file."""
    arxiv_id = paper.id.split("/")[-1]
    file_path = INPUT_FOLDER / f"{index}_{arxiv_id}.txt"
    clean_title = clean_whitespace(paper.title)
    clean_abstract = clean_text(paper.summary)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Title: {clean_title}\n\n")
        f.write(f"Abstract:\n{clean_abstract}\n")
    return file_path

# ------------------------
# Save metadata CSV
# ------------------------
def save_metadata(papers):
    """Save metadata (Index, ArxivID, Title, Authors) of fetched papers to CSV."""
    metadata_file = INPUT_FOLDER / "metadata.csv"
    with open(metadata_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Index", "ArxivID", "Title", "Authors"])
        for idx, paper in enumerate(papers, start=1):
            authors = ", ".join([author.name for author in paper.authors])
            writer.writerow([idx, paper.id.split("/")[-1], paper.title, authors])
    print(f"✅ Metadata saved: {metadata_file}")

# ------------------------
# Summarize abstract
# ------------------------
def summarize_paper(file_path, model_name, paper_index, max_length=180):
    """Generate summary for a paper using the transformer model and save it."""
    with open(file_path, "r", encoding="utf-8") as f:
        txt = f.read()
    match = re.search(r"Abstract:\s*(.*)", txt, re.DOTALL)
    if not match:
        print(f"⚠ No abstract found in {file_path.name}")
        return
    abstract_text = clean_text(match.group(1))
    summary = summarize_with_transformer(
        abstract_text, model_name=model_name, max_length=max_length
    )
    summary = clean_whitespace(summary)
    model_folder = OUTPUT_FOLDER / model_name.replace("/", "_")
    model_folder.mkdir(parents=True, exist_ok=True)
    output_file = model_folder / f"{paper_index}_{model_name.replace('/', '_')}_summary.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"✅ Summary saved: {output_file}")

# ------------------------
# Wrapper function for CLI or imports
# ------------------------
def process_arxiv_query(query, max_results=5, models=None, max_length=180):
    """
    High-level function to:
    1. Create folders
    2. Fetch papers
    3. Save text and metadata
    4. Summarize using specified models
    """
    if models is None:
        models = ["facebook/bart-large-cnn"]
    create_folders()
    papers = fetch_arxiv_papers(query, max_results)
    save_metadata(papers)
    for idx, paper in enumerate(papers, start=1):
        txt_file = save_paper_txt(paper, idx)
        for model in models:
            summarize_paper(txt_file, model_name=model, paper_index=idx, max_length=max_length)

# ------------------------
# CLI entry point
# ------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch arXiv papers and summarize abstracts.")
    parser.add_argument("query", help="Search term for arXiv")
    parser.add_argument("--max_results", type=int, default=5)
    parser.add_argument("--models", type=str, nargs="+", default=["facebook/bart-large-cnn"])
    parser.add_argument("--max_length", type=int, default=180)
    args = parser.parse_args()
    process_arxiv_query(
        args.query,
        max_results=args.max_results,
        models=args.models,
        max_length=args.max_length
    )

