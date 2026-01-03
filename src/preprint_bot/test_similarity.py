import asyncio
import sys
sys.path.insert(0, 'src')

from preprint_bot.api_client import APIClient
from preprint_bot.db_similarity_matcher import group_embeddings_by_paper, compute_paper_similarity
import numpy as np

async def debug_similarity():
    client = APIClient()
    
    # Get your corpus (user papers)
    user_corpus_id = 2  # Replace with your actual corpus ID
    arxiv_corpus_id = 1  # Replace with arXiv corpus ID
    
    print("Fetching embeddings...")
    user_embeddings = await client.get_embeddings_by_corpus(user_corpus_id)
    arxiv_embeddings = await client.get_embeddings_by_corpus(arxiv_corpus_id)
    
    print(f"User embeddings: {len(user_embeddings)}")
    print(f"arXiv embeddings: {len(arxiv_embeddings)}")
    
    if user_embeddings and arxiv_embeddings:
        # Check embedding dimensions
        user_dim = len(user_embeddings[0]['embedding'])
        arxiv_dim = len(arxiv_embeddings[0]['embedding'])
        print(f"\nEmbedding dimensions:")
        print(f"  User: {user_dim}")
        print(f"  arXiv: {arxiv_dim}")
        
        # Check if normalized
        user_norm = np.linalg.norm(user_embeddings[0]['embedding'])
        arxiv_norm = np.linalg.norm(arxiv_embeddings[0]['embedding'])
        print(f"\nEmbedding norms (should be ~1.0 if normalized):")
        print(f"  User: {user_norm:.4f}")
        print(f"  arXiv: {arxiv_norm:.4f}")
        
        # Group by paper
        user_papers = group_embeddings_by_paper(user_embeddings)
        arxiv_papers = group_embeddings_by_paper(arxiv_embeddings)
        
        print(f"\nPapers with embeddings:")
        print(f"  User papers: {len(user_papers)}")
        print(f"  arXiv papers: {len(arxiv_papers)}")
        
        # Test similarity between first user paper and first arXiv paper
        user_paper_id = list(user_papers.keys())[0]
        arxiv_paper_id = list(arxiv_papers.keys())[0]
        
        user_embs = user_papers[user_paper_id]
        arxiv_embs = arxiv_papers[arxiv_paper_id]
        
        print(f"\nTest similarity calculation:")
        print(f"  User paper embeddings: {len(user_embs)}")
        print(f"  arXiv paper embeddings: {len(arxiv_embs)}")
        
        # Test cosine similarity
        sim_cosine = compute_paper_similarity(user_embs, arxiv_embs, method="cosine")
        print(f"  Cosine similarity: {sim_cosine:.4f}")
        
        # Test with raw dot product
        user_matrix = np.array(user_embs, dtype=np.float32)
        arxiv_matrix = np.array(arxiv_embs, dtype=np.float32)
        
        # Raw dot product (for normalized vectors, this IS cosine similarity)
        dot_products = user_matrix @ arxiv_matrix.T
        print(f"  Max dot product: {np.max(dot_products):.4f}")
        print(f"  Min dot product: {np.min(dot_products):.4f}")
        print(f"  Mean dot product: {np.mean(dot_products):.4f}")
        
        # Try a few random pairs
        print(f"\nRandom paper pair similarities:")
        for i in range(min(5, len(user_papers), len(arxiv_papers))):
            up_id = list(user_papers.keys())[i % len(user_papers)]
            ap_id = list(arxiv_papers.keys())[i % len(arxiv_papers)]
            sim = compute_paper_similarity(user_papers[up_id], arxiv_papers[ap_id], "cosine")
            
            up = await client.get_paper_by_id(up_id)
            ap = await client.get_paper_by_id(ap_id)
            
            print(f"  {sim:.4f} | User: {up['title'][:40]}... vs arXiv: {ap['title'][:40]}...")
    
    await client.close()

asyncio.run(debug_similarity())