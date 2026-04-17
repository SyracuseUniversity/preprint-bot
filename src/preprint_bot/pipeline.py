from __future__ import annotations
#!/usr/bin/env python3
"""
Database-integrated arXiv Preprint Recommender Pipeline
"""
import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timedelta, timezone, date as date_type
from zoneinfo import ZoneInfo
import time
import requests
import feedparser
import httpx

from .config import (
    DATA_DIR, DEFAULT_MODEL_NAME, MAX_RESULTS,
    PDF_DIR, PROCESSED_TEXT_DIR,
    SYSTEM_USER_EMAIL, SYSTEM_USER_NAME, ARXIV_CORPUS_NAME, DEFAULT_THRESHOLD,
)
from .api_client import APIClient
from .download_arxiv_pdfs import download_arxiv_pdfs
from .embed_papers import embed_and_store_papers
from .extract_grobid import process_folder as grobid_process_folder
from .summarization_script import TransformerSummarizer, LlamaSummarizer
from .user_mode_processor import process_unprocessed_papers
from .db_similarity_matcher import run_similarity_matching


async def get_all_profile_categories(api_client: APIClient) -> List[str]:
    try:
        response = await api_client.client.get(f"{api_client.base_url}/profiles/")
        response.raise_for_status()
        profiles = response.json()
        all_categories = set()
        for profile in profiles:
            all_categories.update(profile.get('categories', []))
        categories_list = list(all_categories)
        print(f"Found {len(categories_list)} unique categories from user profiles: {categories_list}")
        return categories_list
    except Exception as e:
        print(f"Error fetching profile categories: {e}")
        return []


async def fetch_papers_for_arxiv_day(target_date, categories):
    eastern = ZoneInfo("America/New_York")
    local_end = datetime(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        hour=14,
        minute=0,
        second=0,
        tzinfo=eastern,
    )
    local_start = local_end - timedelta(days=1)
    start_datetime = local_start.astimezone(timezone.utc)
    end_datetime = local_end.astimezone(timezone.utc)
    start = start_datetime.strftime("%Y%m%d%H%M")
    end = end_datetime.strftime("%Y%m%d%H%M")
    all_entries = []
    seen_ids = set()

    print(f"\nFetching papers for arXiv day: {target_date.strftime('%Y-%m-%d')}")
    print(f"Time window: {start_datetime} to {end_datetime} (UTC)")
    print(f"Categories: {categories}")

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "PreprintBot/1.0 (preprintbot@syr.edu)"}) as client:
        for cat in categories:
            query = f"cat:{cat}+AND+submittedDate:[{start}+TO+{end}]"
            url = (
                "https://export.arxiv.org/api/query?"
                f"search_query={query}"
                f"&start=0&max_results=100"
                "&sortBy=submittedDate&sortOrder=descending"
            )

            max_retries = 4
            backoff = 10
            success = False

            for attempt in range(max_retries):
                try:
                    resp = await client.get(url)
                    if resp.status_code == 429:
                        retry_after = resp.headers.get('Retry-After')
                        wait = int(retry_after) if retry_after else backoff * (2 ** attempt)
                        print(f"  {cat}: 429 rate limited, waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.text)
                    new_count = 0
                    for entry in feed.entries:
                        arxiv_id = entry.id.split('/')[-1]
                        if arxiv_id not in seen_ids:
                            seen_ids.add(arxiv_id)
                            all_entries.append(entry)
                            new_count += 1
                    print(f"  {cat}: {new_count} new papers")
                    success = True
                    break
                except Exception as e:
                    wait = backoff * (2 ** attempt)
                    print(f"  Error fetching {cat} (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait)

            if not success:
                print(f"  {cat}: failed after {max_retries} attempts, skipping")

            await asyncio.sleep(5)

    print(f"Total papers for {target_date.strftime('%Y-%m-%d')}: {len(all_entries)}")
    return all_entries

async def fetch_and_store_arxiv(
    api_client: APIClient,
    categories: List[str],
    target_date: datetime,
    skip_download: bool = False,
    skip_parse: bool = False
):
    user = await api_client.get_or_create_user(SYSTEM_USER_EMAIL, SYSTEM_USER_NAME)
    print(f"Using system user: {user['email']}")

    corpus = await api_client.get_or_create_corpus(
        user_id=user['id'],
        name=ARXIV_CORPUS_NAME,
        description="Automatically fetched arXiv papers"
    )
    print(f"Using corpus: {corpus['name']} (ID: {corpus['id']})")

    entries = await fetch_papers_for_arxiv_day(target_date, categories)

    if not entries:
        print("No papers found for this date")
        return corpus['id'], entries

    print(f"Fetched {len(entries)} papers")

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

    stored_count = 0
    for paper_data in papers_data:
        existing = await api_client.get_paper_by_arxiv_id(paper_data["arxiv_id"])
        if existing:
            continue

        submitted_date = None
        pub_str = paper_data['metadata'].get('published', '')
        if pub_str:
            try:
                submitted_date = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
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

    if not skip_download and stored_count > 0:
        download_arxiv_pdfs(
            [{"arxiv_url": p["metadata"]["arxiv_url"]} for p in papers_data],
            output_folder=str(PDF_DIR),
            use_s3=False,
            min_delay=3
        )

    if not skip_parse and stored_count > 0:
        print("\nParsing PDFs with GROBID...")
        grobid_process_folder(PDF_DIR, PROCESSED_TEXT_DIR)
        await store_sections(api_client, corpus['id'], entries)

    return corpus['id'], entries


async def store_sections(api_client: APIClient, corpus_id: int, entries):
    print(f"Extracting sections from papers in corpus {corpus_id}...")
    papers = await api_client.get_papers_by_corpus(corpus_id)
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
                await api_client.create_section(paper_id=paper['id'], header=header, text=text)
                paper_sections += 1
                sections_stored += 1
            except Exception:
                pass
        if paper_sections > 0:
            print(f"  Stored {paper_sections} sections for: {paper['title'][:50]}...")

    print(f"Stored {sections_stored} total sections")


async def summarize_papers(api_client: APIClient, corpus_id: int, summarizer, entries, mode: str = "abstract", paper_ids: set[int] | None = None):
    print(f"\nGenerating summaries using {type(summarizer).__name__}...")
    papers = await api_client.get_papers_by_corpus(corpus_id)
    entry_ids = {e.id.split('/')[-1] for e in entries}
    papers = [p for p in papers if p.get('arxiv_id') in entry_ids]

    if paper_ids is not None:
        papers = [p for p in papers if p['id'] in paper_ids]
        print(f"  Filtered to {len(papers)} recommended papers")

    if not papers:
        print("  No papers found to summarize")
        return

    summarized_count = 0
    for paper in papers:
        if not paper.get('abstract'):
            continue
        try:
            summary_text = summarizer.summarize(paper['abstract'], max_length=150, mode=mode)
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


async def generate_recommendations(api_client: APIClient, arxiv_corpus_id: int, user_corpora: List, target_date: datetime) -> set:
    if not user_corpora:
        print("No user corpora to generate recommendations for")
        return set()

    print(f"Generating recommendations for {len(user_corpora)} user corpora")

    recommended_paper_ids = set()

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
            if run_id is None:
                print(f"    ✗ Skipped: no embeddings found")
                continue
            print(f"    ✓ Created recommendation run ID: {run_id}")

            recs = await api_client.get_recommendations_by_run(run_id)
            for rec in recs:
                recommended_paper_ids.add(rec['paper_id'])

        except Exception as e:
            print(f"    ✗ Failed: {e}")

    print(f"\n  Total unique recommended papers: {len(recommended_paper_ids)}")
    return recommended_paper_ids


async def send_all_digests(api_client: APIClient, run_date: str = None):
    run_date = run_date or str(date_type.today())
    run_date_obj = date_type.fromisoformat(run_date)

    try:
        response = await api_client.client.get(f"{api_client.base_url}/profiles/")
        response.raise_for_status()
        profiles = response.json()
    except Exception as e:
        print(f"  Failed to fetch profiles: {e}")
        return

    for profile in profiles:
        if not profile.get("email_notify", False):
            continue

        frequency = profile.get("frequency", "daily")

        # Check if today is the right day to send for this frequency
        if frequency == "weekly":
            # Send on Mondays only
            if run_date_obj.weekday() != 0:
                print(f"  - [{profile['name']}] skipped: weekly frequency, not Monday")
                continue
        elif frequency == "monthly":
            # Send on the 1st of each month only
            if run_date_obj.day != 1:
                print(f"  - [{profile['name']}] skipped: monthly frequency, not 1st of month")
                continue
        # "daily" falls through and always sends

        profile_id = profile["id"]
        user_id = profile["user_id"]

        resp = None
        try:
            resp = await api_client.client.post(
                f"{api_client.base_url}/emails/send-digest",
                json={"user_id": user_id, "profile_id": profile_id, "run_date": run_date}
            )
            resp.raise_for_status()
            result = resp.json()
            status = result.get("status")
            if status == "sent":
                print(f"  ✓ [{profile['name']}] → {result.get('to')} ({result.get('papers_count')} papers)")
            else:
                print(f"  - [{profile['name']}] skipped: {result.get('reason')}")
        except Exception as e:
            if resp is not None:
                print(
                    f"  ✗ [{profile['name']}] failed: {e} "
                    f"(status={getattr(resp, 'status_code', 'unknown')}, body={getattr(resp, 'text', '')})"
                )
            else:
                print(f"  ✗ [{profile['name']}] failed before receiving a response: {e}")


async def run_pipeline(args):
    api_client = APIClient()

    try:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
        prev_day = target_date - timedelta(days=1)

        print("\n" + "="*80)
        print(f"PREPRINT BOT PIPELINE - {target_date.strftime('%Y-%m-%d')}")
        print("="*80)
        print(f"Time window: 2PM {prev_day.strftime('%Y-%m-%d')} to 2PM {target_date.strftime('%Y-%m-%d')} EST")
        print("="*80 + "\n")

        # Step 1 always runs — process papers uploaded since the last run
        print("="*60)
        print("STEP 1: Processing User Papers")
        print("="*60)
        user_result = await process_unprocessed_papers(
            api_client, skip_parse=args.skip_parse, skip_embed=args.skip_embed
        )
        print(f"  Summary: {user_result['parsed']} parsed, {user_result['embedded']} embedded")

        print("\n" + "="*60)
        print("STEP 2: Getting Categories from User Profiles")
        print("="*60)
        categories = await get_all_profile_categories(api_client)

        if not categories:
            print("ERROR: No categories found in user profiles.")
            print("Please create user profiles with categories before running the pipeline.")
            sys.exit(1)

        print("\n" + "="*60)
        print("STEP 3: Fetching arXiv Papers")
        print("="*60)
        corpus_id, entries = await fetch_and_store_arxiv(
            api_client,
            categories=categories,
            target_date=target_date,
            skip_download=args.skip_download,
            skip_parse=args.skip_parse
        )

        entries = entries or []

        if not entries:
            print("No new arXiv papers fetched. Skipping steps 4\u20137.")
        else:
            print("\n" + "="*60)
            print("STEP 4: Generating arXiv Embeddings")
            print("="*60)
            if not args.skip_embed:
                await embed_and_store_papers(
                    api_client,
                    corpus_id=corpus_id,
                    processed_folder=str(PROCESSED_TEXT_DIR),
                    model_name=args.model,
                    store_sections=True
                )

            print("\n" + "="*60)
            print("STEP 5: Generating arXiv Summaries")
            print("="*60)
            if not args.skip_summarize:
                if args.summarizer == "llama":
                    if not Path(args.llm_model).exists():
                        print(f"Warning: LLM model not found at {args.llm_model}. Skipping summarization.")
                    else:
                        summarizer = LlamaSummarizer(model_path=args.llm_model)
                        await summarize_papers(api_client, corpus_id, summarizer, entries, mode="abstract")
                else:
                    summarizer = TransformerSummarizer()
                    await summarize_papers(api_client, corpus_id, summarizer, entries, mode="abstract")
            else:
                print("Skipping summarization.")

            # Gather user corpora for recommendations
            try:
                response = await api_client.client.get(f"{api_client.base_url}/profiles/")
                response.raise_for_status()
                all_profiles = response.json()
            except Exception as e:
                print(f"Failed to fetch profiles: {e}")
                all_profiles = []

            system_user = await api_client.get_user_by_email(SYSTEM_USER_EMAIL)
            system_user_id = system_user['id'] if system_user else None

            user_corpora = []
            for profile in all_profiles:
                if profile['user_id'] == system_user_id:
                    continue
                corpus_name = f"user_{profile['user_id']}_profile_{profile['id']}"
                corpus = await api_client.get_corpus_by_name(profile['user_id'], corpus_name)
                if corpus:
                    user_corpora.append({
                        'user_id': profile['user_id'],
                        'corpus_id': corpus['id'],
                        'profile': profile,
                    })

            print(f"  Found {len(user_corpora)} user corpus/profile pair(s) for recommendations")

            print("\n" + "="*60)
            print("STEP 6: Generating Recommendations")
            print("="*60)
            await generate_recommendations(api_client, corpus_id, user_corpora, target_date)

            print("\n" + "="*60)
            print("STEP 7: Sending Email Digests")
            print("="*60)
            await send_all_digests(api_client, run_date=target_date.strftime("%Y-%m-%d"))

        # Cleanup always runs
        print("\n" + "="*60)
        print("STEP 8: Cleanup")
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
            print(f"  ✓ User paper files are safe (hash-based storage)")
        except Exception as e:
            print(f"  Warning: Cleanup failed: {e}")

        print("\n" + "="*80)
        print("PIPELINE COMPLETE!")
        print("="*80)
        print(f"  • Date: {target_date.strftime('%Y-%m-%d')}")
        print(f"  • User papers: {user_result['parsed']} parsed, {user_result['embedded']} embedded")
        print(f"  • arXiv papers: {len(entries)} fetched")
        print("="*80 + "\n")

    finally:
        await api_client.close()


def main():
    parser = argparse.ArgumentParser(description="Preprint Bot Pipeline")
    parser.add_argument("--date", required=True, help="Target date (YYYY-MM-DD)")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="Embedding model name")
    parser.add_argument("--skip-download", action="store_true", help="Skip PDF download")
    parser.add_argument("--skip-parse", action="store_true", help="Skip GROBID parsing")
    parser.add_argument("--skip-embed", action="store_true", help="Skip embedding generation")
    parser.add_argument("--skip-summarize", action="store_true", help="Skip summarization")
    parser.add_argument("--summarizer", default="llama", choices=["transformer", "llama"], help="Summarizer to use")
    parser.add_argument("--llm-model", default="models/llama-3.2-3b-instruct-q4_k_m.gguf", help="Path to LLM model")

    args = parser.parse_args()
    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()