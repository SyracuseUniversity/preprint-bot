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


#!/usr/bin/env python3
"""
Database-integrated arXiv Preprint Recommender Pipeline
"""
import argparse
import asyncio
import sys
from pathlib import Path

from .config import (
    DATA_DIR, DEFAULT_MODEL_NAME, MAX_RESULTS,
    PDF_DIR, PROCESSED_TEXT_DIR, USER_PDF_DIR, USER_PROCESSED_DIR,
    SYSTEM_USER_EMAIL, SYSTEM_USER_NAME, ARXIV_CORPUS_NAME
)
from .api_client import APIClient
from .download_arxiv_pdfs import download_arxiv_pdfs
from .embed_papers import embed_and_store_papers
from .extract_grobid import process_folder as grobid_process_folder
from .query_arxiv import get_arxiv_entries, get_yesterday_entries
from .summarization_script import TransformerSummarizer, LlamaSummarizer, process_metadata
from .db_similarity_matcher import run_similarity_matching


async def fetch_and_store_arxiv(
    api_client: APIClient,
    category: str,
    skip_download: bool = False,
    skip_parse: bool = False
):
    """Fetch arXiv papers and store in database"""
    
    # Get or create system user
    user = await api_client.get_or_create_user(SYSTEM_USER_EMAIL, SYSTEM_USER_NAME)
    print(f"✓ Using system user: {user['email']}")
    
    # Get or create arXiv corpus
    corpus = await api_client.get_or_create_corpus(
        user_id=user['id'],
        name=ARXIV_CORPUS_NAME,
        description="Automatically fetched arXiv papers"
    )
    print(f"✓ Using corpus: {corpus['name']} (ID: {corpus['id']})")
    
    # Fetch papers from arXiv
    if category == "all":
        print(f"\n▶ Fetching ALL preprints from yesterday...")
        entries = get_yesterday_entries(rate_limit=3.0)
    else:
        print(f"\n▶ Fetching {MAX_RESULTS} papers from {category}...")
        entries = get_arxiv_entries(category=category, max_results=MAX_RESULTS)
    
    papers_data = []
    for entry in entries:
        arxiv_id = entry.id.split("/")[-1]
        papers_data.append({
            "arxiv_id": arxiv_id,
            "title": entry.title.strip(),
            "abstract": entry.summary.strip(),
            "metadata": {
                "published": getattr(entry, "published", ""),
                "arxiv_url": entry.id,
                "authors": [a.name for a in getattr(entry, "authors", [])]
            }
        })
    
    print(f"✓ Fetched {len(papers_data)} papers")
    
    # Store papers in database
    stored_count = 0
    for paper_data in papers_data:
        existing = await api_client.get_paper_by_arxiv_id(paper_data["arxiv_id"])
        if existing:
            print(f"⊙ Paper {paper_data['arxiv_id']} already exists")
            continue
        
        try:
            await api_client.create_paper(
                corpus_id=corpus['id'],
                arxiv_id=paper_data['arxiv_id'],
                title=paper_data['title'],
                abstract=paper_data['abstract'],
                metadata=paper_data['metadata'],
                source="arxiv",
                pdf_path=str(PDF_DIR / f"{paper_data['arxiv_id']}.pdf"),
                processed_text_path=str(PROCESSED_TEXT_DIR / f"{paper_data['arxiv_id']}_output.txt")
            )
            stored_count += 1
        except Exception as e:
            print(f"✗ Failed to store {paper_data['arxiv_id']}: {e}")
    
    print(f"✓ Stored {stored_count} new papers in database")
    
    # Download PDFs
    if not skip_download:
        download_arxiv_pdfs(
            [{"arxiv_url": p["metadata"]["arxiv_url"]} for p in papers_data],
            output_folder=str(PDF_DIR),
            delay_seconds=2
        )
    
    # Parse with GROBID
    if not skip_parse:
        print("\n▶ Parsing PDFs with GROBID...")
        grobid_process_folder(PDF_DIR, PROCESSED_TEXT_DIR)
        
        # Store sections in database
        await store_sections(api_client, corpus['id'])
    
    return corpus['id']


async def store_sections(api_client: APIClient, corpus_id: int):
    """Extract and store sections from processed text files"""
    papers = await api_client.get_papers_by_corpus(corpus_id)
    
    for paper in papers:
        processed_file = Path(paper.get('processed_text_path', ''))
        if not processed_file.exists():
            continue
        
        with open(processed_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        sections = []
        current_header = None
        current_text = []
        
        # Skip title and abstract (first 2 lines)
        for line in lines[2:]:
            line = line.strip()
            if line.startswith("### "):
                if current_header and current_text:
                    sections.append((current_header, ' '.join(current_text)))
                current_header = line[4:].strip()
                current_text = []
            elif line:
                current_text.append(line)
        
        if current_header and current_text:
            sections.append((current_header, ' '.join(current_text)))
        
        # Store sections
        for header, text in sections:
            try:
                await api_client.create_section(
                    paper_id=paper['id'],
                    header=header,
                    text=text
                )
            except Exception as e:
                print(f"✗ Failed to store section for paper {paper['id']}: {e}")


async def run_corpus_mode(args):
    """Corpus mode: fetch and process arXiv papers"""
    api_client = APIClient()
    
    try:
        # Fetch and store
        corpus_id = await fetch_and_store_arxiv(
            api_client,
            category=args.category,
            skip_download=args.skip_download,
            skip_parse=args.skip_parse
        )
        
        # Embed papers
        if not args.skip_embed:
            await embed_and_store_papers(
                api_client,
                corpus_id=corpus_id,
                processed_folder=str(PROCESSED_TEXT_DIR),
                model_name=args.model,
                store_sections=True
            )
        
        print(f"\n✓ Corpus mode complete. Corpus ID: {corpus_id}")
        
    finally:
        await api_client.close()


async def run_user_mode(args):
    """User mode: process user papers and find matches"""
    api_client = APIClient()
    
    try:
        # Get user
        if not args.user_email:
            print("Error: --user-email required in user mode")
            sys.exit(1)
        
        user = await api_client.get_or_create_user(args.user_email, args.user_name)
        print(f"✓ User: {user['email']}")
        
        # Create user corpus
        user_corpus = await api_client.get_or_create_corpus(
            user_id=user['id'],
            name=f"{user['email']}_papers",
            description="User uploaded papers"
        )
        
        # Process user PDFs
        user_pdf_folder = Path(args.user_folder or USER_PDF_DIR)
        if not user_pdf_folder.exists():
            print(f"Error: User folder not found: {user_pdf_folder}")
            sys.exit(1)
        
        user_processed = USER_PROCESSED_DIR / user['email']
        user_processed.mkdir(parents=True, exist_ok=True)
        
        # Parse PDFs
        if not args.skip_parse:
            grobid_process_folder(user_pdf_folder, user_processed)
        
        # Store user papers in database
        await store_user_papers(api_client, user_corpus['id'], user_pdf_folder, user_processed)
        
        # Embed user papers
        if not args.skip_embed:
            await embed_and_store_papers(
                api_client,
                corpus_id=user_corpus['id'],
                processed_folder=str(user_processed),
                model_name=args.model,
                store_sections=True
            )
        
        # Get arXiv corpus
        system_user = await api_client.get_user_by_email(SYSTEM_USER_EMAIL)
        arxiv_corpus = await api_client.get_corpus_by_name(system_user['id'], ARXIV_CORPUS_NAME)
        
        if not arxiv_corpus:
            print("Error: arXiv corpus not found. Run --mode corpus first.")
            sys.exit(1)
        
        # Run similarity matching
        await run_similarity_matching(
            api_client,
            user_id=user['id'],
            user_corpus_id=user_corpus['id'],
            arxiv_corpus_id=arxiv_corpus['id'],
            threshold=args.threshold,
            method=args.method,
            model_name=args.model
        )
        
        print(f"\n✓ User mode complete. Check recommendations in database.")
        
    finally:
        await api_client.close()


async def store_user_papers(api_client: APIClient, corpus_id: int, pdf_folder: Path, processed_folder: Path):
    """Store user papers in database"""
    for pdf_file in pdf_folder.glob("*.pdf"):
        processed_file = processed_folder / f"{pdf_file.stem}_output.txt"
        
        if not processed_file.exists():
            continue
        
        # Extract title and abstract
        with open(processed_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        title = lines[0].strip().replace("# ", "") if lines else pdf_file.stem
        abstract = lines[1].strip().replace("## Abstract", "") if len(lines) > 1 else ""
        
        # Check if already exists
        existing = await api_client.get_paper_by_arxiv_id(pdf_file.stem)
        if existing:
            continue
        
        try:
            await api_client.create_paper(
                corpus_id=corpus_id,
                arxiv_id=pdf_file.stem,
                title=title,
                abstract=abstract,
                metadata={"source_file": pdf_file.name},
                source="user",
                pdf_path=str(pdf_file),
                processed_text_path=str(processed_file)
            )
        except Exception as e:
            print(f"✗ Failed to store {pdf_file.name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Database-integrated arXiv recommender")
    parser.add_argument("--mode", choices=["corpus", "user"], required=True)
    parser.add_argument("--category", default="cs.LG")
    parser.add_argument("--threshold", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--method", default="cosine", choices=["faiss", "cosine", "qdrant"])
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-parse", action="store_true")
    parser.add_argument("--skip-embed", action="store_true")
    parser.add_argument("--user-folder", help="Path to user PDFs")
    parser.add_argument("--user-email", help="User email (required in user mode)")
    parser.add_argument("--user-name", help="User name")
    
    args = parser.parse_args()
    
    if args.mode == "corpus":
        asyncio.run(run_corpus_mode(args))
    elif args.mode == "user":
        asyncio.run(run_user_mode(args))


if __name__ == "__main__":
    main()