import xmlrpc.client

url = "https://kainatcecos4.odoo.com"
db = "kainatcecos4"
username = "Kainatececos17@gmail.com"
api_key = "daaf6167ae7035371ff174e6c8c97ea3582a8d44" # Use your real key

print(f"--- Attempting XML-RPC Handshake ---")
try:
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, api_key, {})
    
    if uid:
        print(f"✅ SUCCESS! Your UID is: {uid}")
        print("Now you can use this key in your main project.")
    else:
        print("❌ AUTHENTICATION FAILED.")
        print("Likely causes: 1. Wrong DB name. 2. API Key is revoked. 3. User email case-mismatch.")
        
except Exception as e:
    print(f"❌ ERROR: {e}")