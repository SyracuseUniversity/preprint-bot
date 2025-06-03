import os
import requests
from pathlib import Path
from config import DATA_DIR

def download_arxiv_pdfs(paper_metadata, output_folder="arxiv_pipeline_data/arxiv_pdfs"):
    os.makedirs(output_folder, exist_ok=True)
    for paper in paper_metadata:
        arxiv_id = paper["arxiv_url"].split("/")[-1]
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        pdf_path = os.path.join(output_folder, f"{arxiv_id}.pdf")

        if not os.path.exists(pdf_path):
            try:
                print(f"Downloading: {pdf_url}")
                r = requests.get(pdf_url)
                if r.status_code == 200:
                    with open(pdf_path, "wb") as f:
                        f.write(r.content)
                else:
                    print(f"Failed to download {arxiv_id}")
            except Exception as e:
                print(f"Error: {e}")
