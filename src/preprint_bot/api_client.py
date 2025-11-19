import httpx
from typing import List, Dict, Optional

class APIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def close(self):
        await self.client.aclose()
    
    
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
    
    async def get_or_create_user(self, email: str, name: Optional[str] = None) -> Dict:
        """Get existing user or create new one"""
        user = await self.get_user_by_email(email)
        if user:
            return user
        return await self.create_user(email, name)
    
    
    async def create_corpus(self, user_id: int, name: str, description: str = None) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/corpora/",
            json={"user_id": user_id, "name": name, "description": description}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_corpus_by_name(self, user_id: int, name: str) -> Optional[Dict]:
        """Get corpus by user_id and name"""
        response = await self.client.get(f"{self.base_url}/corpora/")
        corpora = response.json()
        return next((c for c in corpora if c["user_id"] == user_id and c["name"] == name), None)
    
    async def get_or_create_corpus(self, user_id: int, name: str, description: str = None) -> Dict:
        """Get existing corpus or create new one"""
        corpus = await self.get_corpus_by_name(user_id, name)
        if corpus:
            return corpus
        return await self.create_corpus(user_id, name, description)
    
    
    async def create_paper(self, corpus_id: int, arxiv_id: str, title: str, 
                          abstract: str, metadata: Dict, source: str = "arxiv",
                          processed_text_path: str = None, pdf_path: str = None) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/papers/",
            json={
                "corpus_id": corpus_id,
                "arxiv_id": arxiv_id,
                "title": title,
                "abstract": abstract,
                "metadata": metadata,
                "source": source,
                "file_path": pdf_path  # CHANGED: was pdf_path, now file_path
            }
        )
        response.raise_for_status()
        paper = response.json()
        
        # ADDED: Update processed text path separately if provided
        if processed_text_path:
            await self.update_paper_processed_path(paper["id"], processed_text_path)
        
        return paper
    
    async def update_paper_processed_path(self, paper_id: int, path: str) -> Dict:
        """Update the processed text path for a paper"""
        response = await self.client.post(
            f"{self.base_url}/papers/{paper_id}/processed-text",
            params={"path": path}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[Dict]:
        """Get paper by arxiv_id"""
        response = await self.client.get(f"{self.base_url}/papers/")
        papers = response.json()
        return next((p for p in papers if p.get("arxiv_id") == arxiv_id), None)
    
    async def get_paper_by_id(self, paper_id: int) -> Optional[Dict]:
        """Get paper by ID"""
        response = await self.client.get(f"{self.base_url}/papers/{paper_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    
    async def get_papers_by_corpus(self, corpus_id: int) -> List[Dict]:
        """Get all papers in a corpus"""
        response = await self.client.get(f"{self.base_url}/papers/?corpus_id={corpus_id}")
        response.raise_for_status()
        return response.json()
    
    
    async def create_section(self, paper_id: int, header: str, text: str) -> Dict:
        """Create a section for a paper"""
        response = await self.client.post(
            f"{self.base_url}/sections/",
            json={
                "paper_id": paper_id,
                "header": header,  # Changed from section_header
                "text": text       # Changed from section_text
            }
        )
        response.raise_for_status()
        return response.json()
        
    async def get_sections_by_paper(self, paper_id: int) -> List[Dict]:
        """Get all sections for a paper"""
        response = await self.client.get(f"{self.base_url}/sections/?paper_id={paper_id}")
        response.raise_for_status()
        return response.json()
    
    
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
    
    async def get_embeddings_by_corpus(self, corpus_id: int, type: str = "abstract") -> List[Dict]:
        """Get all embeddings for papers in a corpus"""
        response = await self.client.get(
            f"{self.base_url}/embeddings/?corpus_id={corpus_id}&type={type}"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_embeddings_by_paper(self, paper_id: int, type: str = None) -> List[Dict]:
        """Get embeddings for a specific paper"""
        params = {"paper_id": paper_id}
        if type:
            params["type"] = type
        response = await self.client.get(f"{self.base_url}/embeddings/", params=params)
        response.raise_for_status()
        return response.json()
    
    async def batch_create_embeddings(self, embeddings: List[Dict]) -> List[Dict]:
        """Batch create multiple embeddings"""
        response = await self.client.post(
            f"{self.base_url}/embeddings/batch",
            json=embeddings
        )
        response.raise_for_status()
        return response.json()
    
    async def create_summary(self, paper_id: int, mode: str, summary_text: str, summarizer: str) -> Dict:
        """Create a summary for a paper"""
        response = await self.client.post(
            f"{self.base_url}/summaries/",
            json={
                "paper_id": paper_id,
                "mode": mode,
                "summary_text": summary_text,
                "summarizer": summarizer
            }
        )
        response.raise_for_status()
        return response.json()
    
    
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
    
    async def get_recommendations_by_run(self, run_id: int) -> List[Dict]:
        """Get all recommendations for a run"""
        response = await self.client.get(f"{self.base_url}/recommendations/?run_id={run_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_recommendations_with_papers(self, run_id: int, limit: int = 50) -> List[Dict]:
        """Get recommendations with full paper details"""
        response = await self.client.get(
            f"{self.base_url}/recommendations/run/{run_id}/with-papers",
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()
    
    
    async def create_processing_run(self, run_type: str, category: str) -> Dict:
        """Track a processing run"""
        # NOTE: This endpoint doesn't exist yet in the API
        # You may want to add it or remove this method
        return {"id": 0, "run_type": run_type, "category": category}
    
    async def update_processing_run(self, run_id: int, status: str, papers_processed: int = None) -> Dict:
        """Update processing run status"""
        # NOTE: This endpoint doesn't exist yet in the API
        # You may want to add it or remove this method
        return {"id": run_id, "status": status}