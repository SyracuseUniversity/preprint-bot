import os, uuid, requests, json, feedparser
from config import ARXIV_CATEGORIES, MAX_RESULTS, DATA_DIR

def fetch_arxiv_papers():
    all_papers = []

    for category in ARXIV_CATEGORIES:
        print(f"Fetching {category}")
        base_url = "http://export.arxiv.org/api/query?"
        query = f"search_query=cat:{category}&start=0&max_results={MAX_RESULTS}&sortBy=submittedDate&sortOrder=descending"
        response = requests.get(base_url + query)

        if response.status_code == 200:
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
        else:
            print(f"Failed to fetch {category}")

    print(f"Total papers fetched: {len(all_papers)}")

    with open(os.path.join(DATA_DIR, "arxiv_cs_papers.json"), "w") as f:
        json.dump(all_papers, f, indent=2)

    return all_papers
