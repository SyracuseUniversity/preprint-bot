"""
Database-integrated similarity matcher
Uses embeddings stored in PostgreSQL to find similar papers
"""
import numpy as np
from typing import List, Dict
from sklearn.metrics.pairwise import cosine_similarity
import faiss


async def run_similarity_matching(
    api_client,
    user_id: int,
    user_corpus_id: int,
    arxiv_corpus_id: int,
    threshold: str = "medium",
    method: str = "cosine",
    model_name: str = "all-MiniLM-L6-v2",
    top_k: int = 50,
    use_sections: bool = True
):
    """
    Run similarity matching between user papers and arXiv papers.
    """
    from .config import SIMILARITY_THRESHOLDS
    
    threshold_value = SIMILARITY_THRESHOLDS.get(threshold, 0.6)
    
    print(f"\n▶ Running similarity matching...")
    print(f"  Method: {method}")
    print(f"  Threshold: {threshold} ({threshold_value})")
    print(f"  Using: {'Section embeddings' if use_sections else 'Abstract embeddings'}")
    
    # Create recommendation run
    run = await api_client.create_recommendation_run(
        profile_id=None,
        user_id=user_id,
        user_corpus_id=user_corpus_id,
        ref_corpus_id=arxiv_corpus_id,
        threshold=threshold,
        method=f"{method}_{'sections' if use_sections else 'abstract'}"
    )
    run_id = run["id"]
    print(f"✓ Created recommendation run {run_id}")
    
    if use_sections:
        # Get ALL embeddings (both abstract and section)
        print("▶ Fetching user paper embeddings (abstract + sections)...")
        user_embeddings = await api_client.get_embeddings_by_corpus(user_corpus_id)
        
        print("▶ Fetching arXiv paper embeddings (abstract + sections)...")
        arxiv_embeddings = await api_client.get_embeddings_by_corpus(arxiv_corpus_id)
    else:
        # Just abstracts
        print("▶ Fetching user paper embeddings (abstract only)...")
        user_embeddings = await api_client.get_embeddings_by_corpus(user_corpus_id, type="abstract")
        
        print("▶ Fetching arXiv paper embeddings (abstract only)...")
        arxiv_embeddings = await api_client.get_embeddings_by_corpus(arxiv_corpus_id, type="abstract")
    
    if not user_embeddings:
        print("✗ No user embeddings found. Run embedding step first.")
        return
    
    print(f"✓ Found {len(user_embeddings)} user embeddings")
    
    if not arxiv_embeddings:
        print("✗ No arXiv embeddings found. Run corpus mode first.")
        return
    
    print(f"✓ Found {len(arxiv_embeddings)} arXiv embeddings")
    
    # Group embeddings by paper
    user_papers = group_embeddings_by_paper(user_embeddings)
    arxiv_papers = group_embeddings_by_paper(arxiv_embeddings)
    
    print(f"✓ Grouped into {len(user_papers)} user papers and {len(arxiv_papers)} arXiv papers")
    
    # Compute similarities
    print(f"▶ Computing paper-to-paper similarities...")
    
    paper_scores = {}
    
    for arxiv_paper_id, arxiv_embs in arxiv_papers.items():
        max_similarity = 0.0
        
        # Compare this arXiv paper against ALL user papers
        for user_paper_id, user_embs in user_papers.items():
            similarity = compute_paper_similarity(user_embs, arxiv_embs, method)
            max_similarity = max(max_similarity, similarity)
        
        paper_scores[arxiv_paper_id] = max_similarity
    
    # Filter by threshold
    filtered_papers = {pid: score for pid, score in paper_scores.items() if score >= threshold_value}
    
    print(f"✓ Found {len(filtered_papers)} papers above threshold")
    
    # Sort and take top-k
    sorted_papers = sorted(filtered_papers.items(), key=lambda x: x[1], reverse=True)[:top_k]
    
    print(f"✓ Storing top {len(sorted_papers)} recommendations...")
    
    # Store recommendations
    stored_count = 0
    for rank, (paper_id, score) in enumerate(sorted_papers, 1):
        try:
            paper = await api_client.get_paper_by_id(paper_id)
            
            await api_client.create_recommendation(
                run_id=run_id,
                paper_id=paper_id,
                score=score,
                rank=rank,
                summary=paper.get("abstract", "")[:500]
            )
            stored_count += 1
            
            print(f"  {rank}. {paper['title'][:60]}... (score: {score:.3f})")
            
        except Exception as e:
            print(f"✗ Failed to store recommendation for paper {paper_id}: {e}")
    
    print(f"\n✓ Stored {stored_count} recommendations")
    print(f"✓ Recommendation run ID: {run_id}")
    
    return run_id


def group_embeddings_by_paper(embeddings):
    """Group embeddings by paper_id"""
    papers = {}
    for emb in embeddings:
        paper_id = emb['paper_id']
        if paper_id not in papers:
            papers[paper_id] = []
        papers[paper_id].append(emb['embedding'])
    return papers


def compute_paper_similarity(user_embs, arxiv_embs, method="cosine"):
    """
    Compute similarity between two papers using all their embeddings.
    Returns the maximum similarity across all embedding pairs.
    """
    user_matrix = np.array(user_embs, dtype=np.float32)
    arxiv_matrix = np.array(arxiv_embs, dtype=np.float32)
    
    if method == "faiss":
        similarities = compute_faiss_similarity(user_matrix, arxiv_matrix)
    else:
        similarities = compute_cosine_similarity(user_matrix, arxiv_matrix)
    
    # Return maximum similarity across all pairs
    return float(np.max(similarities))


def compute_cosine_similarity(user_matrix: np.ndarray, arxiv_matrix: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between user and arXiv embeddings."""
    user_norm = user_matrix / np.linalg.norm(user_matrix, axis=1, keepdims=True)
    arxiv_norm = arxiv_matrix / np.linalg.norm(arxiv_matrix, axis=1, keepdims=True)
    return cosine_similarity(user_norm, arxiv_norm)


def compute_faiss_similarity(user_matrix: np.ndarray, arxiv_matrix: np.ndarray) -> np.ndarray:
    """Compute similarity using FAISS."""
    faiss.normalize_L2(user_matrix)
    faiss.normalize_L2(arxiv_matrix)
    dim = arxiv_matrix.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(arxiv_matrix)
    k = arxiv_matrix.shape[0]
    scores, _ = index.search(user_matrix, k)
    return scores