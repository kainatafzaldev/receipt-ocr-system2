"""
============================================================
🚑 PROJECT DOCTOR - COMPLETE DIAGNOSTIC TOOL
============================================================
This script will examine your entire OCR+Odoo project
and identify ALL issues preventing it from working correctly.
"""

import os
import sys
import re
import json
import subprocess
import importlib.util
from pathlib import Path

class ProjectDoctor:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.good = []
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.frontend_dir = os.path.join(self.project_root, '..', 'frontend')
        
    def print_header(self, text):
        print(f"\n{'='*60}")
        print(f"🔍 {text}")
        print(f"{'='*60}")
    
    def print_issue(self, issue):
        print(f"❌ {issue}")
        self.issues.append(issue)
    
    def print_warning(self, warning):
        print(f"⚠️  {warning}")
        self.warnings.append(warning)
    
    def print_good(self, good):
        print(f"✅ {good}")
        self.good.append(good)
    
    def check_file_exists(self, filepath, description):
        if os.path.exists(filepath):
            self.print_good(f"{description} found: {os.path.basename(filepath)}")
            return True
        else:
            self.print_issue(f"{description} MISSING: {filepath}")
            return False
    
    def analyze_main_py(self):
        self.print_header("ANALYZING MAIN.PY")
        
        main_py_path = os.path.join(self.project_root, 'main.py')
        if not self.check_file_exists(main_py_path, "main.py"):
            return
        
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for validate_api_key function definition
        if 'def validate_api_key' in content:
            self.print_good("validate_api_key() function is defined")
        else:
            self.print_issue("validate_api_key() function is MISSING")
        
        # Check function order (validate_api_key before it's used)
        validate_pos = content.find('def validate_api_key')
        extract_pos = content.find('def extract_text_with_vlm')
        
        if validate_pos != -1 and extract_pos != -1:
            if validate_pos < extract_pos:
                self.print_good("validate_api_key() defined BEFORE extract_text_with_vlm()")
            else:
                self.print_issue("validate_api_key() defined AFTER extract_text_with_vlm() - This will cause errors!")
        
        # Check for universal_receipt_handler
        if 'def universal_receipt_handler' in content:
            self.print_good("universal_receipt_handler() function exists")
        else:
            self.print_issue("universal_receipt_handler() function MISSING")
        
        # Check for proper item extraction in universal handler
        if 'item_candidates' in content and 'price_values' in content:
            self.print_good("universal handler has item and price arrays")
        else:
            self.print_warning("universal handler may not properly separate items from prices")
        
        # Check for hardcoded item names
        hardcoded_items = ['ASADA TACO', 'ATM CHARGE', 'Papyrus']
        found_hardcoded = []
        for item in hardcoded_items:
            if item in content and 'def universal' in content:
                found_hardcoded.append(item)
        
        if found_hardcoded:
            self.print_warning(f"Hardcoded item names found: {found_hardcoded} - This limits receipt types")
        
        # Check prepare_odoo_data function
        if 'def prepare_odoo_data' in content:
            self.print_good("prepare_odoo_data() function exists")
            
            # Check if it filters properly
            if 'if any(x in lower_label for x in' in content:
                self.print_good("prepare_odoo_data filters out non-items")
            else:
                self.print_warning("prepare_odoo_data may not filter out headers properly")
        else:
            self.print_issue("prepare_odoo_data() function MISSING")
        
        # Check for proper tax handling
        if 'tax_amount' in content:
            self.print_good("Tax amount handling present")
        else:
            self.print_warning("Tax handling may be missing")
    
    def analyze_odoo_integration(self):
        self.print_header("ANALYZING ODOO INTEGRATION")
        
        odoo_path = os.path.join(self.project_root, 'odoo_integration.py')
        if not self.check_file_exists(odoo_path, "odoo_integration.py"):
            return
        
        with open(odoo_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check connection method
        if 'def connect' in content:
            self.print_good("connect() method exists")
        else:
            self.print_issue("connect() method MISSING")
        
        # Check create_vendor_bill method
        if 'def create_vendor_bill' in content:
            self.print_good("create_vendor_bill() method exists")
            
            # Check for error handling
            if 'try:' in content and 'except' in content:
                self.print_good("Error handling present in create_vendor_bill")
            else:
                self.print_warning("create_vendor_bill may lack proper error handling")
        else:
            self.print_issue("create_vendor_bill() method MISSING")
        
        # Check for tax handling
        if 'tax' in content.lower():
            self.print_good("Tax handling present")
        else:
            self.print_warning("Tax handling may be missing in Odoo integration")
    
    def analyze_frontend(self):
        self.print_header("ANALYZING FRONTEND")
        
        if not os.path.exists(self.frontend_dir):
            self.print_issue(f"Frontend directory NOT FOUND: {self.frontend_dir}")
            return
        
        self.print_good(f"Frontend directory exists: {self.frontend_dir}")
        
        # Check index.html
        index_path = os.path.join(self.frontend_dir, 'index.html')
        if self.check_file_exists(index_path, "index.html"):
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'script.js' in content:
                self.print_good("index.html references script.js")
            else:
                self.print_issue("index.html does NOT reference script.js")
        
        # Check script.js
        script_path = os.path.join(self.frontend_dir, 'script.js')
        if self.check_file_exists(script_path, "script.js"):
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check BACKEND_URL
            if 'BACKEND_URL' in content:
                self.print_good("BACKEND_URL is defined")
                
                # Extract BACKEND_URL
                url_match = re.search(r'BACKEND_URL\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                if url_match:
                    url = url_match.group(1)
                    self.print_good(f"BACKEND_URL is set to: {url}")
                else:
                    self.print_warning("Could not extract BACKEND_URL value")
            else:
                self.print_issue("BACKEND_URL is NOT defined in script.js")
            
            # Check displaySideBySide function
            if 'function displaySideBySide' in content:
                self.print_good("displaySideBySide() function exists")
            else:
                self.print_issue("displaySideBySide() function MISSING")
            
            # Check for item filtering
            if 'skipPatterns' in content or 'itemLines' in content:
                self.print_good("Item filtering logic present")
            else:
                self.print_warning("Frontend may not filter out non-items properly")
    
    def check_environment(self):
        self.print_header("CHECKING ENVIRONMENT")
        
        # Check .env file
        env_path = os.path.join(self.project_root, '.env')
        if os.path.exists(env_path):
            self.print_good(".env file exists")
            
            with open(env_path, 'r') as f:
                env_content = f.read()
            
            required_vars = ['NOVITA_API_KEY', 'ODOO_URL', 'ODOO_DB', 'ODOO_USERNAME', 'ODOO_PASSWORD']
            for var in required_vars:
                if var in env_content:
                    self.print_good(f"{var} is set in .env")
                else:
                    self.print_issue(f"{var} is MISSING from .env")
        else:
            self.print_issue(".env file MISSING - This will cause API connection failures")
        
        # Check Python packages
        required_packages = ['flask', 'flask-cors', 'python-dotenv', 'requests', 'pillow']
        for package in required_packages:
            try:
                importlib.import_module(package.replace('-', '_'))
                self.print_good(f"Python package '{package}' is installed")
            except ImportError:
                self.print_issue(f"Python package '{package}' is NOT installed")
    
    def check_data_flow(self):
        self.print_header("ANALYZING DATA FLOW")
        
        print("\n📋 EXPECTED DATA FLOW:")
        print("   1. Image → VLM extracts raw text")
        print("   2. Raw text → universal_receipt_handler()")
        print("   3. Handler separates: headers, items, prices, summaries")
        print("   4. Items matched with prices in order")
        print("   5. Unit prices calculated (total/quantity)")
        print("   6. Data formatted for Odoo (only items + tax)")
        print("   7. Odoo API receives clean data")
        
        # Check for common data flow issues
        print("\n🔍 COMMON ISSUES TO CHECK:")
        print("   ❌ Items being filtered out incorrectly")
        print("   ❌ Prices not matching with items")
        print("   ❌ Quantities not being detected")
        print("   ❌ Headers being sent as items to Odoo")
        print("   ❌ Tax not being extracted properly")
        print("   ❌ Unit price calculation wrong (total vs unit)")
    
    def provide_solutions(self):
        self.print_header("SOLUTIONS FOR DETECTED ISSUES")
        
        if self.issues:
            print("\n🔴 CRITICAL ISSUES FOUND:")
            for i, issue in enumerate(self.issues, 1):
                print(f"   {i}. {issue}")
        else:
            self.print_good("No critical issues found!")
        
        if self.warnings:
            print("\n🟡 WARNINGS:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. {warning}")
        
        print("\n🟢 RECOMMENDED FIXES:")
        print("   1. Fix function order: Move validate_api_key() to top of file")
        print("   2. Make universal handler truly dynamic (no hardcoded item names)")
        print("   3. Ensure price extraction works for all formats")
        print("   4. Add better filtering in prepare_odoo_data()")
        print("   5. Check BACKEND_URL in script.js matches your server IP")
        print("   6. Verify all required Python packages are installed")
        print("   7. Ensure .env file has all required variables")
    
    def run_diagnostic(self):
        print("\n" + "="*70)
        print("🚑 PROJECT DOCTOR - COMPLETE DIAGNOSTIC")
        print("="*70)
        print(f"Project root: {self.project_root}")
        print(f"Time: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.analyze_main_py()
        self.analyze_odoo_integration()
        self.analyze_frontend()
        self.check_environment()
        self.check_data_flow()
        self.provide_solutions()
        
        print("\n" + "="*70)
        print(f"📊 DIAGNOSTIC SUMMARY:")
        print(f"   🔴 Critical Issues: {len(self.issues)}")
        print(f"   🟡 Warnings: {len(self.warnings)}")
        print(f"   🟢 Good: {len(self.good)}")
        print("="*70)
        
        if not self.issues:
            print("\n🎉 Your project looks good! If still having issues, check:")
            print("   - Network connectivity to Odoo")
            print("   - Odoo credentials in .env file")
            print("   - Novita.ai API key validity")
            print("   - Receipt image quality")
        else:
            print("\n🔧 Fix the critical issues above first, then run this doctor again.")

if __name__ == "__main__":
    doctor = ProjectDoctor()
    doctor.run_diagnostic()