import os
import requests

# Load the key from environment variables (Never hardcode it!)
API_KEY = os.getenv("MY_API_KEY")
BASE_URL = "https://api.example.com"  # REPLACE with your actual API base URL

def run_tests():
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    print("--- Starting API Key Tests ---")

    # 1. Happy Path Test
    response = requests.get(f"{BASE_URL}/data", headers=headers)
    print(f"1. Connection Test: {'PASSED' if response.status_code == 200 else 'FAILED'} (Status: {response.status_code})")

    # 2. Unauthorized Test
    bad_headers = {"Authorization": "Bearer WRONG_KEY"}
    response = requests.get(f"{BASE_URL}/data", headers=bad_headers)
    print(f"2. Unauthorized Test: {'PASSED' if response.status_code in [401, 403] else 'FAILED'} (Status: {response.status_code})")

    # 3. Scope/Permission Test (Attempting a protected action)
    response = requests.post(f"{BASE_URL}/admin", headers=headers)
    print(f"3. Permission Test: {'PASSED' if response.status_code == 403 else 'FAILED'} (Status: {response.status_code})")

    # 4. Rate Limiting Check
    # We check the headers to see if rate limits are communicated
    print(f"4. Rate Limit Info: {response.headers.get('X-RateLimit-Limit', 'Not Provided')}")

    # 5. Environment Variable Security Check
    if API_KEY and len(API_KEY) > 10:
        print("5. Security Check: PASSED (Key loaded from environment variable)")
    else:
        print("5. Security Check: FAILED (Key not found or too short)")

if __name__ == "__main__":
    run_tests()