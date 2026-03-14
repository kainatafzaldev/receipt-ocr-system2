"""
FULL PROJECT DIAGNOSTIC TOOL
Run this to check every component of your OCR project
"""

import os
import sys
import importlib
import subprocess
import requests
import socket
from datetime import datetime

print("=" * 70)
print("🔍 COMPLETE PROJECT DIAGNOSTIC")
print("=" * 70)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Directory: {os.getcwd()}")
print("=" * 70)

# ==================== CHECK 1: PYTHON ENVIRONMENT ====================
print("\n📌 CHECKING PYTHON ENVIRONMENT")
print("-" * 50)

print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

required_packages = [
    ('flask', 'flask'),
    ('flask_cors', 'flask-cors'),
    ('dotenv', 'python-dotenv'),
    ('requests', 'requests'),
    ('PIL', 'pillow'),
    ('odoo_integration', 'odoo_integration (local)'),
    ('document_scanner', 'document_scanner (local)'),
    ('image_preprocessor', 'image_preprocessor (local)')
]

for package_name, display_name in required_packages:
    try:
        if package_name in ['odoo_integration', 'document_scanner', 'image_preprocessor']:
            # Check local files
            if os.path.exists(f"{package_name}.py"):
                print(f"✅ {display_name} - Found")
            else:
                print(f"❌ {display_name} - NOT FOUND")
        else:
            importlib.import_module(package_name)
            print(f"✅ {display_name} - Installed")
    except ImportError as e:
        print(f"❌ {display_name} - NOT INSTALLED: {e}")

# ==================== CHECK 2: ENVIRONMENT VARIABLES ====================
print("\n📌 CHECKING .ENV FILE")
print("-" * 50)

env_path = os.path.join(os.path.dirname(__file__), '.env')
print(f"Looking for .env at: {env_path}")
print(f"File exists: {os.path.exists(env_path)}")

if os.path.exists(env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)
        
        novita_key = os.getenv('NOVITA_API_KEY')
        odoo_url = os.getenv('ODOO_URL')
        odoo_db = os.getenv('ODOO_DB')
        odoo_user = os.getenv('ODOO_USERNAME')
        odoo_pass = os.getenv('ODOO_PASSWORD')
        
        print(f"\n📋 Environment variables loaded:")
        print(f"  NOVITA_API_KEY: {'✅ SET' if novita_key else '❌ MISSING'}")
        if novita_key:
            print(f"    - Starts with: {novita_key[:10]}...")
            print(f"    - Length: {len(novita_key)}")
        
        print(f"  ODOO_URL: {'✅ SET' if odoo_url else '❌ MISSING'} - {odoo_url}")
        print(f"  ODOO_DB: {'✅ SET' if odoo_db else '❌ MISSING'} - {odoo_db}")
        print(f"  ODOO_USERNAME: {'✅ SET' if odoo_user else '❌ MISSING'} - {odoo_user}")
        print(f"  ODOO_PASSWORD: {'✅ SET' if odoo_pass else '❌ MISSING'}")
        
    except Exception as e:
        print(f"❌ Error loading .env: {e}")
else:
    print("❌ .env file not found!")

# ==================== CHECK 3: FILE STRUCTURE ====================
print("\n📌 CHECKING PROJECT FILES")
print("-" * 50)

backend_dir = os.path.dirname(__file__)
project_root = os.path.dirname(backend_dir)
frontend_dir = os.path.join(project_root, 'frontend')

required_files = [
    (backend_dir, 'main.py'),
    (backend_dir, 'odoo_integration.py'),
    (backend_dir, 'document_scanner.py'),
    (backend_dir, 'image_preprocessor.py'),
    (frontend_dir, 'index.html'),
    (frontend_dir, 'script.js'),
    (frontend_dir, 'style.css'),
]

for directory, filename in required_files:
    filepath = os.path.join(directory, filename)
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"✅ {filename} - Found ({size} bytes)")
    else:
        print(f"❌ {filename} - NOT FOUND at {filepath}")

# ==================== CHECK 4: PORT AVAILABILITY ====================
print("\n📌 CHECKING PORT 5000")
print("-" * 50)

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

if check_port(5000):
    print("⚠️ Port 5000 is IN USE - Another process is running")
    print("   Try: taskkill /F /IM python.exe")
else:
    print("✅ Port 5000 is FREE")

# ==================== CHECK 5: TEST NOVITA API KEY ====================
print("\n📌 TESTING NOVITA API KEY")
print("-" * 50)

if novita_key and novita_key != 'your_novita_api_key_here':
    try:
        headers = {
            "Authorization": f"Bearer {novita_key}",
            "Content-Type": "application/json"
        }
        
        # Simple test to check if key works
        test_payload = {
            "model": "qwen/qwen3-vl-235b-a22b-instruct",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 5
        }
        
        print("Testing Novita API connection...")
        response = requests.post(
            "https://api.novita.ai/v3/openai/chat/completions",
            headers=headers,
            json=test_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Novita API key is VALID")
        elif response.status_code == 401:
            print("❌ Novita API key is INVALID (Unauthorized)")
        else:
            print(f"⚠️ Novita API returned status {response.status_code}")
            print(f"   Response: {response.text[:100]}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Novita API - Check internet")
    except requests.exceptions.Timeout:
        print("❌ Novita API timeout")
    except Exception as e:
        print(f"❌ Error testing Novita API: {e}")
else:
    print("❌ Cannot test - NOVITA_API_KEY not set")

# ==================== CHECK 6: TEST ODOO CONNECTION ====================
print("\n📌 TESTING ODOO CONNECTION")
print("-" * 50)

if odoo_url and odoo_db and odoo_user and odoo_pass:
    try:
        import xmlrpc.client
        
        print(f"Connecting to Odoo at: {odoo_url}")
        
        # Test common endpoint
        common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
        version = common.version()
        print(f"✅ Odoo server version: {version.get('server_version', 'Unknown')}")
        
        # Test authentication
        uid = common.authenticate(odoo_db, odoo_user, odoo_pass, {})
        if uid:
            print(f"✅ Authentication successful! User ID: {uid}")
        else:
            print("❌ Authentication failed - Wrong credentials")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Odoo URL: {odoo_url}")
    except Exception as e:
        print(f"❌ Odoo connection error: {e}")
else:
    print("❌ Cannot test - Odoo credentials incomplete")

# ==================== CHECK 7: TEST FLASK ROUTES ====================
print("\n📌 TESTING FLASK ROUTES")
print("-" * 50)

# Try to start Flask briefly to check routes
try:
    print("Attempting to import main.py...")
    sys.path.insert(0, backend_dir)
    
    try:
        import main
        print("✅ main.py imported successfully")
        
        # Check if app exists
        if hasattr(main, 'app'):
            print("✅ Flask app found in main.py")
            
            # List all routes
            print("\n📋 Available routes:")
            for rule in main.app.url_map.iter_rules():
                methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
                print(f"   {rule} [{methods}]")
        else:
            print("❌ No Flask app found in main.py")
            
    except Exception as e:
        print(f"❌ Error importing main.py: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"❌ Error: {e}")

# ==================== SUMMARY ====================
print("\n" + "=" * 70)
print("📊 DIAGNOSTIC SUMMARY")
print("=" * 70)

print("\n🔴 CRITICAL CHECKS:")
print("  1. Python environment: Check above for missing packages")
print("  2. .env file: Check if NOVITA_API_KEY and Odoo credentials are set")
print("  3. Novita API: Check if key is valid")
print("  4. Odoo connection: Check if credentials work")
print("  5. File structure: Check if all files exist")

print("\n📝 NEXT STEPS:")
print("  1. Fix any ❌ errors above")
print("  2. Run 'python main.py' to start server")
print("  3. Check browser console (F12) for errors")
print("  4. Look for 🔥 PROCESS RECEIPT CALLED in terminal")

print("\n" + "=" * 70)
print("✅ Diagnostic complete - Report saved above")
print("=" * 70)

# Save report to file
report_file = f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
with open(report_file, 'w') as f:
    f.write("See console output for full diagnostic results\n")
print(f"\n📁 Report saved to: {report_file}")