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

    for arxiv_idx, paper in enumerate(all_cs_papers):
        arxiv_file_key = paper["arxiv_url"].split("/")[-1] + "_output.txt"
        arxiv_chunks = arxiv_sections_dict.get(arxiv_file_key)
        if arxiv_chunks is None:
            continue

        for user_file in user_files:
            user_chunks = user_sections_dict.get(user_file)
            if user_chunks is None:
                continue

            sim_matrix = np.dot(user_chunks, arxiv_chunks.T)
            best_score = np.max(sim_matrix)

            if best_score >= threshold:
                final_matches.append({
                    "title": paper["title"],
                    "summary": paper["summary"],
                    "url": paper["arxiv_url"],
                    "published": paper["published"],
                    "score": float(best_score)
                })

    final_matches = sorted(final_matches, key=lambda x: x["score"], reverse=True)

    with open(os.path.join(DATA_DIR, "ranked_matches.json"), "w") as f:
        json.dump(final_matches, f, indent=2)

    return final_matches