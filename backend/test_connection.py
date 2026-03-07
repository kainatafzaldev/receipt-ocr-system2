import xmlrpc.client
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv('ODOO_URL')
db = os.getenv('ODOO_DB')
username = os.getenv('ODOO_USERNAME')
password = os.getenv('ODOO_PASSWORD') # Use the API Key here

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
try:
    uid = common.authenticate(db, username, password, {})
    if uid:
        print(f"✅ Success! UID: {uid}")
    else:
        print("❌ Authentication failed (UID is False). Check password/API Key.")
except Exception as e:
    print(f"❌ Connection error: {e}")