@echo off
chcp 65001 >nul
echo ========================================
echo    快速重启服务器服务
echo ========================================
echo.

set SCRIPT_DIR=%~dp0
set CONFIG_FILE=%SCRIPT_DIR%deploy_config.ini

if not exist "%CONFIG_FILE%" (
    echo ❌ 配置文件不存在: %CONFIG_FILE%
    pause
    exit /b 1
)

REM 读取配置
set PYTHON_SCRIPT=%TEMP%\read_config.py
echo import configparser > "%PYTHON_SCRIPT%"
echo config = configparser.ConfigParser() >> "%PYTHON_SCRIPT%"
echo config.read(r'%CONFIG_FILE%') >> "%PYTHON_SCRIPT%"
echo print(config['server']['ip']) >> "%PYTHON_SCRIPT%"
echo print(config['server']['user']) >> "%PYTHON_SCRIPT%"
echo print(config['server']['key_path']) >> "%PYTHON_SCRIPT%"
echo print(config['server']['remote_project_path']) >> "%PYTHON_SCRIPT%"

for /f "tokens=1,2,3,4" %%a in ('python "%PYTHON_SCRIPT%"') do (
    set SERVER_IP=%%a
    set SERVER_USER=%%b
    set KEY_PATH=%%c
    set REMOTE_PATH=%%d
)

del "%PYTHON_SCRIPT%"

echo 服务器: %SERVER_IP%
echo.

REM 修复私钥权限
icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

echo 正在重启服务器服务...
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "cd %REMOTE_PATH% && bash scripts/deploy/server_deploy_stable.sh"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo    ✓ 服务重启成功！
    echo ========================================
    echo.
    echo 访问地址: http://%SERVER_IP%:5000
    echo.
) else (
    echo.
    echo ❌ 服务重启失败
    echo.
)

pause