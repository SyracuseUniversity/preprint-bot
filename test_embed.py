from src.preprint_bot.api_client import APIClient
import asyncio

async def check():
    client = APIClient()
    try:
        papers = await client.get_papers_by_corpus(1)
        print(f"Papers in corpus 1: {len(papers)}")
        
        all_papers = await client.client.get("http://127.0.0.1:8000/papers/")
        print(f"Total papers in DB: {len(all_papers.json())}")
        
        corpora = await client.client.get("http://127.0.0.1:8000/corpora/")
        print(f"Corpora: {corpora.json()}")
    finally:
        await client.close()

asyncio.run(check())