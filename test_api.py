#!/usr/bin/env python3
"""
Test script to verify API and database integration
Run this after setting up the database and starting the API server
"""

import asyncio
import httpx
from datetime import datetime
import random

API_BASE = "http://localhost:8000"


async def test_api():
    """Test all core API endpoints"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🧪 Testing Preprint Bot API\n")
        
        # Generate unique identifiers for this test run
        timestamp = datetime.now().timestamp()
        random_suffix = random.randint(1000, 9999)
        
        # 1. Health Check
        print("1. Testing health endpoint...")
        response = await client.get(f"{API_BASE}/health")
        print(f"   Status: {response.json()}")
        assert response.status_code == 200
        print("   ✓ Health check passed\n")
        
        # 2. Create User
        print("2. Testing user creation...")
        user_data = {
            "email": f"test_{timestamp}@example.com",
            "name": "Test User"
        }
        response = await client.post(f"{API_BASE}/users/", json=user_data)
        if response.status_code != 200:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            raise Exception("User creation failed")
        user = response.json()
        print(f"   Created user: {user['email']} (ID: {user['id']})")
        user_id = user['id']
        print("   ✓ User creation passed\n")
        
        # 3. Create Corpus
        print("3. Testing corpus creation...")
        corpus_data = {
            "user_id": user_id,
            "name": f"test_corpus_{timestamp}",
            "description": "Test corpus for API validation"
        }
        response = await client.post(f"{API_BASE}/corpora/", json=corpus_data)
        if response.status_code != 201:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            raise Exception("Corpus creation failed")
        corpus = response.json()
        print(f"   Created corpus: {corpus['name']} (ID: {corpus['id']})")
        corpus_id = corpus['id']
        print("   ✓ Corpus creation passed\n")
        
        # 4. Create Paper
        print("4. Testing paper creation...")
        paper_data = {
            "corpus_id": corpus_id,
            "arxiv_id": f"test.{int(timestamp)}.{random_suffix}",  # Unique arxiv_id
            "title": "Test Paper: A Novel Approach to Testing",
            "abstract": "This is a test paper abstract for API validation purposes.",
            "metadata": {"authors": ["Test Author"], "published": "2023-01-01"},
            "file_path": "/path/to/test.pdf",
            "source": "arxiv"
        }
        response = await client.post(f"{API_BASE}/papers/", json=paper_data)
        if response.status_code != 201:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            raise Exception("Paper creation failed")
        paper = response.json()
        print(f"   Created paper: {paper['title'][:50]}... (ID: {paper['id']})")
        paper_id = paper['id']
        print("   ✓ Paper creation passed\n")
        
        # 5. Create Section
        print("5. Testing section creation...")
        section_data = {
            "paper_id": paper_id,
            "header": "Introduction",
            "text": "This is the introduction section of our test paper."
        }
        response = await client.post(f"{API_BASE}/sections/", json=section_data)
        if response.status_code != 201:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            raise Exception("Section creation failed")
        section = response.json()
        print(f"   Created section: {section['header']} (ID: {section['id']})")
        section_id = section['id']
        print("   ✓ Section creation passed\n")
        
        # 6. Create Embedding
        print("6. Testing embedding creation...")
        # Create a dummy 384-dimensional embedding (matching all-MiniLM-L6-v2)
        dummy_embedding = [0.1] * 384
        embedding_data = {
            "paper_id": paper_id,
            "section_id": None,
            "embedding": dummy_embedding,
            "type": "abstract",
            "model_name": "all-MiniLM-L6-v2"
        }
        response = await client.post(f"{API_BASE}/embeddings/", json=embedding_data)
        if response.status_code != 201:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            raise Exception("Embedding creation failed")
        embedding = response.json()
        print(f"   Created embedding (ID: {embedding['id']})")
        print("   ✓ Embedding creation passed\n")
        
        # 7. List Papers
        print("7. Testing paper listing...")
        response = await client.get(f"{API_BASE}/papers/?corpus_id={corpus_id}")
        if response.status_code != 200:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            raise Exception("Paper listing failed")
        papers = response.json()
        print(f"   Found {len(papers)} paper(s) in corpus")
        assert len(papers) >= 1
        print("   ✓ Paper listing passed\n")
        
        # 8. Get Stats
        print("8. Testing stats endpoint...")
        response = await client.get(f"{API_BASE}/stats")
        if response.status_code != 200:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            raise Exception("Stats endpoint failed")
        stats = response.json()
        print(f"   Database stats:")
        print(f"     Users: {stats['users']}")
        print(f"     Papers: {stats['papers']}")
        print(f"     Embeddings: {stats['embeddings']}")
        print(f"     Recommendations: {stats['recommendations']}")
        print("   ✓ Stats endpoint passed\n")
        
        # 9. Create Recommendation Run
        print("9. Testing recommendation run creation...")
        run_data = {
            "profile_id": None,
            "user_id": user_id,
            "user_corpus_id": corpus_id,
            "ref_corpus_id": corpus_id,
            "threshold": "medium",
            "method": "cosine"
        }
        response = await client.post(f"{API_BASE}/recommendation-runs/", json=run_data)
        if response.status_code != 201:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            raise Exception("Recommendation run creation failed")
        run = response.json()
        print(f"   Created recommendation run (ID: {run['id']})")
        run_id = run['id']
        print("   ✓ Recommendation run creation passed\n")
        
        # 10. Create Recommendation
        print("10. Testing recommendation creation...")
        rec_data = {
            "run_id": run_id,
            "paper_id": paper_id,
            "score": 0.85,
            "rank": 1,
            "summary": "This paper demonstrates effective API testing."
        }
        response = await client.post(f"{API_BASE}/recommendations/", json=rec_data)
        if response.status_code != 201:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            raise Exception("Recommendation creation failed")
        recommendation = response.json()
        print(f"   Created recommendation (ID: {recommendation['id']}, Score: {recommendation['score']})")
        print("   ✓ Recommendation creation passed\n")
        
        # 11. Get Recommendations
        print("11. Testing recommendation retrieval...")
        response = await client.get(f"{API_BASE}/recommendations/?run_id={run_id}")
        if response.status_code != 200:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            raise Exception("Recommendation retrieval failed")
        recommendations = response.json()
        print(f"   Retrieved {len(recommendations)} recommendation(s)")
        assert len(recommendations) >= 1
        print("   ✓ Recommendation retrieval passed\n")
        
        # 12. Vector Similarity Search
        print("12. Testing vector similarity search...")
        search_data = {
            "embedding": dummy_embedding,
            "corpus_id": corpus_id,
            "limit": 5,
            "threshold": 0.0  # Low threshold to ensure we get results
        }
        response = await client.post(f"{API_BASE}/embeddings/search/similar", json=search_data)
        if response.status_code != 200:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            raise Exception("Vector search failed")
        similar_papers = response.json()
        print(f"   Found {len(similar_papers)} similar paper(s)")
        print("   ✓ Vector search passed\n")
        
        # 13. Get Recommendations with Papers
        print("13. Testing recommendations with full paper details...")
        response = await client.get(f"{API_BASE}/recommendations/run/{run_id}/with-papers?limit=10")
        if response.status_code != 200:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            raise Exception("Recommendations with papers failed")
        recs_with_papers = response.json()
        print(f"   Retrieved {len(recs_with_papers)} recommendation(s) with paper details")
        if len(recs_with_papers) > 0:
            print(f"   Sample: {recs_with_papers[0]['title'][:50]}...")
        print("   ✓ Recommendations with papers passed\n")
        
        print("=" * 60)
        print("🎉 All tests passed successfully!")
        print("=" * 60)
        print("\n✓ Your API is properly configured and working")
        print("✓ Database integration is functioning")
        print("✓ Vector embeddings are stored and searchable")
        print("\nYou can now run the full pipeline:")
        print("  preprint_bot --mode corpus --category cs.LG")
        print("\nOr view the API docs at:")
        print(f"  {API_BASE}/docs")


if __name__ == "__main__":
    try:
        asyncio.run(test_api())
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        print("\nPlease ensure:")
        print("  1. PostgreSQL is running")
        print("  2. Database schema is created (run database_schema.sql)")
        print("  3. pgvector extension is installed")
        print("  4. API server is running: uvicorn main:app --reload")
        print("  5. .env file is configured correctly")
        exit(1)