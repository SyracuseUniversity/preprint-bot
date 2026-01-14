from __future__ import annotations
#!/usr/bin/env python3
"""
Database-integrated arXiv Preprint Recommender Pipeline
"""
import argparse
import asyncio
import sys
from pathlib import Path
from typing import Union, List

from .config import (
    DATA_DIR, DEFAULT_MODEL_NAME, MAX_RESULTS,
    PDF_DIR, PROCESSED_TEXT_DIR, USER_PDF_DIR, USER_PROCESSED_DIR,
    SYSTEM_USER_EMAIL, SYSTEM_USER_NAME, ARXIV_CORPUS_NAME,
    get_user_profile_structure
)
from .api_client import APIClient
from .download_arxiv_pdfs import download_arxiv_pdfs
from .embed_papers import embed_and_store_papers
from .extract_grobid import process_folder as grobid_process_folder
from .query_arxiv import (
    get_arxiv_entries, 
    get_yesterday_entries,
    get_arxiv_entries_multi_category,
    get_arxiv_entries_combined_query
)
from .summarization_script import TransformerSummarizer, LlamaSummarizer
from .user_mode_processor import process_user_profiles, run_user_recommendations

async def get_all_profile_categories(api_client: APIClient) -> List[str]:
    """Get unique categories from all user profiles"""
    try:
        response = await api_client.client.get(f"{api_client.base_url}/profiles/")
        response.raise_for_status()
        profiles = response.json()
        
        all_categories = set()
        for profile in profiles:
            categories = profile.get('categories', [])
            all_categories.update(categories)
        
        categories_list = list(all_categories)
        print(f"Found {len(categories_list)} unique categories from user profiles: {categories_list}")
        return categories_list
    except Exception as e:
        print(f"Error fetching profile categories: {e}")
        return []

async def fetch_and_store_arxiv(
    api_client: APIClient,
    categories: Union[str, List[str]] = None,
    max_results_per_category: int = 20,
    skip_download: bool = False,
    skip_parse: bool = False,
    combined_query: bool = False,
    use_daily_window: bool = False
):
    """
    Fetch arXiv papers from one or multiple categories and store in database.
    
    Args:
        api_client: API client instance
        categories: Single category string, list of categories, "all", or None (auto-fetch from profiles)
        max_results_per_category: Max papers per category
        skip_download: Skip PDF download step
        skip_parse: Skip GROBID parsing step
        combined_query: Use single combined query instead of separate queries
    
    Returns:
        int: Corpus ID containing the fetched papers
    """
    # If category is not explicitly provided, get from profiles
    if categories is None or categories == "auto":
        categories = await get_all_profile_categories(api_client)
        if not categories:
            print("No categories found in profiles. Please add categories to user profiles first.")
            return None
        print(f"Auto-detected categories from profiles: {categories}")

    user = await api_client.get_or_create_user(SYSTEM_USER_EMAIL, SYSTEM_USER_NAME)
    print(f"Using system user: {user['email']}")
    
    corpus = await api_client.get_or_create_corpus(
        user_id=user['id'],
        name=ARXIV_CORPUS_NAME,
        description="Automatically fetched arXiv papers"
    )
    print(f"Using corpus: {corpus['name']} (ID: {corpus['id']})")
    
    # Handle different input types
    # Handle different input types
    if use_daily_window:
        # NEW: Fetch daily submission window (yesterday 2PM - today 2PM EST)
        from .query_arxiv import get_daily_submission_window
        
        if isinstance(categories, list):
            entries = get_daily_submission_window(categories, max_results=10000)
        else:
            print("Error: --daily-window requires categories (auto-fetched from profiles)")
            return None

    elif categories == "all":
        print(f"\nFetching ALL preprints from yesterday...")
        entries = get_yesterday_entries(rate_limit=3.0)
    
    elif isinstance(categories, list):
        if combined_query:
            print(f"\nFetching from {len(categories)} categories (combined query)...")
            entries = get_arxiv_entries_combined_query(
                categories=categories,
                max_results=max_results_per_category * len(categories),
                days_back=7
            )
        else:
            print(f"\nFetching from {len(categories)} categories (separate queries)...")
            entries = get_arxiv_entries_multi_category(
                categories=categories,
                max_results_per_category=max_results_per_category,
                rate_limit=3.0
            )
    
    else:
        # Single category string
        print(f"\nFetching from {categories}...")
        entries = get_arxiv_entries(
            category=categories, 
            max_results=max_results_per_category
        )
    
    print(f"Fetched {len(entries)} papers from categories: {categories if isinstance(categories, list) else [categories]}")
    
    # Convert to papers data
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
                "authors": [a.name for a in getattr(entry, "authors", [])],
                "categories": [tag.term for tag in getattr(entry, "tags", [])]
            }
        })
    
    # Store in database
    stored_count = 0
    for paper_data in papers_data:
        existing = await api_client.get_paper_by_arxiv_id(paper_data["arxiv_id"])
        if existing:
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
            print(f"Failed to store {paper_data['arxiv_id']}: {e}")
    
    print(f"Stored {stored_count} new papers in database")
    
    # Download PDFs
    if not skip_download:
        download_arxiv_pdfs(
            [{"arxiv_url": p["metadata"]["arxiv_url"]} for p in papers_data],
            output_folder=str(PDF_DIR),
            use_s3=False,
            min_delay=3  # arXiv requires 3 seconds minimum
        )
    
    # Parse PDFs with GROBID
    if not skip_parse:
        print("\nParsing PDFs with GROBID...")
        grobid_process_folder(PDF_DIR, PROCESSED_TEXT_DIR)
        await store_sections(api_client, corpus['id'])
    
    return corpus['id']


async def store_sections(api_client: APIClient, corpus_id: int):
    """Extract and store sections from processed text files"""
    print(f"Extracting sections from papers in corpus {corpus_id}...")
    papers = await api_client.get_papers_by_corpus(corpus_id)
    
    if not papers:
        print("  No papers found in corpus")
        return
    
    sections_stored = 0
    for paper in papers:
        processed_path = paper.get('processed_text_path')
        if not processed_path:
            continue
            
        processed_file = Path(processed_path)
        if not processed_file.exists():
            continue
        
        try:
            with open(processed_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            continue
        
        sections = []
        current_header = None
        current_text = []
        
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
        
        paper_sections = 0
        for header, text in sections:
            try:
                await api_client.create_section(
                    paper_id=paper['id'],
                    header=header,
                    text=text
                )
                paper_sections += 1
                sections_stored += 1
            except Exception:
                pass
        
        if paper_sections > 0:
            print(f"  Stored {paper_sections} sections for: {paper['title'][:50]}...")
    
    print(f"Stored {sections_stored} total sections")


async def summarize_papers(api_client: APIClient, corpus_id: int, summarizer, mode: str = "abstract"):
    """Generate and store summaries for papers in a corpus"""
    print(f"\nGenerating summaries using {type(summarizer).__name__}...")
    
    papers = await api_client.get_papers_by_corpus(corpus_id)
    
    if not papers:
        print("  No papers found to summarize")
        return
    
    summarized_count = 0
    for paper in papers:
        if not paper.get('abstract'):
            continue
        
        try:
            summary_text = summarizer.summarize(
                paper['abstract'], 
                max_length=150, 
                mode=mode
            )
            
            await api_client.create_summary(
                paper_id=paper['id'],
                mode=mode,
                summary_text=summary_text,
                summarizer=type(summarizer).__name__
            )
            
            summarized_count += 1
            print(f"  {paper['title'][:60]}...")
            
        except Exception as e:
            print(f"  Failed: {paper.get('arxiv_id', paper['id'])}: {e}")
    
    print(f"\nGenerated {summarized_count} summaries")


async def run_corpus_mode(args):
    """Corpus mode: fetch and process arXiv papers"""
    api_client = APIClient()
    
    try:
        # Determine categories to fetch
        if hasattr(args, 'category') and args.category:
            # Handle single string or list
            categories = args.category if isinstance(args.category, list) else [args.category]
            
            # Special case: if list has one element "all", use "all"
            if len(categories) == 1 and categories[0] == "all":
                categories = "all"
        else:
            # No category specified - auto-fetch from profiles
            categories = None
        
        corpus_id = await fetch_and_store_arxiv(
            api_client,
            categories=categories,
            max_results_per_category=args.max_per_category,
            skip_download=args.skip_download,
            skip_parse=args.skip_parse,
            combined_query=args.combined_query,
            use_daily_window=args.daily_window
        )
        
        if not corpus_id:
            print("Failed to fetch papers. Exiting.")
            return
        
        if not args.skip_embed:
            await embed_and_store_papers(
                api_client,
                corpus_id=corpus_id,
                processed_folder=str(PROCESSED_TEXT_DIR),
                model_name=args.model,
                store_sections=True
            )
        
        if not args.skip_summarize:
            if args.summarizer == "llama":
                if not Path(args.llm_model).exists():
                    print(f"Error: LLM model not found at {args.llm_model}")
                    sys.exit(1)
                summarizer = LlamaSummarizer(model_path=args.llm_model)
            else:
                summarizer = TransformerSummarizer()
            
            await summarize_papers(api_client, corpus_id, summarizer, mode="abstract")
        
        print(f"\nCorpus mode complete. Corpus ID: {corpus_id}")
        
    finally:
        await api_client.close()

async def run_user_mode(args):
    """User mode: process user papers from UID/PID structure and run recommendations"""
    api_client = APIClient()
    
    try:
        # Scan directory structure
        structure = get_user_profile_structure(USER_PDF_DIR)
        
        if not structure:
            print(f"Error: No UID directories found in {USER_PDF_DIR}")
            print(f"Expected structure: user_pdfs/UID001/PID001/")
            sys.exit(1)
        
        print(f"Found structure:")
        for uid, pids in structure.items():
            print(f"  {uid}: {', '.join(map(str, pids))}")
        
        # Process specific UID if provided
        if args.uid:
            if args.uid not in structure:
                print(f"Error: {args.uid} not found in directory structure")
                sys.exit(1)
            uids_to_process = {args.uid: structure[args.uid]}
        else:
            uids_to_process = structure
        
        # Process all users and profiles
        all_user_results = []
        for uid, pids in uids_to_process.items():
            result = await process_user_profiles(
                api_client,
                uid,
                pids,
                skip_parse=args.skip_parse,
                skip_embed=args.skip_embed
            )
            if result:
                all_user_results.append(result)
        
        if not all_user_results:
            print("No users processed successfully")
            sys.exit(1)
        
        # Get arXiv corpus for recommendations
        system_user = await api_client.get_user_by_email(SYSTEM_USER_EMAIL)
        if not system_user:
            print("Error: arXiv corpus not found. Run --mode corpus first.")
            sys.exit(1)
        
        arxiv_corpus = await api_client.get_corpus_by_name(system_user['id'], ARXIV_CORPUS_NAME)
        if not arxiv_corpus:
            print("Error: arXiv corpus not found. Run --mode corpus first.")
            sys.exit(1)
        
        print(f"\nUsing arXiv corpus: {arxiv_corpus['name']} (ID: {arxiv_corpus['id']})")
        
        # Run recommendations for each user
        if not args.skip_recommendations:
            for user_result in all_user_results:
                user = user_result['user']
                user_corpora_ids = [r['corpus']['id'] for r in user_result['results']]
                
                await run_user_recommendations(
                    api_client,
                    user,
                    user_corpora_ids,
                    arxiv_corpus['id'],
                    args.threshold,
                    args.method,
                    args.use_sections
                )
        
        print(f"\nUser mode complete.")
        
    finally:
        await api_client.close()


def main():
    parser = argparse.ArgumentParser(description="Database-integrated Preprint Bot")
    parser.add_argument("--mode", choices=["corpus", "user"], required=True)
    
    # Now accepts multiple categories, or none (will auto-fetch from profiles)
    parser.add_argument(
        "--category", 
        nargs='*',  # CHANGED from '+' to '*' to allow zero categories
        default=None,  # CHANGED from ["cs.LG"] to None
        help="arXiv category or categories (e.g., cs.LG cs.CV cs.CL). If not specified, will fetch from user profiles."
    )
    parser.add_argument(
        "--max-per-category",
        type=int,
        default=20,
        help="Max papers per category"
    )
    parser.add_argument(
        "--combined-query",
        action="store_true",
        help="Use single combined query instead of separate queries"
    )
    
    parser.add_argument("--threshold", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--method", default="faiss", choices=["faiss", "cosine", "qdrant"])
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-parse", action="store_true")
    parser.add_argument("--skip-embed", action="store_true")
    parser.add_argument("--skip-summarize", action="store_true")
    parser.add_argument("--skip-recommendations", action="store_true")
    parser.add_argument("--summarizer", default="transformer", choices=["transformer", "llama"])
    parser.add_argument("--llm-model", default="models/Llama-3.1-8B-Instruct-IQ4_XS.gguf")
    parser.add_argument("--uid", help="Process specific UID only (e.g., UID001)")
    parser.add_argument("--use-sections", action="store_true")
    parser.add_argument("--daily-window", action="store_true", help="Fetch papers from yesterday 2PM EST to today 2PM EST (arXiv submission window)")
    
    args = parser.parse_args()
    
    # Handle empty list case
    if args.category is not None and len(args.category) == 0:
        args.category = None
    
    if args.mode == "corpus":
        asyncio.run(run_corpus_mode(args))
    elif args.mode == "user":
        asyncio.run(run_user_mode(args))


if __name__ == "__main__":
    main()