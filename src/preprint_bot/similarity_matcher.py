import os
import json
import argparse
import numpy as np
import faiss
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from sklearn.metrics.pairwise import cosine_similarity

from .config import SIMILARITY_THRESHOLDS, DATA_DIR


def hybrid_similarity_pipeline(
    user_abs_embs, arxiv_abs_embs,
    user_sections_dict, arxiv_sections_dict,
    all_cs_papers, user_files,
    threshold_label="medium",
    method="faiss"  # options: "faiss", "cosine", "qdrant"
):
    """
    Compares user papers to arXiv papers using section-level embeddings.
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
        max_score = 0.0

        # ---------- FAISS ----------
        if method == "faiss":
            faiss.normalize_L2(arxiv_chunks)
            dim = arxiv_chunks.shape[1]
            index = faiss.IndexFlatIP(dim)
            index.add(arxiv_chunks)

        # ---------- Qdrant (in-memory) ----------
        elif method == "qdrant":
            dim = arxiv_chunks.shape[1]
            client = QdrantClient(":memory:")
            client.recreate_collection(
                collection_name="arxiv_chunks",
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            points = [
                PointStruct(id=i, vector=vec.tolist()) for i, vec in enumerate(arxiv_chunks)
            ]
            client.upsert(collection_name="arxiv_chunks", points=points)

        # Loop over user files
        for user_file in user_files:
            user_chunks = user_sections_dict.get(user_file)
            if user_chunks is None or len(user_chunks) == 0:
                continue

            user_chunks = np.array(user_chunks).astype("float32")

            if method == "faiss":
                faiss.normalize_L2(user_chunks)
                scores, _ = index.search(user_chunks, k=1)
                best_score = np.max(scores)

            elif method == "cosine":
                norm_arxiv = arxiv_chunks / np.linalg.norm(arxiv_chunks, axis=1, keepdims=True)
                norm_user = user_chunks / np.linalg.norm(user_chunks, axis=1, keepdims=True)
                scores = cosine_similarity(norm_user, norm_arxiv)
                best_score = np.max(scores)

            elif method == "qdrant":
                best_score = 0.0
                for vec in user_chunks:
                    hits = client.search(
                        collection_name="arxiv_chunks",
                        query_vector=vec.tolist(),
                        limit=1
                    )
                    if hits and hits[0].score > best_score:
                        best_score = hits[0].score

            else:
                raise ValueError(f"Unknown method: {method}")

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hybrid section-wise similarity matcher")
    parser.add_argument(
        "--method",
        type=str,
        default="faiss",
        choices=["faiss", "cosine", "qdrant"],
        help="Similarity method to use (default: faiss)"
    )
    parser.add_argument(
        "--threshold",
        type=str,
        default="medium",
        choices=list(SIMILARITY_THRESHOLDS.keys()),
        help="Similarity threshold label (default: medium)"
    )
    args = parser.parse_args()

    method = args.method
    threshold_label = args.threshold

    print(f"Running similarity pipeline with method = {method}, threshold = {threshold_label}")
