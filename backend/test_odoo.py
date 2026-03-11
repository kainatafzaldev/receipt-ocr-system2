import xmlrpc.client

url = "https://kainatcecos4.odoo.com"
db = "kainatcecos4"
username = "kainatcecos17@gmail.com"
password = "41680a891e21db977c4ecb432b42600faffa4c8"

print("Testing Odoo connection...")
print(f"URL: {url}")
print(f"DB: {db}")
print(f"Username: {username}")

try:
    # Test 1: Check server
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    version = common.version()
    print(f"✅ Server version: {version}")
    
    # Test 2: Try authentication
    uid = common.authenticate(db, username, password, {})
    if uid:
        print(f"✅ Authentication successful! UID: {uid}")
    else:
        print("❌ Authentication failed")
        
        # Try with different username formats
        print("\nTrying alternative formats:")
        
        # Try without domain
        uid = common.authenticate(db, username.split('@')[0], password, {})
        if uid:
            print(f"✅ Success with username: {username.split('@')[0]}")
        
except Exception as e:
    print(f"❌ Error: {e}")