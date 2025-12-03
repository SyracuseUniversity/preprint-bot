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


def get_yesterday_entries(rate_limit: float = 3.0, per_category: int = 10):
    """
    Fetch up to `per_category` entries submitted yesterday (UTC) for each arXiv category.
    Combines all results into a single list.

    Args:
        rate_limit (float): Seconds to sleep between requests. Default=3.0.
        per_category (int): Max number of papers per category (default=100).

    Returns:
        list: Combined list of feedparser entries from all categories.
    """
    # Major arXiv top-level categories
    categories = [
        "cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.IR", "cs.NE", "cs.DS",
        "math.PR", "math.ST", "stat.ML",
        "astro-ph", "cond-mat", "econ.EM", "physics.optics", "quant-ph",
        "eess.AS", "eess.SP", "q-bio.NC", "q-fin.ST"
    ]

    # All arxiv categories
    all_categories = [
    # Computer Science (cs)
    "cs.AI", "cs.AR", "cs.CC", "cs.CE", "cs.CG", "cs.CL", "cs.CR", "cs.CV",
    "cs.CY", "cs.DB", "cs.DC", "cs.DL", "cs.DM", "cs.DS", "cs.ET", "cs.FL",
    "cs.GL", "cs.GR", "cs.GT", "cs.HC", "cs.IR", "cs.IT", "cs.LG", "cs.LO",
    "cs.MA", "cs.MM", "cs.MS", "cs.NA", "cs.NE", "cs.NI", "cs.OH", "cs.OS",
    "cs.PF", "cs.PL", "cs.RO", "cs.SC", "cs.SD", "cs.SE", "cs.SI", "cs.SY",

    # Economics
    "econ.EM", "econ.GN", "econ.TH",

    # Electrical Engineering and Systems Science (eess)
    "eess.AS", "eess.IV", "eess.SP", "eess.SY",

    # Mathematics (math)
    "math.AC", "math.AG", "math.AP", "math.AT", "math.CA", "math.CO",
    "math.CT", "math.CV", "math.CS", "math.DG", "math.DS", "math.FA",
    "math.GM", "math.GN", "math.GR", "math.GT", "math.HO", "math.IT",
    "math.KT", "math.LO", "math.MG", "math.MI", "math.NA", "math.NT",
    "math.OA", "math.OC", "math.PR", "math.QA", "math.RA", "math.RM",
    "math.ST", "math.SG", "math.SP", "math.TO",

    # Physics
    "astro-ph.SR",  # Solar & Stellar Astrophysics (under astro-ph)
    # The physics categories often have “cond-mat”, “gr-qc”, “hep-*”, etc.
    "cond-mat.dis-nn", "cond-mat.mes-hall", "cond-mat.mtrl-sci",
    "cond-mat.other", "cond-mat.quant-gas", "cond-mat.soft",
    "cond-mat.stat-mech", "cond-mat.str-el", "cond-mat.supr-con",
    "gr-qc",
    "hep-ex", "hep-lat", "hep-ph", "hep-th",
    "math-ph",  # “Mathematical Physics” sits under physics archive :contentReference[oaicite:1]{index=1}
    # Also physics.* direct (some physics subcategories)
    "physics.pop-ph", "physics.soc-ph", "physics.space-ph",
    "quant-ph",

    # Quantitative Biology (q-bio)
    "q-bio.BM", "q-bio.MN", "q-bio.NC", "q-bio.OT", "q-bio.SC", "q-bio.TO",

    # Quantitative Finance (q-fin)
    "q-fin.CP", "q-fin.EC", "q-fin.GN", "q-fin.MF", "q-fin.PM", "q-fin.RM",
    "q-fin.ST", "q-fin.TR",

    # Statistics (stat)
    "stat.AP", "stat.CO", "stat.ME", "stat.ML", "stat.OT"
]

    yesterday = datetime.utcnow().date() - timedelta(days=1)
    start = yesterday.strftime("%Y%m%d000000")
    end = yesterday.strftime("%Y%m%d235959")

    all_entries = []

    print(f"▶ Fetching up to {per_category} papers *per category* from {yesterday}…")
    print(f"Total categories: {len(categories)}\n")

    for cat in categories:
        query = f"cat:{cat}+AND+submittedDate:[{start}+TO+{end}]"
        url = (
            "http://export.arxiv.org/api/query?"
            f"search_query={query}"
            f"&start=0&max_results={per_category}"
            "&sortBy=submittedDate&sortOrder=descending"
        )

        print(f"📘 Category: {cat} — fetching up to {per_category} papers…")
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            entries = feed.entries
            count = len(entries)
            print(f"Retrieved {count} papers for {cat}")
            all_entries.extend(entries)
        except Exception as e:
            print(f"Failed for {cat}: {e}")
            continue

        time.sleep(rate_limit)  # be polite to arXiv servers

    print(f"\nTotal collected: {len(all_entries)} papers across {len(categories)} categories.")
    return all_entries


def get_arxiv_entries(category: str, max_results: int = 20):
    """
    Fetch the most recent arXiv entries for a given category (e.g., 'cs.LG').
    """
    query = f"cat:{category}"
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
