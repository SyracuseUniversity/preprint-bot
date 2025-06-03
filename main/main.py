from fetch_arxiv import fetch_arxiv_papers
from download_arxiv_pdfs import download_arxiv_pdfs
from embed_papers import embed_papers
from process_user_pdfs import process_user_papers
from similarity_matcher import compute_similarity
from grobid_parser import process_folder

USER_PDF_FOLDER = "main\my_papers"
ARXIV_PDF_FOLDER = "arxiv_pipeline_data/arxiv_pdfs"
USER_PROCESSED = "arxiv_pipeline_data/processed_users"
ARXIV_PROCESSED = "arxiv_pipeline_data/processed_arxiv"

def main():
    print("\nFetching arXiv papers...")
    all_cs_papers = fetch_arxiv_papers()

    # print("\n⬇Downloading PDFs...")
    # download_arxiv_pdfs(all_cs_papers, ARXIV_PDF_FOLDER)

    print("\nParsing user papers with GROBID...")
    process_folder(USER_PDF_FOLDER, USER_PROCESSED)

    print("\nParsing arXiv papers with GROBID...")
    process_folder(ARXIV_PDF_FOLDER, ARXIV_PROCESSED)

    print("\nEmbedding arXiv papers...")
    new_texts, new_embeddings, model = embed_papers(all_cs_papers)

    print("\nProcessing user PDFs...")
    user_texts, user_embeddings, user_metadata = process_user_papers(USER_PDF_FOLDER, model)

    print("\nPerforming similarity search...")
    matches = compute_similarity(user_embeddings, new_embeddings, all_cs_papers, new_texts)

    print(f"\nFound {len(matches)} relevant new papers:\n")
    for i, match in enumerate(matches, 1):
        print(f"--- Paper #{i} ---")
        print(f"Title : {match['title']}")
        print(f"Link  : {match['url']}\n")

if __name__ == "__main__":
    main()
