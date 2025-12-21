"""
Enhanced arXiv PDF downloader with better rate limiting and monitoring.
"""

import os
import time
import random
import requests
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque
from .config import DATA_DIR

HEADERS = {
    "User-Agent": "arxiv-pdf-fetcher/1.0 (contact: ospo@syr.edu)"
}

class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on server responses.
    Tracks request history to enforce hourly limits.
    """
    
    def __init__(self, min_delay=5, max_delay=15, requests_per_hour=100):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.requests_per_hour = requests_per_hour
        self.last_request_time = 0
        
        # Track request timestamps for hourly limit
        self.request_history = deque(maxlen=requests_per_hour)
        
        # Adaptive delay based on recent rate limits
        self.current_delay = min_delay
        self.consecutive_successes = 0
        self.consecutive_rate_limits = 0
    
    def wait(self):
        """Wait with adaptive delay before allowing next request."""
        # Check hourly limit
        self._enforce_hourly_limit()
        
        # Calculate delay with jitter
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(self.current_delay, self.current_delay + 5)
        
        if elapsed < delay:
            sleep_time = delay - elapsed
            print(f"Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_history.append(time.time())
    
    def _enforce_hourly_limit(self):
        """Ensure we don't exceed requests per hour."""
        if len(self.request_history) >= self.requests_per_hour:
            oldest_request = self.request_history[0]
            time_since_oldest = time.time() - oldest_request
            
            if time_since_oldest < 3600:  # Less than 1 hour
                sleep_time = 3600 - time_since_oldest + random.uniform(1, 5)
                print(f"\nHourly limit reached ({self.requests_per_hour} requests/hour)")
                print(f"   Sleeping for {sleep_time/60:.1f} minutes...")
                time.sleep(sleep_time)
    
    def record_success(self):
        """Adjust rate limit after successful request."""
        self.consecutive_successes += 1
        self.consecutive_rate_limits = 0
        
        # Gradually decrease delay after consistent successes
        if self.consecutive_successes >= 10:
            self.current_delay = max(
                self.min_delay,
                self.current_delay * 0.9
            )
            self.consecutive_successes = 0
            print(f"  ✓ Reduced delay to {self.current_delay:.1f}s")
    
    def record_rate_limit(self):
        """Adjust rate limit after being rate limited."""
        self.consecutive_rate_limits += 1
        self.consecutive_successes = 0
        
        # Increase delay after rate limiting
        self.current_delay = min(
            self.max_delay,
            self.current_delay * 1.5
        )
        print(f"Increased delay to {self.current_delay:.1f}s")
    
    def get_stats(self):
        """Get rate limiter statistics."""
        if not self.request_history:
            return {
                "total_requests": 0,
                "requests_last_hour": 0,
                "current_delay": self.current_delay
            }
        
        now = time.time()
        recent = [t for t in self.request_history if now - t < 3600]
        
        return {
            "total_requests": len(self.request_history),
            "requests_last_hour": len(recent),
            "current_delay": self.current_delay,
            "oldest_request": datetime.fromtimestamp(self.request_history[0]).strftime("%H:%M:%S") if self.request_history else "N/A"
        }


def download_arxiv_pdfs(
    paper_metadata, 
    output_folder="arxiv_pipeline_data/arxiv_pdfs", 
    min_delay=5,  # Increased from 3
    max_delay=15,  # Increased from 10
    requests_per_hour=100,  # New: enforce hourly limit
    max_retries=3,
    initial_backoff=10  # Increased from 5
):
    """
    Downloads PDFs of arXiv papers with robust rate limiting.
    
    Args:
        paper_metadata: List of paper dictionaries with 'arxiv_url' keys
        output_folder: Directory to save PDFs
        min_delay: Minimum delay between requests (seconds)
        max_delay: Maximum delay between requests (seconds)
        requests_per_hour: Maximum requests per hour (arXiv recommends ~100)
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff delay for exponential backoff (seconds)
    
    Returns:
        dict: Statistics about the download process
    """
    os.makedirs(output_folder, exist_ok=True)
    
    rate_limiter = AdaptiveRateLimiter(min_delay, max_delay, requests_per_hour)
    stats = {
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "rate_limited": 0,
        "start_time": time.time()
    }
    
    print(f"\n{'='*60}")
    print(f"Starting arXiv PDF download")
    print(f"Papers to process: {len(paper_metadata)}")
    print(f"Rate limit: {requests_per_hour} requests/hour, {min_delay}-{max_delay}s delay")
    print(f"{'='*60}\n")

    for idx, paper in enumerate(paper_metadata):
        arxiv_id = paper["arxiv_url"].split("/")[-1]
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        pdf_path = os.path.join(output_folder, f"{arxiv_id}.pdf")

        # Skip if already downloaded
        if os.path.exists(pdf_path):
            print(f"[{idx + 1}/{len(paper_metadata)}] ⊘ Skipping (exists): {arxiv_id}")
            stats["skipped"] += 1
            continue

        # Attempt download with exponential backoff
        retry_delay = initial_backoff
        success = False
        
        for attempt in range(max_retries):
            # Apply rate limiting before each attempt
            rate_limiter.wait()
            
            try:
                print(f"[{idx + 1}/{len(paper_metadata)}] Downloading: {arxiv_id} (attempt {attempt + 1}/{max_retries})")
                r = requests.get(pdf_url, headers=HEADERS, timeout=30)

                # Handle rate limiting responses
                if r.status_code in [403, 429, 503]:
                    stats["rate_limited"] += 1
                    rate_limiter.record_rate_limit()
                    print(f"Rate limited (HTTP {r.status_code}). Backing off {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue

                # Check for successful response
                if r.status_code == 200:
                    content_type = r.headers.get("Content-Type", "").lower()
                    
                    if "application/pdf" in content_type:
                        with open(pdf_path, "wb") as f:
                            f.write(r.content)
                        print(f"  ✓ Saved: {arxiv_id} ({len(r.content)/1024:.1f} KB)")
                        stats["downloaded"] += 1
                        rate_limiter.record_success()
                        success = True
                        break
                    else:
                        # Likely CAPTCHA or block page
                        print(f" Got {content_type} instead of PDF")
                        if attempt < max_retries - 1:
                            print(f"     Retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            html_path = f"{pdf_path}.html"
                            with open(html_path, "w", encoding="utf-8") as f:
                                f.write(r.text)
                            print(f"  ✗ Saved HTML to: {html_path}")
                else:
                    print(f" HTTP {r.status_code} for {arxiv_id}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        
            except requests.exceptions.Timeout:
                print(f"Timeout for {arxiv_id}")
                if attempt < max_retries - 1:
                    print(f"     Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    
            except requests.exceptions.RequestException as e:
                print(f"Request error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    
            except Exception as e:
                print(f"Unexpected error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
        
        if not success:
            stats["failed"] += 1
            print(f"  ✗ Failed after {max_retries} attempts")
        
        # Show progress every 10 papers
        if (idx + 1) % 10 == 0:
            elapsed = time.time() - stats["start_time"]
            rate_stats = rate_limiter.get_stats()
            print(f"\n--- Progress Report ---")
            print(f"  Processed: {idx + 1}/{len(paper_metadata)}")
            print(f"  Downloaded: {stats['downloaded']}, Failed: {stats['failed']}, Skipped: {stats['skipped']}")
            print(f"  Requests this hour: {rate_stats['requests_last_hour']}/{requests_per_hour}")
            print(f"  Current delay: {rate_stats['current_delay']:.1f}s")
            print(f"  Elapsed time: {elapsed/60:.1f} min\n")
    
    # Final summary
    elapsed = time.time() - stats["start_time"]
    print(f"\n{'='*60}")
    print("Download Complete!")
    print(f"{'='*60}")
    print(f"  ✓ Downloaded: {stats['downloaded']}")
    print(f"  ⊘ Skipped: {stats['skipped']}")
    print(f"  ✗ Failed: {stats['failed']}")
    print(f"  ⚠  Rate limited: {stats['rate_limited']}")
    print(f"  ⏱  Total time: {elapsed/60:.1f} minutes")
    print(f"  📊 Average: {elapsed/len(paper_metadata):.1f}s per paper")
    print(f"{'='*60}\n")
    
    return stats