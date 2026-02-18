from __future__ import annotations
#!/usr/bin/env python3
"""
Date-based arXiv Preprint Recommender Pipeline - Single Unified Mode
"""
import argparse
import asyncio
import sys
from pathlib import Path
from typing import List
from datetime import datetime, timedelta
import time
import requests
import feedparser

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from preprint_bot.config import (
    DATA_DIR, DEFAULT_MODEL_NAME, MAX_RESULTS,
    PDF_DIR, PROCESSED_TEXT_DIR, USER_PDF_DIR, USER_PROCESSED_DIR,
    SYSTEM_USER_EMAIL, SYSTEM_USER_NAME, ARXIV_CORPUS_NAME,
    get_user_profile_structure
)
from preprint_bot.api_client import APIClient
from preprint_bot.download_arxiv_pdfs import download_arxiv_pdfs
from preprint_bot.embed_papers import embed_and_store_papers
from preprint_bot.extract_grobid import process_folder as grobid_process_folder
from preprint_bot.summarization_script import TransformerSummarizer, LlamaSummarizer
from preprint_bot.user_mode_processor import process_user_profiles, run_user_recommendations
from preprint_bot.db_similarity_matcher import run_similarity_matching

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


async def fetch_papers_for_arxiv_day(target_date, categories):
    """
    Fetch papers for arXiv's upload schedule: 2PM previous day to 2PM target day (EST)
    """
    # arXiv schedule: papers submitted from yesterday 2PM to today 2PM EST
    # Convert to UTC (EST is UTC-5)
    start_datetime = target_date.replace(hour=14, minute=0, second=0) - timedelta(days=1) + timedelta(hours=5)
    end_datetime = target_date.replace(hour=14, minute=0, second=0) + timedelta(hours=5)
    
    # Format for arXiv query (YYYYMMDDHHMM)
    start = start_datetime.strftime("%Y%m%d%H%M")
    end = end_datetime.strftime("%Y%m%d%H%M")
    
    all_entries = []
    seen_ids = set()
    
    print(f"\nFetching papers for arXiv day: {target_date.strftime('%Y-%m-%d')}")
    print(f"Time window: {start_datetime} to {end_datetime} (UTC)")
    print(f"Categories: {categories}")
    
    for cat in categories:
        query = f"cat:{cat}+AND+submittedDate:[{start}+TO+{end}]"
        url = (
            "http://export.arxiv.org/api/query?"
            f"search_query={query}"
            f"&start=0&max_results=100"
            "&sortBy=submittedDate&sortOrder=descending"
        )
        
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            entries = feed.entries
            
            # Deduplicate
            new_count = 0
            for entry in entries:
                arxiv_id = entry.id.split('/')[-1]
                if arxiv_id not in seen_ids:
                    seen_ids.add(arxiv_id)
                    all_entries.append(entry)
                    new_count += 1
            
            print(f"  {cat}: {new_count} new papers")
            time.sleep(3)  # Rate limiting
            
        except Exception as e:
            print(f"  Error fetching {cat}: {e}")
            continue
    
    print(f"Total papers for {target_date.strftime('%Y-%m-%d')}: {len(all_entries)}")
    return all_entries


async def fetch_and_store_arxiv(
    api_client: APIClient,
    categories: List[str],
    target_date: datetime,
    skip_download: bool = False,
    skip_parse: bool = False
):
    """
    Fetch arXiv papers for a specific date and store in database.
    """
    user = await api_client.get_or_create_user(SYSTEM_USER_EMAIL, SYSTEM_USER_NAME)
    print(f"Using system user: {user['email']}")
    
    corpus = await api_client.get_or_create_corpus(
        user_id=user['id'],
        name=ARXIV_CORPUS_NAME,
        description="Automatically fetched arXiv papers"
    )
    print(f"Using corpus: {corpus['name']} (ID: {corpus['id']})")
    
    # Fetch papers for the specified date
    entries = await fetch_papers_for_arxiv_day(target_date, categories)
    
    if not entries:
        print("No papers found for this date")
        return corpus['id'], entries
    
    print(f"Fetched {len(entries)} papers")
    
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
        
        # Extract submitted_date from metadata and CONVERT TO UTC
        from datetime import timezone

        submitted_date = None
        pub_str = paper_data['metadata'].get('published', '')
        if pub_str:
            try:
                # Parse the date
                submitted_date = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
                
                # Convert to UTC and remove timezone info (store as naive UTC)
                if submitted_date.tzinfo is not None:
                    submitted_date = submitted_date.astimezone(timezone.utc).replace(tzinfo=None)
                
            except Exception as e:
                print(f"Failed to parse date for {paper_data.get('arxiv_id', 'unknown')}: {e}")
        
        try:
            await api_client.create_paper(
                corpus_id=corpus['id'],
                arxiv_id=paper_data['arxiv_id'],
                title=paper_data['title'],
                abstract=paper_data['abstract'],
                metadata=paper_data['metadata'],
                source="arxiv",
                pdf_path=str(PDF_DIR / f"{paper_data['arxiv_id']}.pdf"),
                processed_text_path=str(PROCESSED_TEXT_DIR / f"{paper_data['arxiv_id']}_output.txt"),
                submitted_date=submitted_date
            )
            stored_count += 1
        except Exception as e:
            print(f"Failed to store {paper_data['arxiv_id']}: {e}")
    
    print(f"Stored {stored_count} new papers in database")
    
    # Download PDFs
    if not skip_download and stored_count > 0:
        download_arxiv_pdfs(
            [{"arxiv_url": p["metadata"]["arxiv_url"]} for p in papers_data],
            output_folder=str(PDF_DIR),
            use_s3=False,
            min_delay=3
        )
    
    # Parse PDFs with GROBID
    if not skip_parse and stored_count > 0:
        print("\nParsing PDFs with GROBID...")
        grobid_process_folder(PDF_DIR, PROCESSED_TEXT_DIR)
        await store_sections(api_client, corpus['id'], entries)
    
    return corpus['id'], entries


async def store_sections(api_client: APIClient, corpus_id: int, entries):
    """Extract and store sections from processed text files"""
    print(f"Extracting sections from papers in corpus {corpus_id}...")
    papers = await api_client.get_papers_by_corpus(corpus_id)
    
    # Only process papers from current batch
    entry_ids = {e.id.split('/')[-1] for e in entries}
    papers = [p for p in papers if p.get('arxiv_id') in entry_ids]
    
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


async def summarize_papers(api_client: APIClient, corpus_id: int, summarizer, entries, mode: str = "abstract"):
    """Generate and store summaries for papers in a corpus"""
    print(f"\nGenerating summaries using {type(summarizer).__name__}...")
    
    papers = await api_client.get_papers_by_corpus(corpus_id)
    
    # Only process papers from current batch
    entry_ids = {e.id.split('/')[-1] for e in entries}
    papers = [p for p in papers if p.get('arxiv_id') in entry_ids]
    
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


async def process_user_papers(api_client: APIClient, skip_parse: bool, skip_embed: bool):
    """Process user-uploaded papers"""
    print("\n" + "="*60)
    print("STEP: Processing User Papers")
    print("="*60)
    
    # Scan directory structure
    structure = get_user_profile_structure(USER_PDF_DIR)
    
    if not structure:
        print("No user papers found in user_pdfs/")
        return []
    
    print(f"Found user structure:")
    for uid, pids in structure.items():
        print(f"  User {uid}: Profiles {', '.join(map(str, pids))}")
    
    # Process all users and profiles
    all_user_corpora = []
    for uid, pids in structure.items():
        result = await process_user_profiles(
            api_client,
            uid,
            pids,
            skip_parse=skip_parse,
            skip_embed=skip_embed
        )
        if result:
            for r in result['results']:
                all_user_corpora.append({
                    'user_id': result['user']['id'],
                    'corpus_id': r['corpus']['id'],
                    'profile': r['profile']
                })
    
    return all_user_corpora


async def generate_recommendations(api_client: APIClient, arxiv_corpus_id: int, user_corpora: List, target_date: datetime):  
    """Generate recommendations for all user corpora"""
    print("\n" + "="*60)
    print("STEP: Generating Recommendations")
    print("="*60)
    
    if not user_corpora:
        print("No user corpora to generate recommendations for")
        return
    
    print(f"Generating recommendations for {len(user_corpora)} user corpora")
    
    for corpus_info in user_corpora:
        user_corpus_id = corpus_info['corpus_id']
        user_id = corpus_info['user_id']
        profile = corpus_info['profile']
        
        print(f"\n  Profile: {profile['name']} (User {user_id})")
        
        try:
            run_id = await run_similarity_matching(
                api_client,
                user_id=user_id,
                user_corpus_id=user_corpus_id,
                arxiv_corpus_id=arxiv_corpus_id,
                profile_id=profile['id'],
                target_date=target_date,
                threshold=profile['threshold'],
                method='cosine',
                model_name=DEFAULT_MODEL_NAME,
                use_sections=True
            )
            
            print(f"    ✓ Created recommendation run ID: {run_id}")
        except Exception as e:
            print(f"    ✗ Failed: {e}")


async def run_pipeline(args):
    """Unified pipeline: fetch arXiv papers, process user papers, generate recommendations"""
    api_client = APIClient()
    
    try:
        # Parse target date
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
        prev_day = target_date - timedelta(days=1)
        
        print("\n" + "="*80)
        print(f"PREPRINT BOT UNIFIED PIPELINE - {target_date.strftime('%Y-%m-%d')}")
        print("="*80)
        print(f"Time window: 2PM {prev_day.strftime('%Y-%m-%d')} to 2PM {target_date.strftime('%Y-%m-%d')} EST")
        print("="*80 + "\n")
        
        # STEP 1: Get categories from user profiles
        print("="*60)
        print("STEP 1: Getting Categories from User Profiles")
        print("="*60)
        categories = await get_all_profile_categories(api_client)
        
        if not categories:
            print("ERROR: No categories found in user profiles.")
            print("Please create user profiles with categories before running the pipeline.")
            sys.exit(1)
        
        # STEP 2: Fetch and store arXiv papers
        print("\n" + "="*60)
        print("STEP 2: Fetching arXiv Papers")
        print("="*60)
        corpus_id, entries = await fetch_and_store_arxiv(
            api_client,
            categories=categories,
            target_date=target_date,
            skip_download=args.skip_download,
            skip_parse=args.skip_parse
        )
        
        if not entries:
            print("No new papers fetched. Skipping embedding and summarization.")
        else:
            # STEP 3: Generate embeddings
            print("\n" + "="*60)
            print("STEP 3: Generating Embeddings")
            print("="*60)
            await embed_and_store_papers(
                api_client,
                corpus_id=corpus_id,
                processed_folder=str(PROCESSED_TEXT_DIR),
                model_name=args.model,
                store_sections=True
            )
            
            # STEP 4: Generate summaries
            print("\n" + "="*60)
            print("STEP 4: Generating Summaries")
            print("="*60)
            if args.summarizer == "llama":
                if not Path(args.llm_model).exists():
                    print(f"Warning: LLM model not found at {args.llm_model}")
                    print("Skipping summarization.")
                else:
                    summarizer = LlamaSummarizer(model_path=args.llm_model)
                    await summarize_papers(api_client, corpus_id, summarizer, entries, mode="abstract")
            else:
                summarizer = TransformerSummarizer()
                await summarize_papers(api_client, corpus_id, summarizer, entries, mode="abstract")
        
        # STEP 5: Process user papers
        print("\n" + "="*60)
        print("STEP 5: Processing User Papers")
        print("="*60)
        user_corpora = await process_user_papers(
            api_client,
            skip_parse=args.skip_parse,
            skip_embed=args.skip_embed
        )
        
        # STEP 6: Generate recommendations
        print("\n" + "="*60)
        print("STEP 6: Generating Recommendations")
        print("="*60)
        await generate_recommendations(api_client, corpus_id, user_corpora, target_date)
        
        # STEP 7: Cleanup
        print("\n" + "="*60)
        print("STEP 7: Cleanup")
        print("="*60)
        print("Cleaning up temporary arXiv files...")
        try:
            deleted_pdfs = 0
            deleted_txts = 0
            
            for pdf in PDF_DIR.glob("*.pdf"):
                pdf.unlink()
                deleted_pdfs += 1
            
            for txt in PROCESSED_TEXT_DIR.glob("*_output.txt"):
                txt.unlink()
                deleted_txts += 1
            
            print(f"  ✓ Deleted {deleted_pdfs} PDFs and {deleted_txts} processed texts")
            print(f"  ✓ User files in {USER_PDF_DIR} are safe")
        except Exception as e:
            print(f"  Warning: Cleanup failed: {e}")
        
        # Final summary
        print("\n" + "="*80)
        print("PIPELINE COMPLETE!")
        print("="*80)
        print(f"  • Date: {target_date.strftime('%Y-%m-%d')}")
        print(f"  • arXiv Papers: {len(entries)} fetched")
        print(f"  • User Corpora: {len(user_corpora)} processed")
        print(f"  • Corpus ID: {corpus_id}")
        print("="*80 + "\n")
        
    finally:
        await api_client.close()


def main():
    parser = argparse.ArgumentParser(description="Unified Date-based Preprint Bot Pipeline")
    parser.add_argument(
        "--date",
        required=True,
        help="Target date (YYYY-MM-DD) - fetches papers from 2PM previous day to 2PM this day"
    )
    
    # Processing arguments
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="Embedding model name")
    parser.add_argument("--skip-download", action="store_true", help="Skip PDF download")
    parser.add_argument("--skip-parse", action="store_true", help="Skip GROBID parsing")
    parser.add_argument("--skip-embed", action="store_true", help="Skip embedding generation")
    parser.add_argument("--summarizer", default="llama", choices=["transformer", "llama"], help="Summarizer to use")
    parser.add_argument("--llm-model", default="models/llama-3.2-3b-instruct-q4_k_m.gguf", help="Path to LLM model")
    
    args = parser.parse_args()
    
    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()