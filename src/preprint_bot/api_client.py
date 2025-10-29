import httpx
from typing import List, Dict, Optional

class APIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    # User operations
    async def create_user(self, email: str, name: Optional[str] = None) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/users/",
            json={"email": email, "name": name}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        response = await self.client.get(f"{self.base_url}/users/")
        users = response.json()
        return next((u for u in users if u["email"] == email), None)
    
    # Corpus operations
    async def create_corpus(self, user_id: int, name: str, description: str = None) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/corpora/",
            json={"user_id": user_id, "name": name, "description": description}
        )
        response.raise_for_status()
        return response.json()
    
    # Paper operations
    async def create_paper(self, corpus_id: int, arxiv_id: str, title: str, 
                          abstract: str, metadata: Dict, source: str = "arxiv") -> Dict:
        response = await self.client.post(
            f"{self.base_url}/papers/",
            json={
                "corpus_id": corpus_id,
                "arxiv_id": arxiv_id,
                "title": title,
                "abstract": abstract,
                "metadata": metadata,
                "source": source
            }
        )
        response.raise_for_status()
        return response.json()
    
    # Embedding operations
    async def create_embedding(self, paper_id: int, embedding: List[float], 
                              type: str, model_name: str, section_id: Optional[int] = None) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/embeddings/",
            json={
                "paper_id": paper_id,
                "section_id": section_id,
                "embedding": embedding,
                "type": type,
                "model_name": model_name
            }
        )
        response.raise_for_status()
        return response.json()
    
    # Recommendation operations
    async def create_recommendation_run(self, profile_id: int, user_id: int,
                                       user_corpus_id: int, ref_corpus_id: int,
                                       threshold: str, method: str) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/recommendation-runs/",
            json={
                "profile_id": profile_id,
                "user_id": user_id,
                "user_corpus_id": user_corpus_id,
                "ref_corpus_id": ref_corpus_id,
                "threshold": threshold,
                "method": method
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def create_recommendation(self, run_id: int, paper_id: int, 
                                   score: float, rank: int, summary: str = None) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/recommendations/",
            json={
                "run_id": run_id,
                "paper_id": paper_id,
                "score": score,
                "rank": rank,
                "summary": summary
            }
        )
        response.raise_for_status()
        return response.json()