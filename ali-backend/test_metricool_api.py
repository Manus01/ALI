"""
Quick test script to diagnose Metricool API response structure.
Run with: python test_metricool_api.py
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

METRICOOL_USER_TOKEN = os.getenv("METRICOOL_USER_TOKEN")
METRICOOL_USER_ID = os.getenv("METRICOOL_USER_ID")
BASE_URL = "https://app.metricool.com/api"

print(f"User ID: {METRICOOL_USER_ID}")
print(f"Token exists: {bool(METRICOOL_USER_TOKEN)}")

headers = {
    "X-Mc-Auth": METRICOOL_USER_TOKEN,
    "Content-Type": "application/json"
}
params = {"userId": METRICOOL_USER_ID}

# Test different endpoints
endpoints = [
    "/admin/profiles",
    "/admin/simpleProfiles"
]

for endpoint in endpoints:
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing: {url}")
    print(f"{'='*60}")
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"Status: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list):
                print(f"Response is a list with {len(data)} items")
                if data:
                    first_item = data[0]
                    print(f"First item keys: {list(first_item.keys())}")
                    # Check for social network data
                    if 'socialNetworks' in first_item:
                        print(f"  socialNetworks: {first_item['socialNetworks']}")
                    if 'providers' in first_item:
                        print(f"  providers: {first_item['providers']}")
                    if 'networks' in first_item:
                        print(f"  networks: {first_item['networks']}")
                    # Print all key-value pairs for first item
                    print(f"\nFull first item:")
                    for k, v in first_item.items():
                        print(f"  {k}: {v}")
            elif isinstance(data, dict):
                print(f"Response is a dict with keys: {list(data.keys())}")
                print(data)
        else:
            print(f"Error response: {res.text}")
            
    except Exception as e:
        print(f"Error: {e}")
