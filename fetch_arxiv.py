"""
Module to fetch recent arXiv papers using the arXiv API and save them as JSON.

Features:
- Iterates over predefined categories from `config.py`.
- Uses retry logic to handle temporary network failures.
- Extracts metadata like title, summary, URL, and publication date.
- Writes the results to a JSON file for later processing in the pipeline.

This script is polite to arXiv by sleeping between requests and using small batch sizes.
"""

import os, uuid, requests, json, feedparser, time
from config import ARXIV_CATEGORIES, MAX_RESULTS, DATA_DIR

def fetch_with_retry(url, retries=3, delay=5):
    """
    Attempt to fetch a URL with retry logic.

    Args:
        url (str): URL to fetch.
        retries (int): Number of retry attempts before failing.
        delay (int): Seconds to wait between retries.

    Returns:
        requests.Response: The HTTP response if successful.

    Raises:
        Exception: If all retries fail.
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"Attempt {attempt+1}/{retries} failed: {e}")
            time.sleep(delay)
    raise Exception(f"Failed to fetch after {retries} attempts: {url}")

def fetch_arxiv_papers():
    """
    Fetches recent papers from arXiv based on categories defined in `config.py`.

    Returns:
        all_papers (list of dict): List of paper metadata including title, summary, URL, and category.
    
    Saves:
        arxiv_cs_papers.json: JSON file containing metadata of fetched papers.
    """
    all_papers = []

    for category in ARXIV_CATEGORIES:
        print(f"Fetching {category}")

        # Construct API query for the given category
        base_url = "http://export.arxiv.org/api/query?"
        query = f"search_query=cat:{category}&start=0&max_results={MAX_RESULTS}&sortBy=submittedDate&sortOrder=descending"
        url = base_url + query

        # Robust fetching with retry logic
        response = fetch_with_retry(url, retries=3, delay=3)

        # Parse the returned Atom XML using feedparser
        feed = feedparser.parse(response.content)
        for entry in feed.entries:
            all_papers.append({
                "id": str(uuid.uuid4()),               # Unique ID for internal use
                "title": entry.title.strip(),
                "summary": entry.summary.strip(),
                "published": entry.published,
                "arxiv_url": entry.link,
                "category": category
            })

        # Sleep to avoid hitting arXiv rate limits
        time.sleep(3)

    print(f"Total papers fetched: {len(all_papers)}")

    # Save the fetched metadata to a JSON file
    with open(os.path.join(DATA_DIR, "arxiv_cs_papers.json"), "w") as f:
        json.dump(all_papers, f, indent=2)

    return all_papers
