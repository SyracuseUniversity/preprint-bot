import os
import json
import numpy as np
import faiss
from .config import SIMILARITY_THRESHOLDS, DATA_DIR

"""
Hybrid Section-wise Similarity Matching
---------------------------------------

This function compares each user-uploaded paper to every arXiv paper using
section-level embeddings rather than full-document embeddings.

Why section-wise?
- Embedding an entire paper into a single vector can blur topic distinctions
  and run into length limits.
- Breaking each paper into sections (or chunks) preserves semantic focus,
  enabling more precise similarity matching.
- Even if only part of a paper is relevant (e.g., its Methods section), it can be matched.

How it works:
-------------
1. For each arXiv paper:
    - Its sections are embedded into vectors.
    - These vectors are normalized and indexed using FAISS for fast retrieval.

2. For each user paper:
    - Each section is also embedded and normalized.
    - For every arXiv paper's FAISS index, we search each user section vector
      to find the most similar section in the arXiv paper.
    - This gives a set of similarity scores (one for each section).

3. We take the maximum score from those comparisons as the similarity
   between the user paper and the arXiv paper.

4. If this best score exceeds a threshold (e.g., 0.7 for "medium"), the arXiv
   paper is considered a match and is saved with its title, summary, URL, and score.

5. After all comparisons, the matched papers are sorted by score in descending order
   and saved to disk.

Benefits:
---------
- Fine-grained comparison captures partial overlaps between papers.
- Works well even if the structure or section titles vary.
- More interpretable and accurate than full-document embedding approaches.

Dependencies:
-------------
- FAISS (for efficient similarity search)
- Sentence-transformers or similar model for embeddings
- JSON files with parsed paper sections from GROBID or equivalent
"""

def hybrid_similarity_pipeline(
    user_abs_embs, arxiv_abs_embs,
    user_sections_dict, arxiv_sections_dict,
    all_cs_papers, user_files,
    threshold_label="medium"
):
    """
    Compares user papers to arXiv papers using section-level embeddings.

    For each arXiv paper, builds a FAISS index from its section embeddings.
    Then, compares each user paper's sections to find the most similar chunk.
    If the best similarity score exceeds a threshold, the arXiv paper is added
    to the results. Matches are ranked and saved to disk.

    Returns:
        A list of matched arXiv papers sorted by similarity score.
    """

    threshold = SIMILARITY_THRESHOLDS.get(threshold_label, 0.7)
    final_matches_dict = {}

    for paper in all_cs_papers:
        arxiv_id_with_version = paper["arxiv_url"].split("/")[-1]
        arxiv_file_key = f"{arxiv_id_with_version}_output.txt"
        arxiv_chunks = arxiv_sections_dict.get(arxiv_file_key)

        if arxiv_chunks is None or len(arxiv_chunks) == 0:
            continue

        arxiv_chunks = np.array(arxiv_chunks).astype("float32")
        faiss.normalize_L2(arxiv_chunks)

        dim = arxiv_chunks.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(arxiv_chunks)

        max_score = 0.0

        for user_file in user_files:
            user_chunks = user_sections_dict.get(user_file)
            if user_chunks is None or len(user_chunks) == 0:
                continue

            user_chunks = np.array(user_chunks).astype("float32")
            faiss.normalize_L2(user_chunks)

            scores, _ = index.search(user_chunks, k=1)
            best_score = np.max(scores)

            max_score = max(max_score, best_score)

        if max_score >= threshold:
            final_matches_dict[paper["arxiv_url"]] = {
                "title": paper["title"],
                "summary": paper["summary"],
                "url": paper["arxiv_url"],
                "published": paper["published"],
                "score": float(max_score)
            }

    final_matches = sorted(final_matches_dict.values(), key=lambda x: x["score"], reverse=True)

    with open(os.path.join(DATA_DIR, "ranked_matches.json"), "w", encoding="utf-8") as f:
        json.dump(final_matches, f, indent=2)

    return final_matches
