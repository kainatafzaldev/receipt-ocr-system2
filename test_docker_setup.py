#!/usr/bin/env python3
"""
Docker Setup Test Script
Run this script to verify all Docker files are in the correct locations
"""

import os
import sys
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_status(message, status, details=""):
    """Print formatted status message"""
    if status == "✅":
        print(f"{GREEN}{status} {message}{RESET}")
    elif status == "❌":
        print(f"{RED}{status} {message}{RESET}")
    elif status == "⚠️":
        print(f"{YELLOW}{status} {message}{RESET}")
    elif status == "ℹ️":
        print(f"{BLUE}{status} {message}{RESET}")
    
    if details:
        print(f"   {details}")

def check_file(location, description, required=True):
    """Check if a file exists at the specified location"""
    path = Path(location)
    exists = path.exists()
    
    if exists:
        print_status(f"{description} found at: {location}", "✅")
        return True
    else:
        if required:
            print_status(f"{description} MISSING at: {location}", "❌")
        else:
            print_status(f"{description} not found at: {location} (optional)", "⚠️")
        return False

def check_directory(location, description):
    """Check if a directory exists"""
    path = Path(location)
    exists = path.is_dir()
    
    if exists:
        print_status(f"{description} directory found: {location}", "✅")
        return True
    else:
        print_status(f"{description} directory MISSING: {location}", "❌")
        return False

def main():
    """Main test function"""
    print("\n" + "="*60)
    print("🐳 DOCKER SETUP VERIFICATION TEST")
    print("="*60)
    
    # Get current directory
    current_dir = Path.cwd()
    print_status(f"Current directory: {current_dir}", "ℹ️")
    
    # Check if we're in project root
    is_root = (current_dir / "backend").is_dir() and (current_dir / "frontend").is_dir()
    
    if not is_root:
        print_status("You are NOT in the project root!", "⚠️")
        print("   Project root should contain 'backend' and 'frontend' folders")
        print(f"   Current contents: {[f.name for f in current_dir.iterdir() if f.is_dir()]}")
        
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    print("\n" + "-"*60)
    print("📁 CHECKING DIRECTORY STRUCTURE")
    print("-"*60)
    
    # Check main directories
    check_directory("backend", "Backend")
    check_directory("frontend", "Frontend")
    
    print("\n" + "-"*60)
    print("📄 CHECKING DOCKER FILES IN PROJECT ROOT")
    print("-"*60)
    
    # Files in project root
    root_files = [
        ("docker-compose.yml", "Docker Compose file", True),
        ("Makefile", "Makefile", False),  # Optional
        (".env", "Environment file", True),
    ]
    
    root_ok = True
    for filename, description, required in root_files:
        if not check_file(filename, description, required):
            if required:
                root_ok = False
    
    print("\n" + "-"*60)
    print("📄 CHECKING DOCKER FILES IN BACKEND FOLDER")
    print("-"*60)
    
    # Files in backend folder
    backend_files = [
        ("backend/Dockerfile", "Dockerfile", True),
        ("backend/.dockerignore", "Docker ignore file", True),
        ("backend/requirements.txt", "Requirements file", True),
        ("backend/main.py", "Main application", True),
        ("backend/odoo_integration.py", "Odoo integration", True),
        ("backend/image_preprocessor.py", "Image preprocessor", True),
        ("backend/document_scanner.py", "Document scanner", False),
    ]
    
    backend_ok = True
    for filename, description, required in backend_files:
        if not check_file(filename, description, required):
            if required:
                backend_ok = False
    
    print("\n" + "-"*60)
    print("🔍 CHECKING FILE CONTENT")
    print("-"*60)
    
    # Check Dockerfile content
    dockerfile_path = Path("backend/Dockerfile")
    if dockerfile_path.exists():
        with open(dockerfile_path, 'r') as f:
            content = f.read()
            if "FROM python:" in content:
                print_status("Dockerfile has correct base image", "✅")
            else:
                print_status("Dockerfile missing FROM python: line", "❌")
            
            if "EXPOSE 5000" in content:
                print_status("Dockerfile exposes port 5000", "✅")
            else:
                print_status("Dockerfile missing EXPOSE 5000", "❌")
    
    # Check docker-compose.yml content
    compose_path = Path("docker-compose.yml")
    if compose_path.exists():
        with open(compose_path, 'r') as f:
            content = f.read()
            if "receipt-ocr-app" in content:
                print_status("docker-compose has service defined", "✅")
            else:
                print_status("docker-compose missing service definition", "❌")
            
            if "ports:" in content and "5000:5000" in content:
                print_status("docker-compose has correct port mapping", "✅")
            else:
                print_status("docker-compose missing port mapping", "❌")
    
    # Check .env file
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, 'r') as f:
            content = f.read()
            required_vars = ['NOVITA_API_KEY', 'ODOO_URL', 'ODOO_DB', 'ODOO_USERNAME', 'ODOO_PASSWORD']
            missing_vars = []
            for var in required_vars:
                if var not in content:
                    missing_vars.append(var)
            
            if not missing_vars:
                print_status(".env file has all required variables", "✅")
            else:
                print_status(f".env missing: {', '.join(missing_vars)}", "⚠️")
    
    print("\n" + "-"*60)
    print("📊 SUMMARY")
    print("-"*60)
    
    if root_ok and backend_ok:
        print_status("✅✅✅ ALL DOCKER FILES ARE CORRECT! ✅✅✅", "✅")
        print("\nYour Docker setup is ready! You can now run:")
        print("  docker-compose build")
        print("  docker-compose up -d")
    else:
        print_status("⚠️ Some files are missing or incorrect", "⚠️")
        print("\nPlease fix the issues above before running Docker.")
    
    print("\n" + "="*60)
    print("📍 EXPECTED FILE LOCATIONS:")
    print("="*60)
    print("""
PROJECT ROOT (OCR_Project/):
├── docker-compose.yml
├── Makefile (optional)
├── .env
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── main.py
│   ├── odoo_integration.py
│   ├── image_preprocessor.py
│   └── document_scanner.py (optional)
└── frontend/
    ├── index.html
    ├── script.js
    └── style.css
    """)

if __name__ == "__main__":
    main()