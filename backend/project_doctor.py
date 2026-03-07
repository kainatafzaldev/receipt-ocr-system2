# project_doctor.py
import os
import sys
import socket
import xmlrpc.client
import requests
from datetime import datetime
import importlib.util
import subprocess

class ProjectDoctor:
    def __init__(self):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.backend_dir = self.project_root
        self.frontend_dir = os.path.join(os.path.dirname(self.project_root), 'frontend')
        self.issues = []
        self.warnings = []
        self.passed = []
        
    def print_header(self, text):
        print("\n" + "="*60)
        print(f"🔍 {text}")
        print("="*60)
    
    def print_pass(self, text):
        print(f"  ✅ {text}")
        self.passed.append(text)
    
    def print_warning(self, text):
        print(f"  ⚠️  {text}")
        self.warnings.append(text)
    
    def print_fail(self, text):
        print(f"  ❌ {text}")
        self.issues.append(text)
    
    def check_python_environment(self):
        self.print_header("Checking Python Environment")
        
        # Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
            self.print_pass(f"Python {python_version} (OK)")
        else:
            self.print_fail(f"Python {python_version} (Need 3.8+)")
        
        # Required packages
        required_packages = [
            'flask', 'flask_cors', 'python_dotenv', 
            'requests', 'PIL', 'xmlrpc.client'
        ]
        
        for package in required_packages:
            try:
                if package == 'PIL':
                    from PIL import Image
                elif package == 'xmlrpc.client':
                    import xmlrpc.client
                else:
                    importlib.import_module(package)
                self.print_pass(f"{package} installed")
            except ImportError as e:
                self.print_fail(f"{package} missing - {str(e)}")
    
    def check_env_file(self):
        self.print_header("Checking .env Configuration")
        
        env_path = os.path.join(self.backend_dir, '.env')
        if not os.path.exists(env_path):
            self.print_fail(".env file not found!")
            return
        
        self.print_pass(".env file exists")
        
        # Read and parse .env
        with open(env_path, 'r') as f:
            env_content = f.read()
        
        # Check each required variable
        required_vars = {
            'NOVITA_API_KEY': 'Novita AI API Key',
            'ODOO_URL': 'Odoo URL',
            'ODOO_DB': 'Odoo Database',
            'ODOO_USERNAME': 'Odoo Username',
            'ODOO_PASSWORD': 'Odoo Password'
        }
        
        env_dict = {}
        for line in env_content.split('\n'):
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
        
        for var, description in required_vars.items():
            if var in env_dict and env_dict[var]:
                if var == 'NOVITA_API_KEY' and env_dict[var].startswith('sk_W'):
                    self.print_pass(f"{description} configured")
                elif var == 'ODOO_URL' and env_dict[var].startswith(('http://', 'https://')):
                    self.print_pass(f"{description}: {env_dict[var]}")
                elif var in ['ODOO_DB', 'ODOO_USERNAME']:
                    self.print_pass(f"{description}: {env_dict[var]}")
                elif var == 'ODOO_PASSWORD':
                    self.print_pass(f"{description}: [HIDDEN]")
            else:
                self.print_fail(f"{description} missing or empty")
        
        return env_dict
    
    def test_odoo_connection(self, env_vars):
        self.print_header("Testing Odoo Connection")
        
        url = env_vars.get('ODOO_URL', '').rstrip('/')
        db = env_vars.get('ODOO_DB', '')
        username = env_vars.get('ODOO_USERNAME', '')
        password = env_vars.get('ODOO_PASSWORD', '')
        
        if not all([url, db, username, password]):
            self.print_fail("Missing Odoo credentials in .env")
            return
        
        # Test 1: Basic URL reachability
        try:
            response = requests.get(url, timeout=5)
            self.print_pass(f"URL reachable (Status: {response.status_code})")
        except requests.exceptions.ConnectionError:
            self.print_fail(f"Cannot reach {url} - Check URL or internet connection")
            return
        except Exception as e:
            self.print_warning(f"URL check warning: {str(e)}")
        
        # Test 2: XML-RPC endpoint
        try:
            common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
            version = common.version()
            self.print_pass(f"XML-RPC endpoint working - Odoo {version.get('server_version', 'unknown')}")
        except Exception as e:
            self.print_fail(f"XML-RPC endpoint failed: {str(e)}")
            
            # Suggest fix for Odoo Online
            if 'odoo.com' in url:
                self.print_warning("For Odoo Online (.odoo.com):")
                self.print_warning("  1. Log into Odoo as admin")
                self.print_warning("  2. Go to Settings → Users → Your User")
                self.print_warning("  3. Click 'Action' → 'Change Password' to set a password")
                self.print_warning("  4. Or generate an API key from 'Account Security' tab")
            return
        
        # Test 3: Authentication
        try:
            uid = common.authenticate(db, username, password, {})
            if uid:
                self.print_pass(f"Authentication successful! User ID: {uid}")
                
                # Test 4: Model access
                models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
                try:
                    partner_count = models.execute_kw(db, uid, password, 'res.partner', 'search_count', [[]])
                    self.print_pass(f"Model access working - Found {partner_count} partners")
                except Exception as e:
                    self.print_warning(f"Model access warning: {str(e)}")
            else:
                self.print_fail("Authentication failed - Wrong username or password")
                self.print_warning("Try resetting password or generating API key")
        except Exception as e:
            self.print_fail(f"Authentication error: {str(e)}")
    
    def check_project_files(self):
        self.print_header("Checking Project Files")
        
        # Backend files
        backend_files = ['main.py', 'odoo_integration.py', 'document_scanner.py']
        for file in backend_files:
            path = os.path.join(self.backend_dir, file)
            if os.path.exists(path):
                size = os.path.getsize(path)
                self.print_pass(f"{file} exists ({size} bytes)")
            else:
                self.print_fail(f"{file} missing!")
        
        # Frontend files
        if os.path.exists(self.frontend_dir):
            frontend_files = ['index.html', 'script.js', 'style.css']
            for file in frontend_files:
                path = os.path.join(self.frontend_dir, file)
                if os.path.exists(path):
                    size = os.path.getsize(path)
                    self.print_pass(f"frontend/{file} exists ({size} bytes)")
                else:
                    self.print_warning(f"frontend/{file} missing")
        else:
            self.print_warning("Frontend directory not found")
    
    def check_port_availability(self):
        self.print_header("Checking Ports")
        
        # Check if Flask is running
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5000))
        if result == 0:
            self.print_pass("Flask backend is running on port 5000")
        else:
            self.print_warning("Flask backend not running on port 5000")
            self.print_warning("  Start with: cd backend && python main.py")
        sock.close()
    
    def check_network(self):
        self.print_header("Network Diagnostics")
        
        # Check internet connection
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self.print_pass("Internet connection working")
        except OSError:
            self.print_fail("No internet connection")
            return
        
        # Check DNS resolution for Odoo
        try:
            from urllib.parse import urlparse
            env_vars = self.load_env_vars()
            if env_vars and 'ODOO_URL' in env_vars:
                domain = urlparse(env_vars['ODOO_URL']).netloc
                ip = socket.gethostbyname(domain)
                self.print_pass(f"DNS resolution for {domain}: {ip}")
        except Exception as e:
            self.print_warning(f"DNS resolution failed: {str(e)}")
    
    def load_env_vars(self):
        env_path = os.path.join(self.backend_dir, '.env')
        env_vars = {}
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_vars[key] = value
        return env_vars
    
    def print_summary(self):
        self.print_header("DIAGNOSTIC SUMMARY")
        
        print(f"\nTotal Checks: {len(self.passed) + len(self.warnings) + len(self.issues)}")
        print(f"✅ Passed: {len(self.passed)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Issues: {len(self.issues)}")
        
        if self.issues:
            print("\n🔴 CRITICAL ISSUES TO FIX:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        
        if self.warnings:
            print("\n🟡 WARNINGS TO CHECK:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if not self.issues:
            print("\n🎉 No critical issues found! Your project should work!")
            if self.warnings:
                print("   Check warnings for potential improvements.")
    
    def run_diagnostics(self):
        print("\n" + "="*60)
        print("🏥 PROJECT DOCTOR - COMPLETE DIAGNOSTIC")
        print("="*60)
        print(f"Project Root: {self.project_root}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.check_python_environment()
        env_vars = self.check_env_file()
        self.check_project_files()
        self.check_port_availability()
        self.check_network()
        
        if env_vars:
            self.test_odoo_connection(env_vars)
        
        self.print_summary()
        
        # Save report
        report_file = f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(f"Diagnostic Report - {datetime.now()}\n")
            f.write(f"Passed: {len(self.passed)}\n")
            f.write(f"Warnings: {len(self.warnings)}\n")
            f.write(f"Issues: {len(self.issues)}\n\n")
            if self.issues:
                f.write("CRITICAL ISSUES:\n")
                for issue in self.issues:
                    f.write(f"- {issue}\n")
        
        print(f"\n📝 Report saved to: {report_file}")

if __name__ == "__main__":
    doctor = ProjectDoctor()
    doctor.run_diagnostics()