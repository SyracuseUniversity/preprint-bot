import os
import time
import requests
import feedparser
import argparse
import json
from urllib.parse import urlparse
from extract_grobid import extract_grobid_sections_from_bytes, spacy_tokenize

SAVE_DIR = "parsed_arxiv_outputs"
os.makedirs(SAVE_DIR, exist_ok=True)

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
    url = (
        "http://export.arxiv.org/api/query?"
        + "search_query=" + query
        + "&start=0&max_results=" + str(max_results)
        + "&sortBy=submittedDate&sortOrder=descending"
    )
    resp = requests.get(url)
    resp.raise_for_status()
    feed = feedparser.parse(resp.text)
    return feed.entries


def get_arxiv_pdf_bytes(arxiv_url):
    parsed = urlparse(arxiv_url)
    arxiv_id = parsed.path.strip("/").split("/")[-1]
    pdf_url = "https://arxiv.org/pdf/" + arxiv_id + ".pdf"
    response = requests.get(pdf_url)
    response.raise_for_status()
    return response.content, arxiv_id


def write_output(arxiv_id, result, tokenized):
    txt_path = os.path.join(SAVE_DIR, arxiv_id + "_output.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Title: {}\n".format(result['title']))
        f.write("Abstract: {}\n\n".format(result['abstract']))
        f.write("Authors: {}\n".format(", ".join(result['authors'])))
        f.write("Affiliations: {}\n".format(", ".join(result['affiliations'])))
        f.write("Publication Date: {}\n\n".format(result['pub_date']))
        f.write("Sections:\n")
        for sec in result['sections']:
            f.write("\n- {}:\n{}\n".format(sec['header'], sec['text']))

        f.write("\nTokenized Title:\n{}\n".format(" ".join(tokenized['title'])))
        f.write("\nTokenized Abstract:\n{}\n".format(" ".join(tokenized['abstract'])))
        f.write("\nTokenized Sections:\n")
        for sec in tokenized['sections']:
            f.write("\n- {}:\n{}\n".format(sec['header'], " ".join(sec['tokens'])))


def write_jsonl(arxiv_id, result, tokenized):
    json_path = os.path.join(SAVE_DIR, arxiv_id + "_output.jsonl")
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
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def main(keywords, category, max_results, delay):
    query = build_query(keywords, category)
    print("Search Query:", query)
    entries = get_arxiv_entries(query, max_results)
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
                    {'header': sec['header'], 'tokens': spacy_tokenize(sec['text'])}
                    for sec in result['sections']
                ]
            }

            write_output(arxiv_id, result, tokenized)
            write_jsonl(arxiv_id, result, tokenized)
            print(f"Finished: {arxiv_id}")
            time.sleep(delay)

        except Exception as e:
            print(f"Error with {entry.id}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch and process arXiv papers by keywords, category, or both."
    )
    parser.add_argument(
        "--keywords", nargs="*", default=[],
        help="Keywords to search for, e.g. --keywords squarefree pattern_avoidance"
    )
    parser.add_argument(
        "--category", default=None,
        help="arXiv subject category, e.g. --category cs.CL"
    )
    parser.add_argument(
        "--max-results", type=int, default=5,
        help="Maximum number of papers to fetch"
    )
    parser.add_argument(
        "--delay", type=float, default=2.0,
        help="Seconds to sleep between downloads to respect rate limits"
    )
    args = parser.parse_args()

    main(args.keywords, args.category, args.max_results, args.delay)
