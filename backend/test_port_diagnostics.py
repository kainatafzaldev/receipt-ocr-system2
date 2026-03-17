"""
=====================================================
  PORT DIAGNOSTIC TEST - Railway / Flask Deployment
  Run this file to find port/host issues
=====================================================
"""

import os
import sys
import socket
import subprocess

# ─────────────────────────────────────────────
# ANSI Colors for terminal output
# ─────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"  {GREEN}✅ PASS{RESET}  {msg}")
def fail(msg):  print(f"  {RED}❌ FAIL{RESET}  {msg}")
def warn(msg):  print(f"  {YELLOW}⚠️  WARN{RESET}  {msg}")
def info(msg):  print(f"  {CYAN}ℹ️  INFO{RESET}  {msg}")
def header(msg):print(f"\n{BOLD}{CYAN}{'─'*55}\n  {msg}\n{'─'*55}{RESET}")

issues_found = []

# ─────────────────────────────────────────────
# TEST 1: Check PORT environment variable
# ─────────────────────────────────────────────
header("TEST 1: PORT Environment Variable")

port_env = os.environ.get("PORT")
if port_env:
    ok(f"PORT env variable exists → '{port_env}'")
    try:
        port_val = int(port_env)
        ok(f"PORT is a valid integer → {port_val}")
    except ValueError:
        fail(f"PORT value '{port_env}' is NOT a valid integer!")
        issues_found.append("PORT env variable is not a valid integer.")
else:
    warn("PORT env variable is NOT set. Will fall back to default.")
    info("Railway sets PORT automatically — make sure you read it with os.environ.get('PORT', 8080)")
    issues_found.append("PORT environment variable is missing. Use os.environ.get('PORT', 8080).")

# ─────────────────────────────────────────────
# TEST 2: Check HOST binding
# ─────────────────────────────────────────────
header("TEST 2: Host Binding Check")

RECOMMENDED_HOST = "0.0.0.0"
WRONG_HOST       = "127.0.0.1"

# Try to find main.py or app.py and check the run() call
source_files = []
for fname in ["main.py", "app.py", "server.py", "run.py"]:
    if os.path.exists(fname):
        source_files.append(fname)

if not source_files:
    warn("No main.py / app.py found in current directory.")
    info("Run this script from your project root folder.")
else:
    for fname in source_files:
        info(f"Scanning '{fname}' for host/port settings...")
        with open(fname, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines   = content.splitlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Check for wrong host
            if WRONG_HOST in stripped and "run(" in stripped:
                fail(f"Line {i}: Found hardcoded '{WRONG_HOST}' → will NOT work on Railway!")
                info(f"  → Change to: app.run(host='0.0.0.0', port=...)")
                issues_found.append(f"{fname} line {i}: host='127.0.0.1' blocks Railway access.")

            # Check for correct host
            if RECOMMENDED_HOST in stripped and "run(" in stripped:
                ok(f"Line {i}: Host is correctly set to '0.0.0.0'")

            # Check for hardcoded port
            if "run(" in stripped and ("8080" in stripped or "5000" in stripped or "3000" in stripped):
                if "os.environ" not in stripped and "PORT" not in stripped:
                    warn(f"Line {i}: Hardcoded port detected → '{stripped}'")
                    info("  → Change to: port=int(os.environ.get('PORT', 8080))")
                    issues_found.append(f"{fname} line {i}: Hardcoded port. Use os.environ.get('PORT', 8080).")

            # Check for debug=True in production
            if "debug=True" in stripped and "run(" in stripped:
                warn(f"Line {i}: debug=True is ON — disable in production!")
                issues_found.append(f"{fname} line {i}: debug=True should be False in production.")

# ─────────────────────────────────────────────
# TEST 3: Check if port is already in use
# ─────────────────────────────────────────────
header("TEST 3: Port Availability Check")

test_port = int(os.environ.get("PORT", 8080))
info(f"Testing if port {test_port} is available on 0.0.0.0 ...")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.bind(("0.0.0.0", test_port))
    ok(f"Port {test_port} is FREE and available to bind.")
    sock.close()
except OSError as e:
    fail(f"Port {test_port} is ALREADY IN USE or blocked!")
    info(f"  Error: {e}")
    issues_found.append(f"Port {test_port} is already in use. Kill the existing process.")

# ─────────────────────────────────────────────
# TEST 4: Check required environment variables
# ─────────────────────────────────────────────
header("TEST 4: Required Environment Variables")

required_vars = [
    "NOVITA_API_KEY",
    "ODOO_URL",
    "PORT",
]

optional_vars = [
    "ODOO_DB",
    "ODOO_USER",
    "ODOO_PASSWORD",
    "SECRET_KEY",
]

for var in required_vars:
    val = os.environ.get(var)
    if val:
        masked = val[:6] + "..." if len(val) > 6 else "***"
        ok(f"{var} → '{masked}'")
    else:
        fail(f"{var} is MISSING! Add it to Railway environment variables.")
        issues_found.append(f"Missing required env variable: {var}")

for var in optional_vars:
    val = os.environ.get(var)
    if val:
        ok(f"{var} → set ✓")
    else:
        warn(f"{var} → not set (optional)")

# ─────────────────────────────────────────────
# TEST 5: Flask / Gunicorn Check
# ─────────────────────────────────────────────
header("TEST 5: Flask & Gunicorn Installation")

try:
    import flask
    ok(f"Flask is installed → version {flask.__version__}")
except ImportError:
    fail("Flask is NOT installed! Run: pip install flask")
    issues_found.append("Flask not installed.")

try:
    result = subprocess.run(["gunicorn", "--version"], capture_output=True, text=True)
    ok(f"Gunicorn is installed → {result.stdout.strip()}")
except FileNotFoundError:
    warn("Gunicorn is NOT installed.")
    info("  → For production, run: pip install gunicorn")
    info("  → Start command:  gunicorn main:app --bind 0.0.0.0:$PORT --workers 2")
    issues_found.append("Gunicorn missing — recommended for Railway production deployments.")

# ─────────────────────────────────────────────
# TEST 6: Socket connectivity to Odoo
# ─────────────────────────────────────────────
header("TEST 6: Odoo URL Reachability")

odoo_url = os.environ.get("ODOO_URL", "")
if odoo_url:
    # Parse hostname from URL
    hostname = odoo_url.replace("https://", "").replace("http://", "").split("/")[0]
    info(f"Trying to reach Odoo host: {hostname} ...")
    try:
        ip = socket.gethostbyname(hostname)
        ok(f"DNS resolved → {hostname} = {ip}")
    except socket.gaierror as e:
        fail(f"Cannot resolve Odoo hostname '{hostname}'!")
        info(f"  Error: {e}")
        issues_found.append(f"Odoo URL '{hostname}' is unreachable. Check ODOO_URL env variable.")
else:
    warn("ODOO_URL is not set — skipping connectivity test.")

# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
header("SUMMARY")

if not issues_found:
    print(f"\n  {GREEN}{BOLD}🎉 All tests passed! No port issues found.{RESET}\n")
else:
    print(f"\n  {RED}{BOLD}Found {len(issues_found)} issue(s):{RESET}\n")
    for i, issue in enumerate(issues_found, 1):
        print(f"  {RED}{i}.{RESET} {issue}")

    print(f"""
{CYAN}─────────────────────────────────────────────────────
  QUICK FIX — update your app.run() to:
─────────────────────────────────────────────────────{RESET}

  import os
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port, debug=False)

{CYAN}  Or use Gunicorn (recommended for Railway):{RESET}

  gunicorn main:app --bind 0.0.0.0:$PORT --workers 2
""")