import os
import time
import requests
import feedparser
import argparse
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse

from .extract_grobid import extract_grobid_sections_from_bytes, spacy_tokenize
from .config import MAX_RESULTS as CONFIG_MAX_RESULTS, DATA_DIR

# Output directory
SAVE_DIR = os.path.join(os.getcwd(), "pdf_processes")
os.makedirs(SAVE_DIR, exist_ok=True)

# Default MAX_RESULTS (can be overridden by CLI or config)
MAX_RESULTS = CONFIG_MAX_RESULTS if CONFIG_MAX_RESULTS else 500  # increase, since we want *all*


def get_yesterday_entries(rate_limit: float = 3.0):
    """
    Fetch all arXiv entries submitted yesterday (UTC), regardless of category, with pagination.
    
    Args:
        rate_limit (float): Seconds to sleep between requests. Default=3.0 sec (per arXiv guidelines).
    """
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    start = yesterday.strftime("%Y%m%d000000")
    end = yesterday.strftime("%Y%m%d235959")
    query = f"submittedDate:[{start} TO {end}]"

    all_entries = []
    start_index = 0
    batch_size = 2000   # arXiv max per query

    while True:
        url = (
            "http://export.arxiv.org/api/query?"
            + f"search_query={query}"
            + f"&start={start_index}&max_results={batch_size}"
            + "&sortBy=submittedDate&sortOrder=descending"
        )
        print(f"▶ Fetching batch starting at {start_index} …")
        resp = requests.get(url)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        entries = feed.entries

        if not entries:
            break

        all_entries.extend(entries)
        start_index += batch_size

        # stop if fewer than batch_size returned → end of results
        if len(entries) < batch_size:
            break

        # Respect arXiv API rate limits
        print(f"⏳ Sleeping {rate_limit} sec before next request…")
        time.sleep(rate_limit)

    print(f"✅ Retrieved total {len(all_entries)} entries from yesterday.")
    return all_entries


def get_arxiv_entries(query, max_results):
    """
    Fetch arXiv entries using a full query string.
    """
    url = (
        "http://export.arxiv.org/api/query?"
        + "search_query=" + query
        + f"&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    )
    resp = requests.get(url)
    resp.raise_for_status()
    return feedparser.parse(resp.text).entries


def get_arxiv_pdf_bytes(arxiv_url):
    """
    Download the PDF bytes given an arXiv entry URL.
    """
    parsed = urlparse(arxiv_url)
    arxiv_id = parsed.path.strip("/").split("/")[-1]
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    response = requests.get(pdf_url)
    response.raise_for_status()
    return response.content, arxiv_id


def process_entry(entry, delay):
    """
    Process a single arXiv entry: download PDF, extract sections, tokenize,
    save outputs, and return record.
    """
    arxiv_id = entry.id.split('/')[-1]
    print(f"\nProcessing {arxiv_id}")

    # Fetch PDF and parse
    pdf_bytes, _ = get_arxiv_pdf_bytes(entry.id)
    result = extract_grobid_sections_from_bytes(pdf_bytes)

    # Tokenize sections
    tokenized = {
        'title': spacy_tokenize(result['title']),
        'abstract': spacy_tokenize(result['abstract']),
        'sections': [
            {'header': sec['header'], 'tokens': spacy_tokenize(sec['text'])}
            for sec in result['sections']
        ]
    }

    record = {
        "arxiv_id": arxiv_id,
        "title": result['title'],
        "abstract": result['abstract'],
        "authors": result['authors'],
        "affiliations": result['affiliations'],
        "pub_date": result['pub_date'],
        "sections": result['sections'],
        "tokens": tokenized
    }

    # Save outputs
    txt_path = os.path.join(SAVE_DIR, f"{arxiv_id}_output.txt")
    jsonl_path = os.path.join(SAVE_DIR, f"{arxiv_id}_output.jsonl")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result['title'] + "\n\n")
        f.write(result['abstract'] + "\n\n")
        for sec in result['sections']:
            f.write(sec['header'] + "\n")
            f.write(sec['text'] + "\n\n")

    with open(jsonl_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    print(f"Finished: {arxiv_id}")
    time.sleep(delay)
    return record


def write_all_json(records, filename="metadata.json"):
    """
    Save all fetched papers' metadata into one JSON file.
    """
    json_path = os.path.join(SAVE_DIR, filename)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"✅ Saved {len(records)} papers into {json_path}")


def main(max_results=MAX_RESULTS, delay=2):
    """
    Run pipeline for ALL preprints from yesterday.
    """
    query = get_yesterday_query()
    print("Search Query:", query)
    entries = get_arxiv_entries(query, max_results)

    print(f"Fetched {len(entries)} entries from arXiv.")
    all_records = []

    for entry in entries:
        try:
            record = process_entry(entry, delay)
            all_records.append(record)
        except Exception as e:
            print(f"Error with {entry.id}: {e}")

    write_all_json(all_records, filename="metadata.json")
    print(f"\nSaved {len(all_records)} papers into {os.path.join(SAVE_DIR, 'metadata.json')}")
