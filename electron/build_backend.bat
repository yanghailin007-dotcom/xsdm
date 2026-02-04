@echo off
chcp 65001 >nul
echo ========================================
echo 打包Flask后端为可执行文件
echo ========================================

REM 切换到项目根目录
cd /d "%~dp0.."

REM 激活虚拟环境
if exist ".venv\Scripts\activate.bat" (
    echo 使用虚拟环境...
    call .venv\Scripts\activate.bat
) else (
    echo 警告: 未找到虚拟环境，使用系统Python
)

REM 检查是否安装了pyinstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo 正在安装PyInstaller...
    pip install pyinstaller
)

echo.
echo 正在打包后端...
echo.

REM 切换到项目根目录
cd /d "%~dp0.."

REM 使用PyInstaller打包
pyinstaller --noconfirm ^
    --onefile ^
    --windowed ^
    --name app ^
    --add-data "web/templates;web/templates" ^
    --add-data "static;static" ^
    --add-data "config;config" ^
    --add-data "src;src" ^
    --hidden-import flask ^
    --hidden-import flask_cors ^
    --hidden-import werkzeug ^
    --hidden-import jinja2 ^
    --hidden-import PIL ^
    --hidden-import requests ^
    --collect-all flask ^
    --collect-all jinja2 ^
    web/app.py

REM 创建backend_dist目录并复制文件
if not exist "backend_dist" mkdir backend_dist
xcopy /E /I /Y "dist\app.exe" "backend_dist\"
xcopy /E /I /Y "web\templates" "backend_dist\web\templates\"
xcopy /E /I /Y "static" "backend_dist\static\"
xcopy /E /I /Y "config" "backend_dist\config\"
xcopy /E /I /Y "src" "backend_dist\src\"

echo.
echo ========================================
echo 打包完成！
echo 输出目录: backend_dist
echo ========================================
pause
