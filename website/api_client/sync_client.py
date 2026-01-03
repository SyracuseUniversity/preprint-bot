import asyncio
from typing import Optional, List, Dict
from .client import WebAPIClient

class SyncWebAPIClient:
    """Synchronous wrapper around WebAPIClient for use in Streamlit"""
    
    def __init__(self, base_url: str = None):
        self._client = WebAPIClient(base_url)
        self.base_url = self._client.base_url
    
    def _run_async(self, coro):
        """Run async coroutine synchronously"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro)
    
    # Auth
    def login(self, email: str, password: str) -> Dict:
        return self._run_async(self._client.login(email, password))
    
    def register(self, email: str, password: str, name: str = None) -> Dict:
        return self._run_async(self._client.register(email, password, name))
    
    def request_password_reset(self, email: str) -> Dict:
        return self._run_async(self._client.request_password_reset(email))
    
    def reset_password(self, token: str, new_password: str) -> Dict:
        return self._run_async(self._client.reset_password(token, new_password))
    
    def verify_session(self, user_id: int) -> Dict:
        return self._run_async(self._client.verify_session(user_id))
    
    # Users
    def get_user(self, user_id: int) -> Dict:
        return self._run_async(self._client.get_user(user_id))
    
    def update_user(self, user_id: int, email: str = None, name: str = None) -> Dict:
        return self._run_async(self._client.update_user(user_id, email, name))
    
    def list_users(self) -> List[Dict]:
        return self._run_async(self._client.list_users())
    
    # Profiles
    def create_profile(self, user_id: int, name: str, keywords: list, 
                       categories: list = None, frequency: str = "weekly",
                       threshold: str = "medium"):
        """Create a new profile"""
        return self._run_async(
            self._client.create_profile(
                user_id=user_id,
                name=name,
                keywords=keywords,
                categories=categories or [],
                frequency=frequency,
                threshold=threshold
            )
        )
    
    def get_profile(self, profile_id: int) -> Dict:
        return self._run_async(self._client.get_profile(profile_id))
    
    def list_profiles(self) -> List[Dict]:
        return self._run_async(self._client.list_profiles())
    
    def get_user_profiles(self, user_id: int) -> List[Dict]:
        return self._run_async(self._client.get_user_profiles(user_id))
    
    def update_profile(self, profile_id: int, **kwargs) -> Dict:
        return self._run_async(self._client.update_profile(profile_id, **kwargs))
    
    def delete_profile(self, profile_id: int):
        return self._run_async(self._client.delete_profile(profile_id))
    
    # Corpora
    def create_corpus(self, user_id: int, name: str, description: str = None) -> Dict:
        return self._run_async(self._client.create_corpus(user_id, name, description))
    
    def get_corpus(self, corpus_id: int) -> Dict:
        return self._run_async(self._client.get_corpus(corpus_id))
    
    def list_corpora(self) -> List[Dict]:
        return self._run_async(self._client.list_corpora())
    
    def get_user_corpora(self, user_id: int) -> List[Dict]:
        return self._run_async(self._client.get_user_corpora(user_id))
    
    # Papers
    def get_paper(self, paper_id: int) -> Dict:
        return self._run_async(self._client.get_paper(paper_id))
    
    def list_papers(self, corpus_id: int = None) -> List[Dict]:
        return self._run_async(self._client.list_papers(corpus_id))
    
    def get_corpus_papers(self, corpus_id: int) -> List[Dict]:
        return self._run_async(self._client.get_corpus_papers(corpus_id))
    
    # Recommendations
    def get_recommendation_run(self, run_id: int) -> Dict:
        return self._run_async(self._client.get_recommendation_run(run_id))
    
    def list_recommendation_runs(self) -> List[Dict]:
        return self._run_async(self._client.list_recommendation_runs())
    
    def get_user_recommendation_runs(self, user_id: int) -> List[Dict]:
        return self._run_async(self._client.get_user_recommendation_runs(user_id))
    
    def get_recommendations_with_papers(self, run_id: int, limit: int = 50) -> List[Dict]:
        return self._run_async(self._client.get_recommendations_with_papers(run_id, limit))
    
    def get_user_recommendations(self, user_id: int, limit: int = 100) -> List[Dict]:
        return self._run_async(self._client.get_user_recommendations(user_id, limit))

    def get_profile_recommendations(self, profile_id: int, limit: int = 100) -> List[Dict]:
        return self._run_async(self._client.get_profile_recommendations(profile_id, limit))
    
    # Summaries
    def get_paper_summaries(self, paper_id: int) -> List[Dict]:
        return self._run_async(self._client.get_paper_summaries(paper_id))

    # Uploads - all use async wrapper
    def upload_paper_bytes(self, user_id: int, profile_id: int, filename: str, file_bytes: bytes):
        """Upload paper from bytes"""
        return self._run_async(
            self._client.upload_paper_bytes(user_id, profile_id, filename, file_bytes)
        )
    
    def list_uploaded_papers(self, user_id: int, profile_id: int):
        """List uploaded papers for a profile"""
        return self._run_async(
            self._client.list_uploaded_papers(user_id, profile_id)
        )
    
    def delete_uploaded_paper(self, user_id: int, profile_id: int, filename: str):
        """Delete an uploaded paper"""
        return self._run_async(
            self._client.delete_uploaded_paper(user_id, profile_id, filename)
        )
    
    def trigger_processing(self, user_id: int, profile_id: int):
        """Trigger processing of uploaded papers"""
        return self._run_async(
            self._client.trigger_processing(user_id, profile_id)
        )
    
    def get_processing_progress(self, user_id: int, profile_id: int):
        """Get processing progress"""
        return self._run_async(
            self._client.get_processing_progress(user_id, profile_id)
        )