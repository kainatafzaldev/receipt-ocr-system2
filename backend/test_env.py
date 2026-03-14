from dotenv import load_dotenv
import os

env_path = os.path.join(os.path.dirname(__file__), '.env')
print(f"Looking for .env at: {env_path}")
print(f"File exists: {os.path.exists(env_path)}")

load_dotenv(env_path)

api_key = os.getenv('NOVITA_API_KEY')
print(f"API Key found: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"API Key starts with: {api_key[:10]}...")
    
# Also check Odoo variables
odo_url = os.getenv('ODOO_URL')
print(f"Odoo URL found: {'Yes' if odo_url else 'No'}")