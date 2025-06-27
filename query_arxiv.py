import os
import time
import requests
import feedparser
import json
from urllib.parse import urlparse
from extract_grobid import extract_grobid_sections_from_bytes, spacy_tokenize

SAVE_DIR = "parsed_arxiv_outputs"
os.makedirs(SAVE_DIR, exist_ok=True)

# ARXIV_CATEGORY = "cs.CL"
MAX_RESULTS = 999  # Limit papers for testing

def get_recent_arxiv_entries(category="cs.CL", max_results=5):
    url = f"http://export.arxiv.org/api/query?search_query=cat:{category}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    feed = feedparser.parse(requests.get(url).text)
    return feed.entries

def get_arxiv_pdf_bytes(arxiv_url):
    parsed = urlparse(arxiv_url)
    arxiv_id = parsed.path.strip("/").split("/")[-1]
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    
    response = requests.get(pdf_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download PDF: {response.status_code}")
    
    return response.content, arxiv_id

def write_output(arxiv_id, result, tokenized):
    output_path = os.path.join(SAVE_DIR, f"{arxiv_id}_output.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Title: {result['title']}\n")
        f.write(f"Abstract: {result['abstract']}\n\n")
        f.write(f"Authors: {', '.join(result['authors'])}\n")
        f.write(f"Affiliations: {', '.join(result['affiliations'])}\n")
        f.write(f"Publication Date: {result['pub_date']}\n\n")

        f.write("Sections:\n")
        for sec in result['sections']:
            f.write(f"\n- {sec['header']}:\n{sec['text']}\n")

        f.write("\nTokenized Title:\n")
        f.write(" ".join(tokenized['title']) + "\n")

        f.write("\nTokenized Abstract:\n")
        f.write(" ".join(tokenized['abstract']) + "\n")

        f.write("\nTokenized Sections:\n")
        for sec in tokenized['sections']:
            f.write(f"\n- {sec['header']}:\n{' '.join(sec['tokens'])}\n")

def write_jsonl(arxiv_id, result, tokenized):
    json_path = os.path.join(SAVE_DIR, f"{arxiv_id}_output.jsonl")
    record = {
        "arxiv_id": arxiv_id,
        "title": result["title"],
        "abstract": result["abstract"],
        "authors": result["authors"],
        "affiliations": result["affiliations"],
        "pub_date": result["pub_date"],
        "sections": result["sections"],
        "tokens": tokenized
    }
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

def main(category):
    entries = get_recent_arxiv_entries(category, MAX_RESULTS)
    print(f"Fetched {len(entries)} entries from arXiv.")

    for entry in entries:
        try:
            arxiv_id = entry.id.split('/')[-1]
            print(f"\nProcessing {arxiv_id}")
            pdf_bytes, _ = get_arxiv_pdf_bytes(entry.id)
            result = extract_grobid_sections_from_bytes(pdf_bytes)

            tokenized = {
                'title': spacy_tokenize(result['title']),
                'abstract': spacy_tokenize(result['abstract']),
                'sections': [
                    {
                        'header': sec['header'],
                        'tokens': spacy_tokenize(sec['text'])
                    } for sec in result['sections']
                ]
            }

            write_output(arxiv_id, result, tokenized)
            write_jsonl(arxiv_id, result, tokenized)
            print(f"Finished: {arxiv_id}")
            time.sleep(30)  # Avoid arxiv request limits

        except Exception as e:
            print(f"Error with {entry.id}: {e}")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse recent arXiv papers by category")
    parser.add_argument("category", help="arXiv subject category (e.g., cs.CL, stat.ML, math.PR)")
    args = parser.parse_args()

    main(args.category)
