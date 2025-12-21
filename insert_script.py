#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, 'src/preprint_bot')

from api_client import APIClient

# Remove the "uid" field - let the database generate IDs
USERS_DATA = [
    {
        "email": "udayanfg@gmail.com",
        "name": "Alice Researcher",
        "profiles": [
            {
                "name": "1",  # This will be profile ID in directory structure
                "keywords": ["deep learning", "neural networks", "theory", "optimization"],
                "description": "Focus on theoretical foundations of deep learning"
            },
            {
                "name": "2",
                "keywords": ["reinforcement learning", "policy gradient", "Q-learning", "exploration"],
                "description": "Research in reinforcement learning algorithms"
            }
        ]
    },
    {
        "email": "ggwpfax@gmail.com",
        "name": "Bob Scientist",
        "profiles": [
            {
                "name": "3",
                "keywords": ["computer vision", "image recognition", "object detection", "segmentation"],
                "description": "Computer vision and visual recognition systems"
            },
            {
                "name": "4",
                "keywords": ["NLP", "language models", "transformers", "attention"],
                "description": "Natural language understanding and generation"
            }
        ]
    },
    {
        "email": "udayangaikwad9990@gmail.com",
        "name": "Carol PhD",
        "profiles": [
            {
                "name": "5",
                "keywords": ["graph neural networks", "GNN", "graph learning", "message passing"],
                "description": "Graph-structured data and neural networks"
            },
            {
                "name": "6",
                "keywords": ["optimization", "gradient descent", "Adam", "convergence"],
                "description": "Optimization algorithms for machine learning"
            }
        ]
    }
]


async def populate_database():
    client = APIClient(base_url="http://127.0.0.1:8000")
    
    try:
        for user_data in USERS_DATA:
            print(f"\nProcessing user: {user_data['name']}")
            
            user = await client.get_or_create_user(
                email=user_data['email'],
                name=user_data['name']
            )
            print(f"  User ID: {user['id']} ({user['email']})")
            
            for profile_data in user_data['profiles']:
                print(f"  Creating profile: {profile_data['name']}")
                
                profile = await client.create_profile(
                    user_id=user['id'],
                    name=profile_data['name'],  # Use simple numeric names like "1", "2", "3"
                    keywords=profile_data['keywords'],
                    email_notify=True,
                    frequency="weekly",
                    threshold="medium",
                    top_x=10
                )
                print(f"    Profile ID: {profile['id']}")
                print(f"    Directory: pdf_data/user_pdfs/{user['id']}/{profile['id']}/")
        
        print("\n" + "="*60)
        print("All users and profiles created successfully!")
        print("="*60)
        print("\nDirectory structure for PDFs:")
        print("pdf_data/user_pdfs/")
        print("  ├── <user_id>/")
        print("  │   └── <profile_id>/")
        print("  │       └── your_papers.pdf")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(populate_database())