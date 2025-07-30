"""
Module to download PDFs of arXiv papers given their metadata.

This script:
- Extracts arXiv IDs from paper metadata.
- Downloads corresponding PDFs from arXiv using their public URL pattern.
- Applies polite scraping practices (User-Agent, delays).
- Saves PDFs to the configured output directory.
- Handles and logs potential errors, including HTML pages triggered by CAPTCHAs.

Dependencies:
- requests
- time
- os
- pathlib
"""

import os
import time
import requests
from pathlib import Path
from .config import DATA_DIR

# Custom headers to identify the request and avoid getting blocked
HEADERS = {
    "User-Agent": "arxiv-pdf-fetcher/1.0 (contact: ugaikwad@syr.edu)"
}

def download_arxiv_pdfs(paper_metadata, output_folder="arxiv_pipeline_data/arxiv_pdfs", delay_seconds=5):
    """
    Downloads PDFs of arXiv papers based on provided metadata.

    Parameters:
    - paper_metadata (list): List of dicts, each containing at least an 'arxiv_url' key.
    - output_folder (str): Destination folder for saving PDFs. Default is 'arxiv_pipeline_data/arxiv_pdfs'.
    - delay_seconds (int): Delay between requests to avoid rate-limiting or CAPTCHAs. Default is 5 seconds.

    Behavior:
    - If a file already exists, it skips the download.
    - If content-type is not PDF (e.g., due to CAPTCHA), saves the HTML response for inspection.
    """
    os.makedirs(output_folder, exist_ok=True)

    for idx, paper in enumerate(paper_metadata):
        arxiv_id = paper["arxiv_url"].split("/")[-1]
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        pdf_path = os.path.join(output_folder, f"{arxiv_id}.pdf")

        if not os.path.exists(pdf_path):
            try:
                print(f"[{idx + 1}/{len(paper_metadata)}] Downloading: {pdf_url}")
                r = requests.get(pdf_url, headers=HEADERS)

                # Check if the response is a valid PDF
                if r.headers.get("Content-Type", "").lower().startswith("application/pdf"):
                    with open(pdf_path, "wb") as f:
                        f.write(r.content)
                    print(f"Saved to {pdf_path}")
                else:
                    print(f"Blocked by arXiv or CAPTCHA triggered for {arxiv_id}.")
                    # Save the HTML content to inspect what went wrong
                    with open(f"{pdf_path}.html", "w", encoding="utf-8") as f:
                        f.write(r.text)
            except Exception as e:
                print(f"Error downloading {arxiv_id}: {e}")
            finally:
                # Sleep to avoid hitting rate limits
                time.sleep(delay_seconds)
