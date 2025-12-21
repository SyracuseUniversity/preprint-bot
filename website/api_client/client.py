import httpx
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

class WebAPIClient:
    """Client for communicating with the FastAPI backend"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
        self.timeout = 30.0
    
    async def _request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request to backend API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}{endpoint}"
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
    
    # ==================== AUTH ENDPOINTS ====================
    
    async def login(self, email: str, password: str) -> Dict:
        """Login user and return user info"""
        return await self._request("POST", "/auth/login", json={
            "email": email,
            "password": password
        })
    
    async def register(self, email: str, password: str, name: str = None) -> Dict:
        """Register a new user"""
        return await self._request("POST", "/auth/register", json={
            "email": email,
            "password": password,
            "name": name
        })
    
    async def request_password_reset(self, email: str) -> Dict:
        """Request a password reset token"""
        return await self._request("POST", "/auth/request-reset", json={
            "email": email
        })
    
    async def reset_password(self, token: str, new_password: str) -> Dict:
        """Reset password using token"""
        return await self._request("POST", "/auth/reset-password", json={
            "token": token,
            "new_password": new_password
        })
    
    async def verify_session(self, user_id: int) -> Dict:
        """Verify user session"""
        return await self._request("GET", f"/auth/verify/{user_id}")
    
    # ==================== USER ENDPOINTS ====================
    
    async def get_user(self, user_id: int) -> Dict:
        """Get user by ID"""
        return await self._request("GET", f"/users/{user_id}")
    
    async def update_user(self, user_id: int, email: str = None, name: str = None) -> Dict:
        """Update user information"""
        data = {}
        if email:
            data['email'] = email
        if name:
            data['name'] = name
        return await self._request("PATCH", f"/users/{user_id}", json=data)
    
    async def list_users(self) -> List[Dict]:
        """List all users"""
        return await self._request("GET", "/users/")
    
    # ==================== PROFILE ENDPOINTS ====================
    
    async def create_profile(
        self, 
        user_id: int, 
        name: str, 
        keywords: List[str],
        frequency: str = "weekly", 
        threshold: str = "medium",
        top_x: int = 10
    ) -> Dict:
        """Create a new profile"""
        return await self._request("POST", "/profiles/", json={
            "user_id": user_id,
            "name": name,
            "keywords": keywords,
            "email_notify": True,
            "frequency": frequency,
            "threshold": threshold,
            "top_x": top_x
        })
    
    async def get_profile(self, profile_id: int) -> Dict:
        """Get profile by ID"""
        return await self._request("GET", f"/profiles/{profile_id}")
    
    async def list_profiles(self) -> List[Dict]:
        """List all profiles"""
        return await self._request("GET", "/profiles/")
    
    async def get_user_profiles(self, user_id: int) -> List[Dict]:
        """Get all profiles for a user"""
        all_profiles = await self.list_profiles()
        return [p for p in all_profiles if p['user_id'] == user_id]
    
    async def update_profile(
        self,
        profile_id: int,
        name: str = None,
        keywords: List[str] = None,
        frequency: str = None,
        threshold: str = None,
        top_x: int = None
    ) -> Dict:
        """Update a profile"""
        data = {}
        if name is not None:
            data['name'] = name
        if keywords is not None:
            data['keywords'] = keywords
        if frequency is not None:
            data['frequency'] = frequency
        if threshold is not None:
            data['threshold'] = threshold
        if top_x is not None:
            data['top_x'] = top_x
        
        return await self._request("PUT", f"/profiles/{profile_id}", json=data)
    
    async def delete_profile(self, profile_id: int):
        """Delete a profile"""
        return await self._request("DELETE", f"/profiles/{profile_id}")
    
    # ==================== CORPUS ENDPOINTS ====================
    
    async def create_corpus(self, user_id: int, name: str, description: str = None) -> Dict:
        """Create a new corpus"""
        return await self._request("POST", "/corpora/", json={
            "user_id": user_id,
            "name": name,
            "description": description
        })
    
    async def get_corpus(self, corpus_id: int) -> Dict:
        """Get corpus by ID"""
        return await self._request("GET", f"/corpora/{corpus_id}")
    
    async def list_corpora(self) -> List[Dict]:
        """List all corpora"""
        return await self._request("GET", "/corpora/")
    
    async def get_user_corpora(self, user_id: int) -> List[Dict]:
        """Get all corpora for a user"""
        all_corpora = await self.list_corpora()
        return [c for c in all_corpora if c['user_id'] == user_id]
    
    # ==================== PAPER ENDPOINTS ====================
    
    async def get_paper(self, paper_id: int) -> Dict:
        """Get paper by ID"""
        return await self._request("GET", f"/papers/{paper_id}")
    
    async def list_papers(self, corpus_id: int = None) -> List[Dict]:
        """List papers, optionally filtered by corpus"""
        params = {}
        if corpus_id:
            params['corpus_id'] = corpus_id
        return await self._request("GET", "/papers/", params=params)
    
    async def get_corpus_papers(self, corpus_id: int) -> List[Dict]:
        """Get all papers in a corpus"""
        return await self.list_papers(corpus_id=corpus_id)
    
    # ==================== RECOMMENDATION ENDPOINTS ====================
    
    async def get_recommendation_run(self, run_id: int) -> Dict:
        """Get recommendation run details"""
        return await self._request("GET", f"/recommendation-runs/{run_id}")
    
    async def list_recommendation_runs(self) -> List[Dict]:
        """List all recommendation runs"""
        return await self._request("GET", "/recommendation-runs/")
    
    async def get_user_recommendation_runs(self, user_id: int) -> List[Dict]:
        """Get all recommendation runs for a user"""
        all_runs = await self.list_recommendation_runs()
        return [r for r in all_runs if r['user_id'] == user_id]
    
    async def get_recommendations_with_papers(self, run_id: int, limit: int = 50) -> List[Dict]:
        """Get recommendations with full paper details"""
        return await self._request(
            "GET", 
            f"/recommendations/run/{run_id}/with-papers",
            params={"limit": limit}
        )
    
    async def get_user_recommendations(self, user_id: int, limit: int = 100) -> List[Dict]:
        """Get all recommendations for a user across all runs"""
        runs = await self.get_user_recommendation_runs(user_id)
        
        all_recs = []
        for run in runs[:10]:  # Get latest 10 runs
            try:
                recs = await self.get_recommendations_with_papers(run['id'], limit=limit)
                # Add run info to each recommendation
                for rec in recs:
                    rec['run_id'] = run['id']
                    rec['run_created_at'] = run['created_at']
                all_recs.extend(recs)
            except Exception as e:
                print(f"Error fetching recommendations for run {run['id']}: {e}")
                continue
        
        # Sort by score descending
        all_recs.sort(key=lambda x: x.get('score', 0), reverse=True)
        return all_recs[:limit]
    
    # ==================== SUMMARY ENDPOINTS ====================
    
    async def get_paper_summaries(self, paper_id: int) -> List[Dict]:
        """Get all summaries for a paper"""
        return await self._request("GET", f"/summaries/paper/{paper_id}")