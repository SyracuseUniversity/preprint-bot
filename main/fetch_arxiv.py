import os, uuid, requests, json, feedparser, time
from config import ARXIV_CATEGORIES, MAX_RESULTS, DATA_DIR

def fetch_with_retry(url, retries=3, delay=5):
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
    all_papers = []

    for category in ARXIV_CATEGORIES:
        print(f"Fetching {category}")
        base_url = "http://export.arxiv.org/api/query?"
        query = f"search_query=cat:{category}&start=0&max_results={MAX_RESULTS}&sortBy=submittedDate&sortOrder=descending"
        url = base_url + query

        response = fetch_with_retry(url, retries=3, delay=3)

        feed = feedparser.parse(response.content)
        for entry in feed.entries:
            all_papers.append({
                "id": str(uuid.uuid4()),
                "title": entry.title.strip(),
                "summary": entry.summary.strip(),
                "published": entry.published,
                "arxiv_url": entry.link,
                "category": category
            })

        time.sleep(3)  # Important: don't overload arXiv

    print(f"Total papers fetched: {len(all_papers)}")

    with open(os.path.join(DATA_DIR, "arxiv_cs_papers.json"), "w") as f:
        json.dump(all_papers, f, indent=2)

    return all_papers
