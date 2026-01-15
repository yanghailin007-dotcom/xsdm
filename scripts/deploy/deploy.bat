@echo off
chcp 65001 >nul
echo ========================================
echo    完整自动部署工具 - 上传、部署、运行、测试
echo ========================================
echo.
 
REM 服务器配置
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem
 
echo 服务器信息:
echo   IP: %SERVER_IP%
echo   用户: %SERVER_USER%
echo   密钥: %KEY_PATH%
echo.
 
REM 检查私钥
if not exist "%KEY_PATH%" (
    echo 错误: 私钥文件未找到: %KEY_PATH%
    pause
    exit /b 1
)
 
REM 设置权限
echo 正在设置私钥权限...
icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

REM 测试连接
echo 正在测试SSH连接...
ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "echo 'Connection successful'" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo 错误: SSH连接失败
    pause
    exit /b 1
)
echo SSH连接成功
echo.
 
REM 检查Git Bash
set GIT_BASH="C:\Program Files\Git\bin\bash.exe"
if not exist %GIT_BASH% (
    echo 错误: Git Bash未找到
    pause
    exit /b 1
)
 
REM ========================================
REM 步骤 1: 创建部署压缩包
REM ========================================
echo ========================================
echo 步骤 1/5: 创建部署压缩包
echo ========================================
echo.

set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set ZIP_FILE=novel_system_%TIMESTAMP%.tar.gz

cd /d d:\work6.05
echo 正在创建压缩包: %ZIP_FILE%
%GIT_BASH% -c "tar -czf %ZIP_FILE% --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='logs' --exclude='generated_images' --exclude='aiwx_video_generations' --exclude='veo_video_generations' --exclude='video_generations' --exclude='temp_fanqie_upload' --exclude='temp_uploads' --exclude='chapter_failures' --exclude='Chrome' --exclude='视频项目' --exclude='*.tar.gz' --exclude='.env' --exclude='test_*.py' --exclude='test_*.json' --exclude='phase_one_test_report_*.json' --exclude='xsdm.pem' --exclude='*.log' --exclude='output.*' --exclude='server.log' --exclude='ai_parsed_result.json' --exclude='exported_background.json' --exclude='发布进度*.json' --exclude='文件整理*.json' --exclude='材料整理*.json' ."

if not exist %ZIP_FILE% (
    echo 错误: 压缩包创建失败
    pause
    exit /b 1
)
 
echo 压缩包创建成功: %ZIP_FILE%
for %%F in (%ZIP_FILE%) do echo 大小: %%~zF 字节
echo.

REM ========================================
REM 步骤 2: 上传压缩包到服务器
REM ========================================
echo ========================================
echo 步骤 2/5: 上传压缩包到服务器
echo ========================================
echo.

echo 正在上传 %ZIP_FILE% 到服务器...
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no %ZIP_FILE% %SERVER_USER%@%SERVER_IP%:/tmp/

if %ERRORLEVEL% neq 0 (
    echo 错误: 上传失败
    del %ZIP_FILE%
    pause
    exit /b 1
)
 
echo 上传成功
echo.

REM 删除本地压缩包
del %ZIP_FILE%

REM ========================================
REM 步骤 3: 上传部署脚本到服务器
REM ========================================
echo ========================================
echo 步骤 3/5: 上传部署脚本到服务器
echo ========================================
echo.

echo 正在上传部署脚本...
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no "%~dp0server_deploy.sh" %SERVER_USER%@%SERVER_IP%:/tmp/deploy_script.sh

if %ERRORLEVEL% neq 0 (
    echo 错误: 部署脚本上传失败
    pause
    exit /b 1
)

echo 部署脚本上传成功
echo.

REM ========================================
REM 步骤 4: 执行部署并启动服务
REM ========================================
echo ========================================
echo 步骤 4/5: 执行部署并启动服务
echo ========================================
echo.

echo 正在部署应用并启动服务...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "chmod +x /tmp/deploy_script.sh && bash /tmp/deploy_script.sh"

set DEPLOY_RESULT=%ERRORLEVEL%

echo.

REM ========================================
REM 步骤 5: 测试应用访问
REM ========================================
echo ========================================
echo 步骤 5/5: 测试应用访问
echo ========================================
echo.

if %DEPLOY_RESULT% equ 0 (
    echo 正在测试应用访问...
    echo.
    
    REM 获取服务器IP
    for /f "tokens=*" %%i in ('ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "hostname -I"') do set SERVER_IP_RESULT=%%i
    for /f "tokens=1" %%a in ("%SERVER_IP_RESULT%") do set ACTUAL_IP=%%a
    
    echo 服务器IP: %ACTUAL_IP%
    echo.
    
    REM 测试HTTP访问
    echo 正在测试 HTTP 连接...
    ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "curl -s -o /dev/null -w 'HTTP状态码: %%{http_code}\n' http://127.0.0.1:5000/"
    
    if %ERRORLEVEL% equ 0 (
        echo.
        echo ========================================
        echo   ✓ 所有步骤完成！
        echo ========================================
        echo.
        echo 部署成功！应用已启动并运行。
        echo.
        echo 访问地址:
        echo   本地测试: http://127.0.0.1:5000/
        echo   外网访问: http://%ACTUAL_IP%:5000/
        echo.
        echo 服务管理命令:
        echo   查看状态: ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP% "pgrep -f gunicorn"
        echo   停止服务: ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP% "pkill -f gunicorn"
        echo   查看日志: ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP% "tail -f /home/novelapp/novel-system/logs/error.log"
        echo.
        echo 连接到服务器:
        echo   ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
        echo.
    ) else (
        echo.
        echo ========================================
        echo   ⚠ 部署完成但应用测试失败
        echo ========================================
        echo.
        echo 请检查应用日志:
        echo   ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP% "tail -50 /home/novelapp/novel-system/logs/error.log"
        echo.
    )
) else (
    echo ========================================
    echo   ✗ 部署失败
    echo ========================================
    echo.
    echo 请检查:
    echo 1. 服务器连接
    echo 2. 磁盘空间
    echo 3. Python安装
    echo 4. 应用代码完整性
    echo.
    echo 连接到服务器查看详情:
    echo   ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
    echo.
    echo 查看部署日志:
    echo   ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP% "cat /tmp/deploy_script.sh"
    echo.
)

REM 清理临时文件
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "rm -f /tmp/deploy_script.sh" 2>nul

echo.
pause
