#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, 'src/preprint_bot')

from api_client import APIClient

USERS_DATA = [
    {
        "uid": "UID001",
        "email": "udayanfg@gmail.com",
        "name": "Alice Researcher",
        "profiles": [
            {
                "pid": "PID001",
                "name": "Deep Learning Theory",
                "keywords": ["deep learning", "neural networks", "theory", "optimization"],
                "description": "Focus on theoretical foundations of deep learning",
                "arxiv_queries": [
                    "cat:cs.LG AND (ti:deep AND ti:learning AND ti:theory)",
                    "cat:cs.LG AND (abs:neural AND abs:network AND abs:convergence)"
                ]
            },
            {
                "pid": "PID002",
                "name": "Reinforcement Learning",
                "keywords": ["reinforcement learning", "policy gradient", "Q-learning", "exploration"],
                "description": "Research in reinforcement learning algorithms",
                "arxiv_queries": [
                    "cat:cs.LG AND (ti:reinforcement AND ti:learning)",
                    "cat:cs.LG AND (abs:policy AND abs:gradient)"
                ]
            }
        ]
    },
    {
        "uid": "UID002",
        "email": "ggwpfax@gmail.com",
        "name": "Bob Scientist",
        "profiles": [
            {
                "pid": "PID003",
                "name": "Computer Vision",
                "keywords": ["computer vision", "image recognition", "object detection", "segmentation"],
                "description": "Computer vision and visual recognition systems",
                "arxiv_queries": [
                    "cat:cs.CV AND (ti:vision AND ti:transformer)",
                    "cat:cs.CV AND (abs:object AND abs:detection)"
                ]
            },
            {
                "pid": "PID004",
                "name": "Natural Language Processing",
                "keywords": ["NLP", "language models", "transformers", "attention"],
                "description": "Natural language understanding and generation",
                "arxiv_queries": [
                    "cat:cs.CL AND (ti:language AND ti:model)",
                    "cat:cs.CL AND (abs:transformer AND abs:attention)"
                ]
            }
        ]
    },
    {
        "uid": "UID003",
        "email": "udayangaikwad9990@gmail.com",
        "name": "Carol PhD",
        "profiles": [
            {
                "pid": "PID005",
                "name": "Graph Neural Networks",
                "keywords": ["graph neural networks", "GNN", "graph learning", "message passing"],
                "description": "Graph-structured data and neural networks",
                "arxiv_queries": [
                    "cat:cs.LG AND (ti:graph AND ti:neural)",
                    "cat:cs.LG AND (abs:GNN AND abs:message AND abs:passing)"
                ]
            },
            {
                "pid": "PID006",
                "name": "Optimization Methods",
                "keywords": ["optimization", "gradient descent", "Adam", "convergence"],
                "description": "Optimization algorithms for machine learning",
                "arxiv_queries": [
                    "cat:cs.LG AND (ti:optimization)",
                    "cat:cs.LG AND (abs:gradient AND abs:descent AND abs:convergence)"
                ]
            }
        ]
    }
]


async def populate_database():
    client = APIClient(base_url="http://127.0.0.1:8000")
    
    try:
        for user_data in USERS_DATA:
            print(f"\nProcessing {user_data['uid']}: {user_data['name']}")
            
            user = await client.get_or_create_user(
                email=user_data['email'],
                name=user_data['name']
            )
            print(f"  User ID: {user['id']}")
            
            for profile_data in user_data['profiles']:
                print(f"  Creating profile: {profile_data['pid']} - {profile_data['name']}")
                
                profile = await client.create_profile(
                    user_id=user['id'],
                    name=profile_data['pid'],
                    keywords=profile_data['keywords'],
                    email_notify=True,
                    frequency="weekly",
                    threshold="medium",
                    top_x=10
                )
                print(f"    Profile ID: {profile['id']}")
        
        print("\nAll users and profiles created")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(populate_database())