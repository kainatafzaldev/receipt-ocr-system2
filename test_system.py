#!/usr/bin/env python3
"""
OCR Receipt Processor - System Testing Script
Tests backend API endpoints and basic functionality
"""

import requests
import json
import sys
import base64
import os
from pathlib import Path

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print header"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")

def test_backend_connection(backend_url):
    """Test if backend is running and accessible"""
    print_info(f"Testing backend at: {backend_url}")
    
    try:
        response = requests.get(f"{backend_url}/api/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Backend is running")
            
            # Check API key
            if data.get('api_key_configured'):
                print_success("API key is configured")
            else:
                print_error("API key not configured - check .env file")
                return False
            
            # Print details
            print_info(f"Model: {data.get('model', 'Unknown')}")
            print_info(f"Status: {data.get('status', 'Unknown')}")
            
            return True
        else:
            print_error(f"Backend returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to backend at {backend_url}")
        print_warning("Make sure backend is running: python backend/main.py")
        return False
    except requests.exceptions.Timeout:
        print_error("Backend connection timed out")
        return False
    except Exception as e:
        print_error(f"Error connecting to backend: {str(e)}")
        return False

def test_api_endpoints(backend_url):
    """Test API endpoints"""
    print_header("Testing API Endpoints")
    
    # Test /api endpoint
    try:
        response = requests.get(f"{backend_url}/api", timeout=5)
        if response.status_code == 200:
            print_success("GET /api - API info endpoint works")
        else:
            print_error(f"GET /api returned {response.status_code}")
    except Exception as e:
        print_error(f"GET /api failed: {str(e)}")
    
    # Test /api/test endpoint
    try:
        response = requests.get(f"{backend_url}/api/test", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("GET /api/test - Test endpoint works")
            print_info(f"Message: {data.get('message', 'No message')}")
        else:
            print_error(f"GET /api/test returned {response.status_code}")
    except Exception as e:
        print_error(f"GET /api/test failed: {str(e)}")

def test_frontend_serving(backend_url):
    """Test if frontend is being served"""
    print_header("Testing Frontend Serving")
    
    try:
        response = requests.get(f"{backend_url}/", timeout=5)
        
        if response.status_code == 200:
            print_success("Frontend (/) is being served")
            
            # Check for key elements
            if 'Receipt OCR Processor' in response.text:
                print_success("Frontend HTML contains expected title")
            else:
                print_warning("Frontend title not found in HTML")
            
            if 'script.js' in response.text:
                print_success("Frontend script.js is referenced")
            else:
                print_warning("Frontend script.js not found")
            
            return True
        else:
            print_error(f"Frontend returned status {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Cannot access frontend: {str(e)}")
        return False

def test_ocr_processing(backend_url):
    """Test OCR processing with a simple test image"""
    print_header("Testing OCR Processing")
    
    # Look for test image
    test_image_paths = [
        'test_receipt.png',
        'images/test_receipt.png',
        os.path.join(os.path.dirname(__file__), 'test_receipt.png'),
    ]
    
    test_image_path = None
    for path in test_image_paths:
        if os.path.exists(path):
            test_image_path = path
            break
    
    if not test_image_path:
        print_warning("No test image found - skipping OCR test")
        print_info("Place an image at: test_receipt.png")
        return None
    
    try:
        # Read and encode image
        with open(test_image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        print_info(f"Testing with image: {test_image_path}")
        print_info(f"Image size: {len(image_data)} bytes (base64)")
        
        # Send to backend
        payload = {
            'image': f'data:image/png;base64,{image_data}'
        }
        
        response = requests.post(
            f"{backend_url}/api/process-receipt",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print_success("OCR processing succeeded")
                print_info(f"Processing time: {data.get('processing_time_seconds', 'Unknown')}s")
                
                if data.get('data'):
                    extracted = data['data']
                    text_length = len(extracted.get('text', ''))
                    tokens = extracted.get('tokens_used', 0)
                    
                    print_info(f"Extracted text length: {text_length} characters")
                    print_info(f"Tokens used: {tokens}")
                    print_info(f"Model: {extracted.get('model', 'Unknown')}")
                    
                    if text_length > 0:
                        print_success("Text content extracted!")
                        # Show first 200 chars
                        preview = extracted.get('text', '')[:200]
                        print_info(f"Preview: {preview}...")
                    else:
                        print_warning("No text extracted from image")
                        print_warning("This might be a blank image or very complex receipt")
                
                return True
            else:
                print_error(f"OCR processing failed: {data.get('error', 'Unknown error')}")
                return False
        else:
            print_error(f"API returned status {response.status_code}")
            if response.text:
                print_error(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print_error("OCR processing timed out (>30 seconds)")
        print_warning("This might indicate a slow API connection")
        return False
    except Exception as e:
        print_error(f"OCR test failed: {str(e)}")
        return False

def test_file_upload(backend_url):
    """Test file upload capability"""
    print_header("Testing File Upload")
    
    # Look for test image
    test_image_path = None
    for path in ['test_receipt.png', os.path.join(os.path.dirname(__file__), 'test_receipt.png')]:
        if os.path.exists(path):
            test_image_path = path
            break
    
    if not test_image_path:
        print_warning("No test image found - skipping file upload test")
        return None
    
    try:
        # Test multipart file upload (if backend supports it)
        with open(test_image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{backend_url}/api/upload",
                files=files,
                timeout=10
            )
        
        # This endpoint might not exist - that's OK
        if response.status_code == 200:
            print_success("File upload endpoint exists")
        elif response.status_code == 404:
            print_warning("File upload endpoint not implemented (optional feature)")
        
    except Exception as e:
        print_warning(f"File upload test skipped: {str(e)}")

def run_full_test():
    """Run full system test"""
    print_header("OCR Receipt Processor - System Test")
    
    backend_url = 'http://localhost:5000'
    print_info(f"Testing backend at: {backend_url}")
    
    # Step 1: Check backend connection
    print_header("Step 1: Backend Connection")
    if not test_backend_connection(backend_url):
        print_error("\nBackend not running!")
        print_warning("Start backend with: python backend/main.py")
        return False
    
    # Step 2: Test API endpoints
    print_header("Step 2: API Endpoints")
    test_api_endpoints(backend_url)
    
    # Step 3: Test frontend
    print_header("Step 3: Frontend Serving")
    frontend_ok = test_frontend_serving(backend_url)
    
    # Step 4: Test OCR processing
    print_header("Step 4: OCR Processing")
    test_ocr_processing(backend_url)
    
    # Step 5: Test file upload
    print_header("Step 5: File Upload")
    test_file_upload(backend_url)
    
    # Summary
    print_header("Test Summary")
    print_success("All essential tests completed!")
    
    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60)
    print_info("1. Open browser to: http://localhost:5000/")
    print_info("2. Check backend connection status at top of page")
    print_info("3. Upload a receipt image")
    print_info("4. Click 'Process Receipt' button")
    print_info("5. View extracted data")
    print("\n")

if __name__ == '__main__':
    try:
        run_full_test()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)
