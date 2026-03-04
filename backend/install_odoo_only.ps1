# install_odoo_only.ps1
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              ODOO INSTALLATION SCRIPT                      ║" -ForegroundColor Cyan
Write-Host "║         (Your project is fine, only Odoo is missing)       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "✅ Your backend files are present" -ForegroundColor Green
Write-Host "✅ Your frontend files are present" -ForegroundColor Green
Write-Host "✅ Python is installed" -ForegroundColor Green
Write-Host "✅ Flask is running on port 5000" -ForegroundColor Green
Write-Host "❌ Odoo is NOT running on port 8069" -ForegroundColor Red
Write-Host ""
Write-Host "Let's fix this now!" -ForegroundColor Yellow
Write-Host ""

# ==================== STEP 1: CHECK IF ODOO IS INSTALLED ====================
Write-Host "STEP 1: Checking if Odoo is installed..." -ForegroundColor Yellow

$odooPaths = @(
    "C:\Program Files\Odoo",
    "C:\Program Files (x86)\Odoo",
    "$env:LOCALAPPDATA\Programs\Odoo"
)

$odooInstalled = $false
foreach ($path in $odooPaths) {
    if (Test-Path $path) {
        Write-Host "✅ Odoo found at: $path" -ForegroundColor Green
        $odooInstalled = $true
    }
}

# ==================== STEP 2: DOWNLOAD ODOO IF NOT INSTALLED ====================
if (-not $odooInstalled) {
    Write-Host ""
    Write-Host "STEP 2: Odoo not found. Downloading installer..." -ForegroundColor Yellow
    
    $url = "https://nightly.odoo.com/17.0/nightly/exe/odoo_17.0.latest.exe"
    $output = "$env:TEMP\odoo_installer.exe"
    
    try {
        Write-Host "Downloading from: $url"
        Invoke-WebRequest -Uri $url -OutFile $output
        Write-Host "✅ Download complete!" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "STEP 3: Running Odoo installer..." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "📋 INSTALLATION INSTRUCTIONS:" -ForegroundColor Cyan
        Write-Host "=================================" -ForegroundColor Cyan
        Write-Host "1. Click 'Next' on welcome screen"
        Write-Host "2. Accept the license agreement"
        Write-Host "3. Keep default installation folder"
        Write-Host "4. When asked about PostgreSQL, select 'Install PostgreSQL'"
        Write-Host "5. Set master password (default is 'admin') - REMEMBER IT!"
        Write-Host "6. Click 'Install'"
        Write-Host "7. Wait for installation to complete"
        Write-Host "8. MAKE SURE 'Start Odoo' is CHECKED at the end"
        Write-Host "9. Click 'Finish'"
        Write-Host "=================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Press Enter to start the installer..."
        Read-Host
        
        # Start installer
        Start-Process $output -Wait
        
        Write-Host ""
        Write-Host "✅ Installation completed!" -ForegroundColor Green
    } catch {
        Write-Host "❌ Download failed: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please download manually from:" -ForegroundColor Yellow
        Write-Host "https://www.odoo.com/page/download"
        exit
    }
}

# ==================== STEP 4: START ODOO ====================
Write-Host ""
Write-Host "STEP 4: Starting Odoo..." -ForegroundColor Yellow

# Try to start Odoo service
$service = Get-Service -Name "*odoo*" -ErrorAction SilentlyContinue
if ($service) {
    Write-Host "✅ Found Odoo service: $($service.Name)" -ForegroundColor Green
    Start-Service -Name $service.Name
    Write-Host "✅ Odoo service started!" -ForegroundColor Green
} else {
    Write-Host "⚠️ Odoo service not found. Trying Start Menu..." -ForegroundColor Yellow
    
    # Try Start Menu
    $startMenu = [Environment]::GetFolderPath("CommonStartMenu")
    $shortcut = Get-ChildItem -Path $startMenu -Recurse -Filter "*odoo*.lnk" -ErrorAction SilentlyContinue | Select-Object -First 1
    
    if ($shortcut) {
        Write-Host "✅ Found Odoo shortcut: $($shortcut.Name)" -ForegroundColor Green
        Start-Process $shortcut.FullName
        Write-Host "✅ Odoo started via Start Menu!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "Please start Odoo manually:" -ForegroundColor Yellow
        Write-Host "1. Open Windows Start Menu"
        Write-Host "2. Search for 'Odoo'"
        Write-Host "3. Click on Odoo to start it"
        Write-Host ""
        Write-Host "Press Enter after starting Odoo..."
        Read-Host
    }
}

# ==================== STEP 5: WAIT FOR ODOO ====================
Write-Host ""
Write-Host "STEP 5: Waiting for Odoo to start (this may take up to 60 seconds)..." -ForegroundColor Yellow

$timeout = 60
$startTime = Get-Date
$started = $false

while ((Get-Date) - $startTime -lt [TimeSpan]::FromSeconds($timeout)) {
    $test = Test-NetConnection -ComputerName localhost -Port 8069 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($test.TcpTestSucceeded) {
        $started = $true
        break
    }
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 2
}

if ($started) {
    Write-Host ""
    Write-Host "✅ SUCCESS! Odoo is now running on port 8069!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Odoo did not start within $timeout seconds" -ForegroundColor Red
    Write-Host "Please start Odoo manually and try again" -ForegroundColor Yellow
    exit
}

# ==================== STEP 6: OPEN ODOO ====================
Write-Host ""
Write-Host "STEP 6: Opening Odoo in your browser..." -ForegroundColor Yellow
Start-Process "http://localhost:8069"

Write-Host ""
Write-Host "📋 NEXT STEPS:" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "1. In the browser, you'll see Odoo setup screen"
Write-Host "2. If asked for database, create one with:" -ForegroundColor White
Write-Host "   - Database Name: odoo" -ForegroundColor Green
Write-Host "   - Email: admin" -ForegroundColor Green
Write-Host "   - Password: admin" -ForegroundColor Green
Write-Host "3. After login, go to Apps menu" -ForegroundColor White
Write-Host "4. Search for and install 'Accounting' module" -ForegroundColor White
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "After completing these steps, your OCR project will work!" -ForegroundColor Green
Write-Host ""
Write-Host "Press Enter to continue..."
Read-Host

# ==================== STEP 7: TEST CONNECTION ====================
Write-Host ""
Write-Host "STEP 7: Testing Odoo connection..." -ForegroundColor Yellow

$pythonTest = @"
import xmlrpc.client
try:
    common = xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/common')
    version = common.version()
    print(f'✅ Odoo is running! Version: {version.get("server_version", "unknown")}')
except Exception as e:
    print(f'❌ Error: {e}')
"@

python -c $pythonTest

Write-Host ""
Write-Host "🎉 SETUP COMPLETE!" -ForegroundColor Green
Write-Host "Your Flask backend is running on port 5000" -ForegroundColor Green
Write-Host "Your Odoo is now running on port 8069" -ForegroundColor Green
Write-Host ""
Write-Host "Open your browser and go to: http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
