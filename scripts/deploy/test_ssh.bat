@echo off
REM SSH Connection Test Script

setlocal enabledelayedexpansion

set SERVER_IP=8.163.37.124
set SERVER_USER=novelapp
set KEY_FILE=d:\work6.05\xsdm.pem

echo ========================================
echo   SSH Connection Test
echo ========================================
echo.

echo Checking SSH key file...
if not exist "%KEY_FILE%" (
    echo [ERROR] SSH key file not found: %KEY_FILE%
    echo.
    echo Please check:
    echo 1. Is the key file in the correct location?
    echo 2. Did you rename it correctly?
    pause
    exit /b 1
)

echo [OK] Key file found: %KEY_FILE%
echo.

echo Testing SSH connection...
echo.

ssh -i "%KEY_FILE%" -o StrictHostKeyChecking=no -o ConnectTimeout=10 %SERVER_USER%@%SERVER_IP% "echo 'SSH connection successful!' && echo 'Current user:' && whoami && echo 'Current directory:' && pwd"

if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo SSH CONNECTION FAILED
    echo ========================================
    echo.
    echo Possible issues:
    echo.
    echo 1. Key file permissions
    echo    - On Windows: Right-click key file ^> Properties ^> Security
    echo    - Ensure your user has read access
    echo.
    echo 2. Server-side SSH configuration
    echo    - Key may not be added to server's authorized_keys
    echo    - SSH service may not be running
    echo    - User may not exist on server
    echo.
    echo 3. Key format issue
    echo    - Ensure key is in OpenSSH format
    echo    - Try converting with: ssh-keygen -p -f xsdm.pem
    echo.
    echo 4. Network/firewall issue
    echo    - Check if server is reachable
    echo    - Check firewall rules
    echo.
    echo Troubleshooting steps:
    echo.
    echo Step 1: Test basic connectivity
    echo   ping %SERVER_IP%
    echo.
    echo Step 2: Test SSH with verbose output
    echo   ssh -v -i "%KEY_FILE%" %SERVER_USER%@%SERVER_IP%
    echo.
    echo Step 3: Check server logs
    echo   ssh as root and check: /var/log/auth.log
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo SSH CONNECTION SUCCESSFUL!
echo ========================================
echo.
echo You can proceed with deployment.
echo.
pause