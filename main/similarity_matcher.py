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
    top_n = 20

    # 1. Abstract-level similarity to shortlist candidates
    index = faiss.IndexFlatIP(user_abs_embs.shape[1])
    index.add(user_abs_embs)
    sims, idxs = index.search(arxiv_abs_embs, 1)

    prelim_matches = []
    for i, score in enumerate(sims):
        if score[0] >= threshold:
            prelim_matches.append((i, score[0]))

    prelim_matches = sorted(prelim_matches, key=lambda x: x[1], reverse=True)[:top_n]

    # 2. Section-level similarity
    final_matches = []
    for arxiv_idx, abs_score in prelim_matches:
        arxiv_file_key = all_cs_papers[arxiv_idx]["arxiv_url"].split("/")[-1] + "_output.txt"
        arxiv_chunks = arxiv_sections_dict.get(arxiv_file_key)

        if arxiv_chunks is None:
            continue

        for user_idx, user_file in enumerate(user_files):
            user_chunks = user_sections_dict.get(user_file)
            if user_chunks is None:
                continue

            sim_matrix = np.dot(user_chunks, arxiv_chunks.T)
            best_score = np.max(sim_matrix)
            if best_score >= threshold:
                final_matches.append({
                    "title": all_cs_papers[arxiv_idx]["title"],
                    "summary": all_cs_papers[arxiv_idx]["summary"],
                    "url": all_cs_papers[arxiv_idx]["arxiv_url"],
                    "published": all_cs_papers[arxiv_idx]["published"],
                    "score": float(best_score)
                })

    final_matches = sorted(final_matches, key=lambda x: x["score"], reverse=True)

    with open(os.path.join(DATA_DIR, "ranked_matches.json"), "w") as f:
        json.dump(final_matches, f, indent=2)

    return final_matches
