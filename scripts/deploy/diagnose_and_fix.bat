@echo off
chcp 65001 >nul
echo ========================================
echo    部署诊断和修复工具
echo ========================================
echo.

REM 服务器配置
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

echo ========================================
echo    步骤 1: 检查服务器状态
echo ========================================
echo.

echo 检查SSH连接...
ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "echo '✓ 连接成功'"
if %ERRORLEVEL% neq 0 (
    echo ❌ SSH连接失败
    pause
    exit /b 1
)

echo.
echo 检查项目目录...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "ls -ld /home/novelapp/novel-system 2>/dev/null && echo '✓ 项目目录存在' || echo '❌ 项目目录不存在'"

echo.
echo 检查虚拟环境...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "test -d /home/novelapp/novel-system/venv && echo '✓ 虚拟环境存在' || echo '❌ 虚拟环境不存在'"

echo.
echo 检查日志目录...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "test -d /home/novelapp/novel-system/logs && echo '✓ 日志目录存在' || echo '❌ 日志目录不存在'"

echo.
echo 检查服务状态...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "lsof -ti:5000 >/dev/null 2>&1 && echo '✓ 服务运行中 (端口5000)' || echo '❌ 服务未运行'"

echo.
echo ========================================
echo    步骤 2: 执行修复
echo ========================================
echo.

echo 上传修复脚本...
scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no scripts/deploy/init_logs_on_server.sh %SERVER_USER%@%SERVER_IP%:/tmp/

echo 执行修复...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash /tmp/init_logs_on_server.sh"

echo.
echo ========================================
echo    步骤 3: 验证修复
echo ========================================
echo.

echo 检查日志文件...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "ls -lh /home/novelapp/novel-system/logs/"

echo.
echo ========================================
echo    ✓ 诊断和修复完成！
echo ========================================
echo.
echo 下一步操作：
echo.
echo 1. 如果是首次部署，运行：
echo    scripts/deploy/一键部署_with_logs.bat
echo.
echo 2. 如果只是更新代码，运行：
echo    scripts/deploy/quick_restart_with_logs.bat
echo.
echo 3. 如果需要查看服务器日志：
echo    scripts/deploy/view_server_logs.bat
echo.

pause