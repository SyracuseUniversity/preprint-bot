from api_client.sync_client import SyncWebAPIClient

def test_api_client():
    client = SyncWebAPIClient()
    
    print("Testing API Client...")
    print("-" * 50)
    
    # Test 1: Register
    print("\n1. Testing Registration...")
    try:
        user = client.register(
            email="apitest@example.com",
            password="testpass123",
            name="API Test User"
        )
        print(f" Registration successful: {user}")
        user_id = user['user_id']
    except Exception as e:
        print(f" Registration failed: {e}")
        return
    
    # Test 2: Login
    print("\n2. Testing Login...")
    try:
        login_result = client.login(
            email="apitest@example.com",
            password="testpass123"
        )
        print(f" Login successful: {login_result}")
    except Exception as e:
        print(f" Login failed: {e}")
        return
    
    # Test 3: Get User
    print("\n3. Testing Get User...")
    try:
        user_data = client.get_user(user_id)
        print(f" Get user successful: {user_data}")
    except Exception as e:
        print(f" Get user failed: {e}")
    
    # Test 4: Create Profile
    print("\n4. Testing Create Profile...")
    try:
        profile = client.create_profile(
            user_id=user_id,
            name="Test Profile",
            keywords=["machine learning", "neural networks"],
            frequency="weekly",
            threshold="medium"
        )
        print(f" Profile created: {profile}")
    except Exception as e:
        print(f" Profile creation failed: {e}")
    
    # Test 5: List Profiles
    print("\n5. Testing List Profiles...")
    try:
        profiles = client.get_user_profiles(user_id)
        print(f" Found {len(profiles)} profile(s)")
        for p in profiles:
            print(f"  - {p['name']}: {p['keywords']}")
    except Exception as e:
        print(f" List profiles failed: {e}")
    
    print("\n" + "-" * 50)
    print("API Client test complete!")

if __name__ == "__main__":
    test_api_client()