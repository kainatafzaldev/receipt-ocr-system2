"""
API Key Diagnostic Tool
Run this to check why your API key isn't working
"""

import os
import sys
from dotenv import load_dotenv

print("=" * 70)
print("🔑 API KEY DIAGNOSTIC TOOL")
print("=" * 70)

# ===== TEST 1: Check Python environment =====
print("\n📌 TEST 1: Python Environment")
print("-" * 50)
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Script location: {__file__}")

# ===== TEST 2: Check .env file =====
print("\n📌 TEST 2: .env File Check")
print("-" * 50)

env_path = os.path.join(os.getcwd(), '.env')
print(f".env path: {env_path}")
print(f"File exists: {os.path.exists(env_path)}")

if os.path.exists(env_path):
    # Show file permissions
    print(f"File size: {os.path.getsize(env_path)} bytes")
    print(f"Readable: {os.access(env_path, os.R_OK)}")
    
    # Show first few lines (masking values)
    print("\n📄 .env content (values masked):")
    with open(env_path, 'r') as f:
        for i, line in enumerate(f.readlines()[:10]):  # First 10 lines only
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    if 'PASSWORD' in key.upper() or 'KEY' in key.upper():
                        print(f"  {i+1}. {key}=********")
                    else:
                        print(f"  {i+1}. {line}")
                else:
                    print(f"  {i+1}. {line}")
            else:
                print(f"  {i+1}. {line}")

# ===== TEST 3: Load .env and check variables =====
print("\n📌 TEST 3: Loading .env File")
print("-" * 50)

# Try loading with different methods
print("Method 1: load_dotenv()")
load_dotenv()  # Default
key1 = os.getenv('NOVITA_API_KEY')
print(f"  NOVITA_API_KEY found: {bool(key1)}")
if key1:
    print(f"  Length: {len(key1)}")
    print(f"  First 5 chars: {key1[:5]}")
    print(f"  Last 5 chars: {key1[-5:]}")
    # Check for hidden characters
    print(f"  ASCII values: {[ord(c) for c in key1[:10]]}")

print("\nMethod 2: load_dotenv(override=True)")
load_dotenv(override=True)
key2 = os.getenv('NOVITA_API_KEY')
print(f"  NOVITA_API_KEY found: {bool(key2)}")

print("\nMethod 3: Load with absolute path")
load_dotenv(env_path, override=True)
key3 = os.getenv('NOVITA_API_KEY')
print(f"  NOVITA_API_KEY found: {bool(key3)}")

# ===== TEST 4: Check all required variables =====
print("\n📌 TEST 4: Checking All Required Variables")
print("-" * 50)

required_vars = [
    'NOVITA_API_KEY',
    'NOVITA_API_BASE',
    'VLM_MODEL',
    'LLM_MODEL',
    'PORT',
    'ODOO_URL',
    'ODOO_DB',
    'ODOO_USERNAME',
    'ODOO_PASSWORD'
]

for var in required_vars:
    value = os.getenv(var)
    if value:
        if 'PASSWORD' in var or 'KEY' in var:
            print(f"✅ {var}: [HIDDEN] (length: {len(value)})")
        else:
            print(f"✅ {var}: {value}")
    else:
        print(f"❌ {var}: NOT SET")

# ===== TEST 5: Test the validate_api_key function directly =====
print("\n📌 TEST 5: Testing validate_api_key() Function")
print("-" * 50)

try:
    # Try to import the function from main.py
    sys.path.insert(0, os.getcwd())
    from main import validate_api_key, NOVITA_API_KEY as global_key
    
    print(f"Global NOVITA_API_KEY variable: {bool(global_key)}")
    if global_key:
        print(f"  First 5 chars: {global_key[:5]}")
    
    result, message = validate_api_key()
    print(f"validate_api_key() returned: {result}")
    print(f"Message: {message}")
    
except ImportError as e:
    print(f"❌ Could not import from main.py: {e}")
except Exception as e:
    print(f"❌ Error calling validate_api_key(): {e}")

# ===== TEST 6: Test with Flask request context =====
print("\n📌 TEST 6: Testing in Flask Request Context")
print("-" * 50)

try:
    from main import app
    
    with app.test_request_context():
        # Inside Flask request context
        from main import validate_api_key as ctx_validate
        from main import NOVITA_API_KEY as ctx_key
        
        print(f"Inside request context - Global key exists: {bool(ctx_key)}")
        if ctx_key:
            print(f"  First 5 chars: {ctx_key[:5]}")
        
        result, message = ctx_validate()
        print(f"validate_api_key() in context: {result}")
        print(f"Message: {message}")
        
except Exception as e:
    print(f"❌ Error testing request context: {e}")

# ===== TEST 7: Test direct API call to Novita =====
print("\n📌 TEST 7: Testing Direct API Call to Novita")
print("-" * 50)

key = os.getenv('NOVITA_API_KEY')
if key:
    import requests
    import json
    
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    # Simple test payload
    payload = {
        "model": "qwen/qwen3-vl-235b-a22b-instruct",
        "messages": [
            {"role": "user", "content": "Say 'test'"}
        ],
        "max_tokens": 5
    }
    
    try:
        print("Sending test request to Novita API...")
        response = requests.post(
            "https://api.novita.ai/v3/openai/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ API key is VALID and working!")
            print(f"Response: {response.json()['choices'][0]['message']['content']}")
        elif response.status_code == 401:
            print("❌ API key is INVALID (Unauthorized)")
        else:
            print(f"⚠️ API returned status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Novita API - Check internet")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("❌ Cannot test - NOVITA_API_KEY not found")

# ===== TEST 8: Check for common issues =====
print("\n📌 TEST 8: Common Issues Check")
print("-" * 50)

issues_found = []

# Check for spaces in key
key = os.getenv('NOVITA_API_KEY')
if key:
    if key.startswith(' '):
        issues_found.append("❌ Key starts with a space!")
    if ' ' in key:
        issues_found.append("❌ Key contains spaces!")
    if key.endswith(' '):
        issues_found.append("❌ Key ends with a space!")
    if len(key) < 20:
        issues_found.append("❌ Key is too short (should be >20 chars)")
else:
    issues_found.append("❌ Key not loaded at all")

# Check .env file permissions
if os.path.exists(env_path):
    if not os.access(env_path, os.R_OK):
        issues_found.append("❌ .env file is not readable")
else:
    issues_found.append("❌ .env file missing")

if issues_found:
    print("\n🔴 ISSUES FOUND:")
    for issue in issues_found:
        print(f"  {issue}")
else:
    print("✅ No common issues detected!")

# ===== SUMMARY =====
print("\n" + "=" * 70)
print("📊 DIAGNOSTIC SUMMARY")
print("=" * 70)

print(f"\n🔑 API Key configured: {bool(os.getenv('NOVITA_API_KEY'))}")
print(f"🏥 Health check would show: {'True' if bool(os.getenv('NOVITA_API_KEY')) else 'False'}")

print("\n📝 NEXT STEPS:")
print("  1. If any ❌ errors above, fix them")
print("  2. Make sure your .env file has NO spaces around =")
print("  3. Restart your server: python main.py")
print("  4. Test again: Invoke-RestMethod -Uri 'http://localhost:5000/api/health' -Method Get")

print("\n" + "=" * 70)