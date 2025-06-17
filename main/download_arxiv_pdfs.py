import os
import time
import requests
from pathlib import Path
from config import DATA_DIR

HEADERS = {
    "User-Agent": "arxiv-pdf-fetcher/1.0 (contact: ugaikwad@syr.edu)"
}

def download_arxiv_pdfs(paper_metadata, output_folder="arxiv_pipeline_data/arxiv_pdfs", delay_seconds=5):
    os.makedirs(output_folder, exist_ok=True)

    for idx, paper in enumerate(paper_metadata):
        arxiv_id = paper["arxiv_url"].split("/")[-1]
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        pdf_path = os.path.join(output_folder, f"{arxiv_id}.pdf")

        if not os.path.exists(pdf_path):
            try:
                print(f"[{idx+1}/{len(paper_metadata)}] Downloading: {pdf_url}")
                r = requests.get(pdf_url, headers=HEADERS)

                if r.headers.get("Content-Type", "").lower().startswith("application/pdf"):
                    with open(pdf_path, "wb") as f:
                        f.write(r.content)
                    print(f"Saved to {pdf_path}")
                else:
                    print(f"Blocked by arXiv or CAPTCHA triggered for {arxiv_id}.")
                    with open(f"{pdf_path}.html", "w", encoding="utf-8") as f:
                        f.write(r.text)
            except Exception as e:
                print(f"Error downloading {arxiv_id}: {e}")
            finally:
                time.sleep(delay_seconds)
