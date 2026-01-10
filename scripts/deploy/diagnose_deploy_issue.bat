@echo off
chcp 65001 >nul
echo ========================================
echo    部署问题诊断工具
echo ========================================
echo.

REM 检查必要工具
echo [1/5] 检查必要工具...
where ssh >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ❌ SSH 未安装
    echo 请安装 Git for Windows: https://git-scm.com/download/win
    pause
    exit /b 1
)
echo ✓ SSH 已安装

where scp >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ❌ SCP 未安装
    pause
    exit /b 1
)
echo ✓ SCP 已安装

REM 检查Git Bash
set GIT_BASH="C:\Program Files\Git\bin\bash.exe"
if not exist %GIT_BASH% (
    echo ❌ Git Bash 未找到
    echo 请安装 Git for Windows: https://git-scm.com/download/win
    pause
    exit /b 1
)
echo ✓ Git Bash 已安装

echo.
echo [2/5] 检查私钥文件...
set KEY_PATH=d:\work6.05\xsdm.pem
if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    echo.
    echo 请查找私钥文件，可能的位置：
    dir /s /b d:\*.pem 2>nul | findstr /i "xsdm key private"
    pause
    exit /b 1
)
echo ✓ 私钥文件存在: %KEY_PATH%

REM 检查私钥权限
echo.
echo [3/5] 检查私钥权限...
icacls "%KEY_PATH%" | findstr /i "%USERNAME%:(F)"
if %ERRORLEVEL% neq 0 (
    echo ⚠️ 权限可能不正确，正在修复...
    icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
    icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo ✓ 权限已修复
    ) else (
        echo ❌ 权限修复失败
        pause
        exit /b 1
    )
) else (
    echo ✓ 私钥权限正确
)

echo.
echo [4/5] 测试SSH连接...
set SERVER_IP=8.163.37.124
set SERVER_USER=root

ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "echo '连接成功'" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ SSH连接失败
    echo.
    echo 可能的原因：
    echo 1. 服务器IP错误: %SERVER_IP%
    echo 2. 用户名错误: %SERVER_USER%
    echo 3. 私钥不匹配
    echo 4. 防火墙阻止
    echo.
    echo 尝试详细连接测试...
    ssh -i "%KEY_PATH%" -v -o ConnectTimeout=10 %SERVER_USER%@%SERVER_IP% "echo 'test'" 2>&1 | findstr /i "connecting\|authenticat\|failed\|refused"
    pause
    exit /b 1
)
echo ✓ SSH连接成功

echo.
echo [5/5] 测试磁盘空间...
ssh -i "%KEY_PATH%" -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "df -h /tmp"
echo.

echo ========================================
echo    诊断完成
echo ========================================
echo.
echo 测试创建压缩包...
cd /d d:\work6.05
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set TEST_FILE=test_upload_%TIMESTAMP%.tar.gz

%GIT_BASH% -c "tar -czf %TEST_FILE% --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='logs/*' --exclude='generated_images/*' --exclude='temp_fanqie_upload/*' --exclude='.env' --exclude='test_*.py' --exclude='*.db' . >nul 2>&1"

if not exist %TEST_FILE% (
    echo ❌ 压缩包创建失败
    echo.
    echo 尝试查看详细错误...
    %GIT_BASH% -c "tar -czf %TEST_FILE% --exclude='__pycache__' --exclude='*.pyc' . 2>&1"
    pause
    exit /b 1
)
echo ✓ 压缩包创建成功

echo.
echo 测试上传...
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no %TEST_FILE% %SERVER_USER%@%SERVER_IP%:/tmp/ >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ 上传失败
    echo.
    echo 尝试详细上传...
    scp -i "%KEY_PATH%" -P 22 -v %TEST_FILE% %SERVER_USER%@%SERVER_IP%:/tmp/ 2>&1
    del %TEST_FILE%
    pause
    exit /b 1
)
echo ✓ 上传成功

REM 清理测试文件
del %TEST_FILE%
ssh -i "%KEY_PATH%" -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "rm -f /tmp/test_upload_*.tar.gz"

echo.
echo ========================================
echo    ✓ 所有测试通过！可以开始部署
echo ========================================
pause