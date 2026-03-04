import os
import sys
import json
import base64
import requests
import logging
from dotenv import load_dotenv
from pathlib import Path

# Configure logging to show everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

print("=" * 70)
print("🔍 OCR SYSTEM DEBUGGER - COMPLETE DIAGNOSTIC")
print("=" * 70)

def check_python_environment():
    """Check Python and dependencies"""
    print("\n1. 📦 CHECKING PYTHON ENVIRONMENT")
    print("-" * 40)
    
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Working directory: {os.getcwd()}")
    
    # Check required packages
    required_packages = [
        "flask", "flask-cors", "python-dotenv", "requests", "Pillow"
    ]
    
    print("\nChecking packages:")
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - MISSING! Run: pip install {package}")

def check_env_file():
    """Check .env file configuration"""
    print("\n2. 🔑 CHECKING .ENV FILE")
    print("-" * 40)
    
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file NOT FOUND!")
        print("Create .env file with:")
        print('''
NOVITA_API_KEY=sk_your_actual_key_here
MODEL_NAME=deepseek/deepseek-ocr-2
PORT=5000
DEBUG=True
UPLOAD_FOLDER=uploads
''')
        return None
    
    print("✅ .env file found")
    
    # Load and check .env
    load_dotenv()
    
    api_key = os.getenv('NOVITA_API_KEY')
    model_name = os.getenv('MODEL_NAME', 'deepseek/deepseek-ocr-2')
    
    if not api_key:
        print("❌ NOVITA_API_KEY not set in .env")
    elif api_key == 'your_actual_api_key_here':
        print("❌ NOVITA_API_KEY is using placeholder value")
        print("   Get your key from: https://novita.ai/")
    else:
        print(f"✅ API Key: Found ({api_key[:10]}...)")
    
    print(f"✅ Model: {model_name}")
    
    return api_key, model_name

def test_api_connection(api_key):
    """Test Novita AI API connection"""
    print("\n3. 🌐 TESTING NOVITA AI API CONNECTION")
    print("-" * 40)
    
    if not api_key:
        print("❌ Cannot test API - no API key")
        return False
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Simple models endpoint
    print("Testing API endpoint...")
    try:
        response = requests.get(
            "https://api.novita.ai/v3/openai/models",
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Connection SUCCESSFUL!")
            print(f"Available models: {len(data.get('data', []))}")
            
            # Check if our model is available
            models = [m['id'] for m in data.get('data', [])]
            ocr_models = [m for m in models if 'ocr' in m.lower()]
            print(f"OCR models available: {ocr_models}")
            
            return True
        elif response.status_code == 401:
            print("❌ API Error 401: UNAUTHORIZED")
            print("   Your API key is invalid or expired")
            print("   Get a new key from: https://novita.ai/")
        elif response.status_code == 429:
            print("❌ API Error 429: RATE LIMITED")
            print("   Too many requests. Wait and try again.")
        else:
            print(f"❌ API Error {response.status_code}: {response.text[:200]}")
            
    except requests.exceptions.ConnectionError:
        print("❌ NETWORK CONNECTION ERROR")
        print("   Check your internet connection")
    except requests.exceptions.Timeout:
        print("❌ API TIMEOUT")
        print("   Network is slow or API is down")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {str(e)}")
    
    return False

def test_ocr_extraction(api_key, model_name):
    """Test actual OCR extraction"""
    print("\n4. 🖼️ TESTING OCR EXTRACTION")
    print("-" * 40)
    
    if not api_key:
        print("❌ Cannot test OCR - no API key")
        return
    
    # Create a test image
    print("Creating test receipt image...")
    from PIL import Image, ImageDraw
    
    img = Image.new('RGB', (500, 300), color='white')
    d = ImageDraw.Draw(img)
    
    receipt_text = """TEST SUPERMARKET
123 Main Street
City, State 12345
Tel: (555) 123-4567

DATE: 2024-01-15
TIME: 14:30:00
RECEIPT #: TEST-001

1 Apples             $3.99
2 Bread              $5.98
1 Milk               $4.29
1 Eggs               $2.99

SUBTOTAL:           $17.25
TAX (8%):           $1.38
TOTAL:              $18.63

CASH:               $20.00
CHANGE:             $1.37

THANK YOU!"""
    
    d.text((10, 10), receipt_text, fill='black')
    test_image_path = 'debug_test_receipt.png'
    img.save(test_image_path)
    print(f"✅ Created test image: {test_image_path}")
    
    # Read and encode image
    with open(test_image_path, 'rb') as f:
        image_bytes = f.read()
    
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    # Prepare OCR request
    url = "https://api.novita.ai/v3/openai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all text from this receipt image exactly as it appears."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.1
    }
    
    print("\nSending OCR request...")
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ OCR EXTRACTION SUCCESSFUL!")
            
            if 'choices' in result and len(result['choices']) > 0:
                text = result['choices'][0]['message']['content']
                print(f"\n📝 EXTRACTED TEXT ({len(text)} characters):")
                print("-" * 50)
                print(text)
                print("-" * 50)
                
                # Check for common issues
                if "This is a request" in text or "raw data" in text:
                    print("\n⚠️  WARNING: Model is echoing the prompt")
                    print("   The prompt might need adjustment")
                
                # Show token usage
                if 'usage' in result:
                    usage = result['usage']
                    print(f"\n📊 Token Usage:")
                    print(f"   Prompt tokens: {usage.get('prompt_tokens')}")
                    print(f"   Completion tokens: {usage.get('completion_tokens')}")
                    print(f"   Total tokens: {usage.get('total_tokens')}")
                
                return True
            else:
                print("❌ No text in response")
                print(f"Response: {json.dumps(result, indent=2)[:500]}")
                
        else:
            print(f"❌ OCR FAILED: {response.status_code}")
            print(f"Error: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ OCR ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up test file
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
            print(f"\n🧹 Cleaned up test file: {test_image_path}")
    
    return False

def check_flask_app():
    """Check if Flask app is working"""
    print("\n5. 🚀 CHECKING FLASK APPLICATION")
    print("-" * 40)
    
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Flask app is RUNNING")
            print(f"   Status: {data.get('status')}")
            print(f"   API Key configured: {data.get('api_key_configured')}")
            print(f"   Model: {data.get('model_name')}")
            
            # Test the process-receipt endpoint
            print("\nTesting /api/process-receipt endpoint...")
            
            # Create a small test image
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (100, 50), color='white')
            d = ImageDraw.Draw(img)
            d.text((10,10), "TEST", fill='black')
            img.save('flask_test.png')
            
            with open('flask_test.png', 'rb') as f:
                base64_img = base64.b64encode(f.read()).decode('utf-8')
            
            test_payload = {
                "image": f"data:image/png;base64,{base64_img}",
                "test": True
            }
            
            flask_response = requests.post(
                "http://localhost:5000/api/process-receipt",
                json=test_payload,
                timeout=10
            )
            
            os.remove('flask_test.png')
            
            if flask_response.status_code == 200:
                print("✅ Flask endpoint is WORKING")
            else:
                print(f"❌ Flask endpoint error: {flask_response.status_code}")
                print(f"Response: {flask_response.text[:200]}")
                
        else:
            print(f"❌ Flask returned error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Flask app NOT RUNNING")
        print("   Start Flask with: python main.py")
    except Exception as e:
        print(f"❌ Flask check error: {str(e)}")

def check_file_permissions():
    """Check file and folder permissions"""
    print("\n6. 📁 CHECKING FILE PERMISSIONS")
    print("-" * 40)
    
    # Check uploads folder
    uploads_path = Path("uploads")
    if not uploads_path.exists():
        print("⚠️ uploads folder doesn't exist")
        try:
            uploads_path.mkdir(exist_ok=True)
            print("✅ Created uploads folder")
        except Exception as e:
            print(f"❌ Failed to create uploads folder: {e}")
    else:
        print("✅ uploads folder exists")
    
    # Check if we can write to current directory
    test_file = "test_permission.txt"
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print("✅ Can write to current directory")
    except Exception as e:
        print(f"❌ Cannot write to directory: {e}")

def main():
    """Run all diagnostic tests"""
    print("Starting complete diagnostic...\n")
    
    # Run all checks
    check_python_environment()
    
    api_info = check_env_file()
    if api_info:
        api_key, model_name = api_info
        test_api_connection(api_key)
        test_ocr_extraction(api_key, model_name)
    
    check_flask_app()
    check_file_permissions()
    
    print("\n" + "=" * 70)
    print("✅ DIAGNOSTIC COMPLETE")
    print("=" * 70)
    
    print("\n📋 SUMMARY OF ISSUES FOUND:")
    print("1. Check the red '❌' messages above")
    print("2. Most common issues:")
    print("   - API key not configured in .env file")
    print("   - No internet connection")
    print("   - Flask app not running")
    print("   - Missing Python packages")
    
    print("\n🚀 QUICK FIXES:")
    print("1. Ensure .env has: NOVITA_API_KEY=sk_your_actual_key_here")
    print("2. Install packages: pip install flask flask-cors python-dotenv requests Pillow")
    print("3. Start Flask: python main.py")
    print("4. Check internet connection")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Debug interrupted by user")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR IN DEBUGGER: {str(e)}")
        import traceback
        traceback.print_exc()