# test_jsonrpc.py
import requests
import json

url = 'https://epic-marketing1.odoo.com'
db = 'epic-marketing1'
username = 'haris.herry@gmail.com'
password = 'Honda125'

print("🔍 Testing JSON-RPC Connection to Odoo...")
print(f"URL: {url}")
print(f"Database: {db}")
print(f"Username: {username}")
print("-" * 50)

# Test JSON-RPC authentication
auth_url = f'{url}/web/session/authenticate'
payload = {
    'jsonrpc': '2.0',
    'method': 'call',
    'params': {
        'db': db,
        'login': username,
        'password': password
    },
    'id': 1
}

try:
    print("📡 Sending authentication request...")
    response = requests.post(auth_url, json=payload, timeout=10)
    print(f"Response Status: {response.status_code}")
    
    result = response.json()
    print(f"Full Response: {json.dumps(result, indent=2)}")
    
    if 'result' in result and result['result'].get('uid'):
        uid = result['result']['uid']
        print(f"\n✅ SUCCESS! JSON-RPC Works!")
        print(f"✅ User ID: {uid}")
        print(f"✅ Username: {result['result'].get('name', 'N/A')}")
        print(f"✅ Company: {result['result'].get('company', 'N/A')}")
    else:
        print("\n❌ JSON-RPC Authentication Failed")
        if 'error' in result:
            print(f"Error: {result['error']}")
            
except requests.exceptions.ConnectionError:
    print("❌ Connection Error - Cannot reach Odoo server")
except requests.exceptions.Timeout:
    print("❌ Timeout Error - Server took too long to respond")
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")