import os
import requests
import logging
from dotenv import load_dotenv

# Load variables
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def odoo_doctor():
    print("--- 🩺 ODOO CONNECTION DOCTOR ---")
    
    # 1. Check if files exist
    if not os.path.exists('odoo_integration.py'):
        print("❌ odoo_integration.py not found!")
        return

    # 2. Validate .env keys
    url = os.getenv('ODOO_URL')
    db = os.getenv('ODOO_DB')
    user = os.getenv('ODOO_USERNAME')
    pwd = os.getenv('ODOO_PASSWORD')

    print(f"Checking URL: {url}")
    print(f"Checking DB: {db}")
    print(f"Checking User: {user}")
    print(f"Checking Password (Masked): {'*' * len(pwd) if pwd else 'MISSING'}")

    # 3. Perform a direct Authentication test (ignoring your full app)
    print("\n--- 📡 TESTING AUTHENTICATION ---")
    auth_url = f"{url.rstrip('/')}/web/session/authenticate"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"db": db, "login": user, "password": pwd},
        "id": 1
    }
    
    try:
        response = requests.post(auth_url, json=payload, timeout=10)
        data = response.json()
        
        if 'result' in data and data['result'].get('uid'):
            print(f"✅ SUCCESS! Connected to Odoo.")
            print(f"   UID: {data['result']['uid']}")
            print(f"   Company ID: {data['result'].get('company_id')}")
        else:
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            print(f"❌ AUTH FAILED: {error_msg}")
            if "Access Denied" in str(error_msg):
                print("   👉 TIP: Your API Key or Password is incorrect or lacks permissions.")
            if "Database not found" in str(error_msg):
                print("   👉 TIP: Your ODOO_DB name is incorrect.")
    except Exception as e:
        print(f"❌ NETWORK ERROR: {e}")

if __name__ == "__main__":
    odoo_doctor()