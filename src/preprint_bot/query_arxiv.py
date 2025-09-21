import os
import time
import requests
import feedparser
import argparse
import json
from urllib.parse import urlparse

from .extract_grobid import extract_grobid_sections_from_bytes, spacy_tokenize
from .config import MAX_RESULTS as CONFIG_MAX_RESULTS, DATA_DIR

# Output directory
SAVE_DIR = os.path.join(os.getcwd(), "pdf_processes")
os.makedirs(SAVE_DIR, exist_ok=True)


# Default MAX_RESULTS (can be overridden by CLI or config)
MAX_RESULTS = CONFIG_MAX_RESULTS if CONFIG_MAX_RESULTS else 50


def build_query(keywords, category):
    """
    Build the arXiv API search query combining category and/or keywords.
    """
    parts = []
    if category:
        parts.append(f"cat:{category}")
    if keywords:
        kw_query = "+OR+".join([f'all:"{kw}"' for kw in keywords])
        parts.append(f"({kw_query})")
    if not parts:
        raise ValueError("At least one of --keywords or --category must be provided.")
    return "+AND+".join(parts)


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


def get_recent_arxiv_entries(category="cs.CL", max_results=MAX_RESULTS):
    """
    Convenience: Fetch recent entries for a category only (no keywords).
    """
    url = (
        f"http://export.arxiv.org/api/query?search_query=cat:{category}"
        f"&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
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
    Process a single arXiv entry: download PDF, extract sections, tokenize, return record.
    """
    arxiv_id = entry.id.split('/')[-1]
    print(f"\nProcessing {arxiv_id}")
    pdf_bytes, _ = get_arxiv_pdf_bytes(entry.id)
    result = extract_grobid_sections_from_bytes(pdf_bytes)

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

    print(f"Finished: {arxiv_id}")
    time.sleep(delay)
    return record


SAVE_DIR = os.path.join(os.getcwd(), "pdf_processes")
os.makedirs(SAVE_DIR, exist_ok=True)

def write_all_json(records, filename="metadata.json"):
    """
    Save all fetched papers' metadata into one JSON file.
    """
    json_path = os.path.join(SAVE_DIR, filename)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"✅ Saved {len(records)} papers into {json_path}")



def main(keywords, category, max_results, delay):
    # save all results into one JSON file
    write_all_json(all_records, filename="metadata.json")
    print(f"\nSaved {len(all_records)} papers into {os.path.join(SAVE_DIR, 'metadata.json')}")
    if keywords or category:
        query = build_query(keywords, category)
        print("Search Query:", query)
        entries = get_arxiv_entries(query, max_results)
    else:
        # fallback to default category fetch
        entries = get_recent_arxiv_entries("cs.CL", max_results)

    print(f"Fetched {len(entries)} entries from arXiv.")
    all_records = []

    for entry in entries:
        try:
            record = process_entry(entry, delay)
            all_records.append(record)
        except Exception as e:
            print(f"Error with {entry.id}: {e}")



