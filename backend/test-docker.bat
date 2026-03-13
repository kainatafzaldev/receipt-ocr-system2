@echo off
echo =========================================
echo 🐳 Docker Setup Test Suite
echo =========================================
echo.

set TESTS_PASSED=0
set TESTS_FAILED=0
set TESTS_TOTAL=0

echo 📋 Testing Docker Installation...
echo -----------------------------------------

:: Test 1: Check if Docker is installed
echo | set /p="Checking Docker installation... "
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('docker --version') do set DOCKER_VERSION=%%i
    echo ✅ Found: %DOCKER_VERSION%
    set /a TESTS_PASSED+=1
) else (
    echo ❌ Docker not found
    set /a TESTS_FAILED+=1
)
set /a TESTS_TOTAL+=1

:: Test 2: Check if Docker is running
echo | set /p="Checking Docker daemon... "
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Docker is running
    set /a TESTS_PASSED+=1
) else (
    echo ❌ Docker daemon is not running
    set /a TESTS_FAILED+=1
)
set /a TESTS_TOTAL+=1

:: Test 3: Check if Docker Compose is installed
echo | set /p="Checking Docker Compose... "
docker-compose --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('docker-compose --version') do set COMPOSE_VERSION=%%i
    echo ✅ Found: %COMPOSE_VERSION%
    set /a TESTS_PASSED+=1
) else (
    echo ❌ Docker Compose not found
    set /a TESTS_FAILED+=1
)
set /a TESTS_TOTAL+=1

echo.
echo 📦 Testing Docker Files...
echo -----------------------------------------

:: Test 4: Check if Dockerfile exists
echo | set /p="Checking Dockerfile... "
if exist "Dockerfile" (
    echo ✅ Found
    set /a TESTS_PASSED+=1
) else (
    echo ❌ Dockerfile not found
    set /a TESTS_FAILED+=1
)
set /a TESTS_TOTAL+=1

:: Test 5: Check if docker-compose.yml exists
echo | set /p="Checking docker-compose.yml... "
if exist "docker-compose.yml" (
    echo ✅ Found
    set /a TESTS_PASSED+=1
) else (
    echo ❌ docker-compose.yml not found
    set /a TESTS_FAILED+=1
)
set /a TESTS_TOTAL+=1

:: Test 6: Check if .dockerignore exists
echo | set /p="Checking .dockerignore... "
if exist ".dockerignore" (
    echo ✅ Found
    set /a TESTS_PASSED+=1
) else (
    echo ⚠️  Warning: .dockerignore not found (recommended)
    set /a TESTS_PASSED+=1
)
set /a TESTS_TOTAL+=1

echo.
echo 🔧 Testing Docker Build...
echo -----------------------------------------

:: Test 7: Try to build the Docker image
echo Attempting to build Docker image (this may take a moment)...
docker build -t ocr-test-temp . > docker-build.log 2>&1
if %errorlevel% equ 0 (
    echo ✅ Docker build successful
    set /a TESTS_PASSED+=1
    docker rmi ocr-test-temp >nul 2>&1
) else (
    echo ❌ Docker build failed. Check docker-build.log for details
    set /a TESTS_FAILED+=1
)
set /a TESTS_TOTAL+=1

echo.
echo 🌐 Testing Docker Configuration...
echo -----------------------------------------

:: Test 8: Check docker-compose syntax
echo Validating docker-compose.yml...
docker-compose config > docker-compose-check.log 2>&1
if %errorlevel% equ 0 (
    echo ✅ docker-compose.yml syntax is valid
    set /a TESTS_PASSED+=1
) else (
    echo ❌ docker-compose.yml has syntax errors. Check docker-compose-check.log
    set /a TESTS_FAILED+=1
)
set /a TESTS_TOTAL+=1

echo.
echo 📊 Test Summary
echo -----------------------------------------
echo ✅ Passed: %TESTS_PASSED%
echo ❌ Failed: %TESTS_FAILED%
echo 📋 Total: %TESTS_TOTAL%

if %TESTS_FAILED% equ 0 (
    echo.
    echo 🎉 All tests passed! Your Docker setup looks good!
    echo.
    echo Next steps:
    echo 1. Start your containers: docker-compose up
    echo 2. Check if your OCR backend is running: curl http://localhost:5000/health
    echo 3. Open your frontend in browser
) else (
    echo.
    echo ❌ Some tests failed. Please check the issues above.
)

echo =========================================
pause