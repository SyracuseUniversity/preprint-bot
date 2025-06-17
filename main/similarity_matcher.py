import os
import json
import numpy as np
import faiss
from config import SIMILARITY_THRESHOLDS, DATA_DIR

def hybrid_similarity_pipeline(
    user_abs_embs, arxiv_abs_embs,
    user_sections_dict, arxiv_sections_dict,
    all_cs_papers, user_files,
    threshold_label="medium"
):
    threshold = SIMILARITY_THRESHOLDS.get(threshold_label, 0.7)
    final_matches = []

    for paper in all_cs_papers:
        # ✅ Keep versioned arXiv ID in file name
        arxiv_id_with_version = paper["arxiv_url"].split("/")[-1]
        arxiv_file_key = f"{arxiv_id_with_version}_output.txt"
        arxiv_chunks = arxiv_sections_dict.get(arxiv_file_key)

        if arxiv_chunks is None or len(arxiv_chunks) == 0:
            continue

        # Normalize Arxiv chunks
        arxiv_chunks = np.array(arxiv_chunks).astype("float32")
        faiss.normalize_L2(arxiv_chunks)

        # Build FAISS index
        dim = arxiv_chunks.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(arxiv_chunks)

        for user_file in user_files:
            user_chunks = user_sections_dict.get(user_file)
            if user_chunks is None or len(user_chunks) == 0:
                continue

            user_chunks = np.array(user_chunks).astype("float32")
            faiss.normalize_L2(user_chunks)

            scores, _ = index.search(user_chunks, k=1)
            best_score = np.max(scores)

            if best_score >= threshold:
                final_matches.append({
                    "title": paper["title"],
                    "summary": paper["summary"],
                    "url": paper["arxiv_url"],
                    "published": paper["published"],
                    "score": float(best_score)
                })

    final_matches = sorted(final_matches, key=lambda x: x["score"], reverse=True)

    with open(os.path.join(DATA_DIR, "ranked_matches.json"), "w", encoding="utf-8") as f:
        json.dump(final_matches, f, indent=2)

    return final_matches
