@echo off
chcp 65001 >nul
echo ========================================
echo    小说生成系统 - 代码上传工具
echo ========================================
echo.

REM 检查是否安装了SCP
where scp >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到SCP命令
    echo 请安装Git for Windows或OpenSSH客户端
    echo 下载地址: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM 获取服务器信息
set /p SERVER_IP="请输入服务器IP地址: "
set /p SERVER_USER="请输入服务器用户名 (默认: novelapp): "
if "%SERVER_USER%"=="" set SERVER_USER=novelapp

echo.
echo 服务器IP: %SERVER_IP%
echo 用户名: %SERVER_USER%
echo.

REM 选择上传方式
echo 请选择上传方式:
echo 1. 使用SCP上传整个项目目录
echo 2. 使用SCP上传压缩包
echo 3. 手动输入上传命令
echo.
set /p UPLOAD_TYPE="请输入选项 (1-3): "

if "%UPLOAD_TYPE%"=="1" goto upload_direct
if "%UPLOAD_TYPE%"=="2" goto upload_zip
if "%UPLOAD_TYPE%"=="3" goto manual_upload

:upload_direct
echo.
echo 正在上传项目文件到服务器...
echo 这可能需要几分钟，请耐心等待...
echo.

REM 创建远程目录
scp -r ^
  --exclude='__pycache__' ^
  --exclude='*.pyc' ^
  --exclude='.git' ^
  --exclude='logs/*' ^
  --exclude='generated_images/*' ^
  --exclude='temp_fanqie_upload/*' ^
  --exclude='.env' ^
  --exclude='test_*.py' ^
  --exclude='*.db' ^
  . %SERVER_USER%@%SERVER_IP%:/home/%SERVER_USER%/novel-system

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo ✓ 上传成功！
    echo ========================================
    echo.
    echo 接下来的步骤:
    echo 1. SSH登录服务器: ssh %SERVER_USER%@%SERVER_IP%
    echo 2. 进入项目目录: cd ~/novel-system
    echo 3. 运行部署脚本: bash scripts/deploy/deploy_app.sh
    echo.
) else (
    echo.
    echo ✗ 上传失败，请检查网络连接和服务器信息
)
pause
exit /b 0

:upload_zip
echo.
echo 正在创建压缩包...
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set ZIP_FILE=novel_system_%TIMESTAMP%.tar.gz

REM 使用Git Bash创建tar.gz
"C:\Program Files\Git\bin\bash.exe" -c "tar -czf %ZIP_FILE% --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='logs/*' --exclude='generated_images/*' --exclude='temp_fanqie_upload/*' --exclude='.env' --exclude='test_*.py' --exclude='*.db' ."

if not exist %ZIP_FILE% (
    echo ✗ 压缩包创建失败
    pause
    exit /b 1
)

echo.
echo 正在上传压缩包到服务器...
scp %ZIP_FILE% %SERVER_USER%@%SERVER_IP%:/home/%SERVER_USER%/

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✓ 压缩包上传成功！
    echo.
    echo 请在服务器上执行以下命令解压:
    echo ssh %SERVER_USER%@%SERVER_IP%
    echo cd ~
    echo mkdir -p novel-system
    echo tar -xzf %ZIP_FILE% -C novel-system
    echo rm %ZIP_FILE%
    echo cd novel-system
    echo bash scripts/deploy/deploy_app.sh
    echo.
    
    REM 删除本地压缩包
    del %ZIP_FILE%
) else (
    echo ✗ 上传失败
    del %ZIP_FILE%
)
pause
exit /b 0

:manual_upload
echo.
echo 请手动执行以下命令上传代码:
echo.
echo 方法1 - 直接上传:
echo scp -r --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' . %SERVER_USER%@%SERVER_IP%:/home/%SERVER_USER%/novel-system
echo.
echo 方法2 - 压缩后上传:
echo tar -czf novel_system.tar.gz --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' .
echo scp novel_system.tar.gz %SERVER_USER%@%SERVER_IP%:/home/%SERVER_USER%/
echo.
pause
exit /b 0