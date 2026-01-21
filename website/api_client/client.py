import httpx
from typing import Optional, List, Dict

class WebAPIClient:
    """Async API client for Preprint Bot backend"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or "http://127.0.0.1:8000"
        self.client = httpx.AsyncClient(timeout=60.0)
        self.token = None
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token if available"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    # Auth methods
    async def login(self, email: str, password: str) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data.get('access_token')
        return data
    
    async def register(self, email: str, password: str, name: Optional[str] = None) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/auth/register",
            json={"email": email, "password": password, "name": name}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data.get('access_token')
        return data
    
    async def request_password_reset(self, email: str) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/auth/request-reset",
            json={"email": email}
        )
        response.raise_for_status()
        return response.json()
    
    async def reset_password(self, token: str, new_password: str) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/auth/reset-password",
            json={"token": token, "new_password": new_password}
        )
        response.raise_for_status()
        return response.json()
    
    async def verify_session(self, user_id: int) -> Dict:
        response = await self.client.get(
            f"{self.base_url}/auth/verify/{user_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # User methods
    async def get_user(self, user_id: int) -> Dict:
        response = await self.client.get(
            f"{self.base_url}/users/{user_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def update_user(self, user_id: int, email: str = None, name: str = None) -> Dict:
        data = {}
        if email:
            data['email'] = email
        if name:
            data['name'] = name
        
        response = await self.client.patch(
            f"{self.base_url}/users/{user_id}",
            json=data,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def list_users(self) -> List[Dict]:
        response = await self.client.get(
            f"{self.base_url}/users/",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # Profile methods
    async def create_profile(self, user_id: int, name: str, keywords: List[str],
                           categories: List[str] = None,
                           frequency: str = "weekly", threshold: str = "medium",
                           top_x: int = 10) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/profiles/",
            json={
                "user_id": user_id,
                "name": name,
                "keywords": keywords,
                "categories": categories or [],
                "email_notify": True,
                "frequency": frequency,
                "threshold": threshold,
                "top_x": top_x
            },
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_profile(self, profile_id: int) -> Dict:
        response = await self.client.get(
            f"{self.base_url}/profiles/{profile_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def list_profiles(self) -> List[Dict]:
        response = await self.client.get(
            f"{self.base_url}/profiles/",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_user_profiles(self, user_id: int) -> List[Dict]:
        profiles = await self.list_profiles()
        return [p for p in profiles if p['user_id'] == user_id]
    
    async def update_profile(self, profile_id: int, **kwargs) -> Dict:
        response = await self.client.put(
            f"{self.base_url}/profiles/{profile_id}",
            json=kwargs,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_profile(self, profile_id: int):
        response = await self.client.delete(
            f"{self.base_url}/profiles/{profile_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
    
    # Corpus methods
    async def create_corpus(self, user_id: int, name: str, description: str = None) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/corpora/",
            json={"user_id": user_id, "name": name, "description": description},
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_corpus(self, corpus_id: int) -> Dict:
        response = await self.client.get(
            f"{self.base_url}/corpora/{corpus_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def list_corpora(self) -> List[Dict]:
        response = await self.client.get(
            f"{self.base_url}/corpora/",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_user_corpora(self, user_id: int) -> List[Dict]:
        corpora = await self.list_corpora()
        return [c for c in corpora if c['user_id'] == user_id]
    
    # Paper methods
    async def get_paper(self, paper_id: int) -> Dict:
        response = await self.client.get(
            f"{self.base_url}/papers/{paper_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def list_papers(self, corpus_id: int = None) -> List[Dict]:
        params = {"corpus_id": corpus_id} if corpus_id else {}
        response = await self.client.get(
            f"{self.base_url}/papers/",
            params=params,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_corpus_papers(self, corpus_id: int) -> List[Dict]:
        return await self.list_papers(corpus_id)
    
    # Recommendation methods
    async def get_recommendation_run(self, run_id: int) -> Dict:
        response = await self.client.get(
            f"{self.base_url}/recommendation-runs/{run_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def list_recommendation_runs(self) -> List[Dict]:
        response = await self.client.get(
            f"{self.base_url}/recommendation-runs/",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_user_recommendation_runs(self, user_id: int) -> List[Dict]:
        runs = await self.list_recommendation_runs()
        return [r for r in runs if r['user_id'] == user_id]
    
    async def get_recommendations_with_papers(self, run_id: int, limit: int = 50) -> List[Dict]:
        response = await self.client.get(
            f"{self.base_url}/recommendations/run/{run_id}/with-papers",
            params={"limit": limit},
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_user_recommendations(self, user_id: int, limit: int = 100) -> List[Dict]:
        runs = await self.get_user_recommendation_runs(user_id)
        if not runs:
            return []
        
        all_recommendations = []
        for run in runs[:5]:  # Get recommendations from last 5 runs
            try:
                recs = await self.get_recommendations_with_papers(run['id'], limit)
                all_recommendations.extend(recs)
            except:
                continue
        
        # Sort by score and return top N
        all_recommendations.sort(key=lambda x: x.get('score', 0), reverse=True)
        return all_recommendations[:limit]
    
    async def get_profile_recommendations(self, profile_id: int, limit: int = 5000) -> List[Dict]:
        """Get recommendations for a specific profile"""
        response = await self.client.get(
            f"{self.base_url}/recommendations/profile/{profile_id}",
            params={"limit": limit},
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # Summary methods
    async def get_paper_summaries(self, paper_id: int) -> List[Dict]:
        response = await self.client.get(
            f"{self.base_url}/summaries/paper/{paper_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # Upload methods
    async def upload_paper_bytes(self, user_id: int, profile_id: int,
                                filename: str, file_bytes: bytes) -> Dict:
        files = {"file": (filename, file_bytes, "application/pdf")}
        response = await self.client.post(
            f"{self.base_url}/uploads/paper/{user_id}/{profile_id}",
            files=files,
            headers={"Authorization": f"Bearer {self.token}"} if self.token else {}
        )
        response.raise_for_status()
        return response.json()
    
    async def list_uploaded_papers(self, user_id: int, profile_id: int) -> Dict:
        response = await self.client.get(
            f"{self.base_url}/uploads/papers/{user_id}/{profile_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_uploaded_paper(self, user_id: int, profile_id: int, filename: str) -> Dict:
        response = await self.client.delete(
            f"{self.base_url}/uploads/paper/{user_id}/{profile_id}/{filename}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def trigger_processing(self, user_id: int, profile_id: int) -> Dict:
        response = await self.client.post(
            f"{self.base_url}/uploads/process/{user_id}/{profile_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_processing_progress(self, user_id: int, profile_id: int) -> Dict:
        response = await self.client.get(
            f"{self.base_url}/uploads/progress/{user_id}/{profile_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()