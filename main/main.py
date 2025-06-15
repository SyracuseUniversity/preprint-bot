# from fetch_arxiv import fetch_arxiv_papers
# from download_arxiv_pdfs import download_arxiv_pdfs
# from embed_papers import embed_papers
# from process_user_pdfs import process_user_papers
# from similarity_matcher import compute_similarity
# from grobid_parser import process_folder

# USER_PDF_FOLDER = "main\my_papers"
# ARXIV_PDF_FOLDER = "arxiv_pipeline_data/arxiv_pdfs"
# USER_PROCESSED = "arxiv_pipeline_data/processed_users"
# ARXIV_PROCESSED = "arxiv_pipeline_data/processed_arxiv"

# def main():
#     print("\nFetching arXiv papers...")
#     all_papers = fetch_arxiv_papers()

#     # print("\n⬇Downloading PDFs...")
#     # download_arxiv_pdfs(all_papers, ARXIV_PDF_FOLDER)

#     print("\nParsing user papers with GROBID...")
#     process_folder(USER_PDF_FOLDER, USER_PROCESSED)

#     print("\nParsing arXiv papers with GROBID...")
#     process_folder(ARXIV_PDF_FOLDER, ARXIV_PROCESSED)

#     print("\nEmbedding arXiv papers...")
#     new_texts, new_embeddings, model = embed_papers(all_papers)

#     print("\nProcessing user PDFs...")
#     user_texts, user_embeddings, user_metadata = process_user_papers(USER_PDF_FOLDER, model)

#     print("\nPerforming similarity search...")
#     matches = compute_similarity(user_embeddings, new_embeddings, all_papers, new_texts)

#     print(f"\nFound {len(matches)} relevant new papers:\n")
#     for i, match in enumerate(matches, 1):
#         print(f"--- Paper #{i} ---")
#         print(f"Title : {match['title']}")
#         print(f"Link  : {match['url']}\n")

# if __name__ == "__main__":
#     main()

from fetch_arxiv import fetch_arxiv_papers
from download_arxiv_pdfs import download_arxiv_pdfs
from grobid_parser import process_folder
from embed_papers import embed_abstracts, embed_sections
from process_user_pdfs import process_user_papers
from similarity_matcher import hybrid_similarity_pipeline
from config import *

USER_PDF_FOLDER = "main/my_papers"
ARXIV_PDF_FOLDER = "main/arxiv_pipeline_data/arxiv_pdfs"
USER_PROCESSED = "main/arxiv_pipeline_data/processed_users"
ARXIV_PROCESSED = "main/arxiv_pipeline_data/processed_arxiv"


def main(threshold_label="medium", model_name=DEFAULT_MODEL_NAME):
    print("\nFetching arXiv papers...")
    all_papers = fetch_arxiv_papers()
    # all_papers = "main/arxiv_pipeline_data/arxiv_pdfs.json"

    # # Uncomment if PDFs are not already downloaded
    # print("\nDownloading PDFs...")
    # download_arxiv_pdfs(all_papers, ARXIV_PDF_FOLDER)

    # print("\nParsing user papers with GROBID...")
    # process_folder(USER_PDF_FOLDER, USER_PROCESSED)

    # print("\nParsing arXiv papers with GROBID...")
    # process_folder(ARXIV_PDF_FOLDER, ARXIV_PROCESSED)

    print("\nEmbedding user abstracts...")
    user_abs_texts, user_abs_embs, model, user_files = embed_abstracts(USER_PROCESSED, model_name)

    print("Embedding arXiv abstracts...")
    arxiv_abs_texts, arxiv_abs_embs, _, _ = embed_abstracts(ARXIV_PROCESSED, model_name)

    print("\nEmbedding user sections...")
    user_sections = embed_sections(USER_PROCESSED, model)

    print("Embedding arXiv sections...")
    arxiv_sections = embed_sections(ARXIV_PROCESSED, model)

    print("\nPerforming hybrid similarity search...")
    matches = hybrid_similarity_pipeline(
        user_abs_embs, arxiv_abs_embs,
        user_sections, arxiv_sections,
        all_papers, user_files,
        threshold_label
    )

    print(f"\nFound {len(matches)} relevant papers:\n")
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match['title']}")
        print(f"   Link: {match['url']}")
        print(f"   Score: {match['score']:.3f}\n")

if __name__ == "__main__":
    import sys
    threshold = sys.argv[1] if len(sys.argv) > 1 else "medium"
    model_name = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MODEL_NAME
    main(threshold, model_name)
