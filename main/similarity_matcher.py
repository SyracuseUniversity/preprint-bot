import os, json
import faiss
from config import SIMILARITY_THRESHOLD, DATA_DIR

def compute_similarity(user_embeddings, new_embeddings, all_cs_papers, new_texts):
    dimension = user_embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(user_embeddings)

    similarities, indices = index.search(new_embeddings, 1)

    ranked_matches = []
    for i in range(len(new_texts)):
        score = float(similarities[i][0])
        if score >= SIMILARITY_THRESHOLD:
            ranked_matches.append({
                "title": all_cs_papers[i]['title'],
                "summary": all_cs_papers[i]['summary'],
                "url": all_cs_papers[i]['arxiv_url'],
                "published": all_cs_papers[i]['published'],
                "score": score
            })

    ranked_matches = sorted(ranked_matches, key=lambda x: x["score"], reverse=True)

    with open(os.path.join(DATA_DIR, "ranked_matches.json"), "w") as f:
        json.dump(ranked_matches, f, indent=2)

    return ranked_matches
