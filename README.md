# Preprint Bot

Preprint Bot is an AI-based pipeline that automates the discovery of relevant academic preprints from various preprint servers. It takes a collection of your own research papers, finds the latest preprints in a specified category, and generates a ranked list of recommendations based on semantic content similarity. The final list of recommendations with a concise summary is delivered to you by email.

## How It Works

1.  **Fetch**: Queries the preprint server API for the most recent papers in a category
2. **Download & Parse**: Downloads the PDFs for the new papers. It then uses a running GROBID instance to parse both the new PDFs and the user's reference PDFs into structured text.
3. **Summarization**: Generates an additional AI-based summary for each new paper
4. **Embed**: Uses Transformer models to convert the abstracts and section texts of all papers into numerical vectors (embeddings)
5. **Match**: Compares the vectors from the user's papers against the new preprints to calculate a similarity score
6. **Rank & Save**: Filters out matches below a certain threshold and saves the final, ranked list. 
7. **Email**(under development): Reads the ranked list and sends the report to a specified user email

## Setup & Installation
1. **Prerequisites**: This project requires a locally running GROBID server. GROBID is a machine learning tool that parses scholarly documents.
	- Follow the official  [GROBID installation instructions](https://grobid.readthedocs.io/en/latest/Install-Grobid/) to set it up.
	- The pipeline expects the GROBID server to be available at `http://localhost:8070`.
2. **Clone the Repository**
	```
	git clone https://github.com/SyracuseUniversity/preprint-bot.git
	cd preprint-bot
	```
3. **Install Dependencies**: It is recommended to use a virtual environment
	```
	python -m venv venv source venv/bin/activate # On Windows, use `venv\Scripts\activate` 
	pip install -e .
	```
4. **Optional Dependencies**: If you want to install optional dependencies such as - GPU supported PyTorch or Qdrant client for similarity matching use:
```
pip install preprint_bot[all]
```
## Usage
1. **Add Your Papers**: Place your own relevant PDF papers (the ones you want to find similar articles to) into the `user_pdfs/` directory.
2. **Run the Pipeline**: Execute the main pipeline script from your terminal. You can specify the category, similarity threshold and other options.
	```
	preprint_bot --category cs.LG --threshold medium
	```
	- The `--category` argument specifies the category of papers to search.
	- The `--threshold` can be `low`, `medium`, or `high` to control how strict the matching is.
	- This process can take a while, especially the first time it runs. You can use `--skip-` flags (e.g., `--skip-download`, `--skip-parse`, `--skip-summarize`,`--skip-embed`) on subsequent runs to reuse previous results.
3. **Send the Email Report**: After the pipeline successfully creates the `ranked_matches.json` file, which will then be sent as an email.
