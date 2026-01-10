@echo off
REM Windows智能部署脚本 - 快速同步必要代码

setlocal enabledelayedexpansion

REM 配置变量
set SERVER_IP=8.163.37.124
set SERVER_USER=novelapp
set SERVER_PATH=/home/novelapp/novel-system
set LOCAL_PATH=d:/work6.05
set KEY_FILE=d:/work6.05/xsdm.pem

echo ========================================
echo   智能部署脚本 - 快速同步必要代码
echo ========================================
echo.

REM 检查rsync是否安装
where rsync >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 rsync 命令
    echo.
    echo 请先安装 rsync:
    echo 方式1: 使用 Chocolatey: choco install rsync
    echo 方式2: 下载 cwRsync: https://itefix.net/cwrsync
    echo.
    pause
    exit /b 1
)

echo 将要同步的目录:
echo   + src/        - 核心代码
echo   + web/        - Web界面
echo   + config/     - 配置文件
echo   + scripts/    - 脚本工具
echo   + requirements.txt - 依赖列表
echo.
echo 排除的内容 (不同步):
echo   - Chrome/     - 浏览器自动化 (1.6GB)
echo   - .git/       - Git历史 (605MB)
echo   - .venv/      - 虚拟环境 (15MB)
echo   - generated_images/ - 生成的图片 (39MB)
echo   - 小说项目/    - 本地项目数据
echo   - logs/       - 日志文件
echo   - temp_fanqie_upload/ - 临时文件
echo   - __pycache__/ - Python缓存
echo   - *.pyc       - 编译文件
echo.
set /p confirm="确认开始同步? (y/n): "
if /i not "%confirm%"=="y" (
    echo 取消部署
    pause
    exit /b 0
)

echo.
echo 开始同步...
echo.

REM 使用rsync同步，只传输必要的文件
rsync -avz --progress ^
    --exclude="Chrome/" ^
    --exclude=".git/" ^
    --exclude=".venv/" ^
    --exclude="venv/" ^
    --exclude="generated_images/" ^
    --exclude="logs/" ^
    --exclude="temp_fanqie_upload/" ^
    --exclude="chapter_failures/" ^
    --exclude="__pycache__/" ^
    --exclude="*.pyc" ^
    --exclude="*.pyo" ^
    --exclude=".env" ^
    --exclude="*.db" ^
    --exclude="小说项目/" ^
    --exclude="test_*.py" ^
    --exclude="check_*.py" ^
    --exclude="diagnose_*.py" ^
    --exclude="debug_*.py" ^
    --exclude="*.tar.gz" ^
    --exclude=".vscode/" ^
    --exclude=".idea/" ^
    --exclude="node_modules/" ^
    --exclude="data/users.db" ^
    --exclude="*.log" ^
    --exclude=".claude/" ^
    --exclude="*.pem" ^
    --exclude="*.key" ^
    --exclude="id_rsa*" ^
    --exclude="Chrome.rar" ^
    --delete ^
    -e "ssh -i %KEY_FILE% -o StrictHostKeyChecking=no" ^
    "%LOCAL_PATH%/" ^
    "%SERVER_USER%@%SERVER_IP%:%SERVER_PATH%/"

if %errorlevel% equ 0 (
    echo.
    echo [成功] 同步完成！
    echo ========================================
    echo.
    echo 下一步操作:
    echo 1. SSH连接到服务器:
    echo    ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP%
    echo.
    echo 2. 进入项目目录:
    echo    cd %SERVER_PATH%
    echo.
    echo 3. 创建虚拟环境并安装依赖:
    echo    python3 -m venv venv
    echo    source venv/bin/activate
    echo    pip install -r requirements.txt
    echo.
    echo 4. 配置环境变量:
    echo    cp .env.example .env
    echo    vim .env
    echo.
    echo 5. 重启服务:
    echo    sudo supervisorctl restart novel-system
    echo.
) else (
    echo.
    echo [错误] 同步失败，请检查错误信息
    pause
    exit /b 1
)

pause