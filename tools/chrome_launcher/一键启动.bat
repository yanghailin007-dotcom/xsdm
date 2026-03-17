@echo off
chcp 65001 >nul
title 大文娱 Chrome 启动器

:: 检查是否以管理员运行（某些系统需要）
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [管理员模式运行中...]
) else (
    echo [普通模式运行...]
)
echo.

echo ================================================
echo      欢迎使用大文娱 Chrome 启动器
echo ================================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Python已安装
    goto :run_python
)

:: 没有Python，检查是否有打包的exe
if exist "start_browser.exe" (
    echo [OK] 找到启动器程序
    goto :run_exe
)

:: 都没有，需要下载Python或提示
:eek:cho.
echo ================================================
echo [提示] 首次使用需要安装 Python
echo ================================================
echo.
echo 请选择：
echo.
echo [1] 自动下载并安装 Python（推荐，约 30MB）
echo [2] 我已经有 Python，重新检测
echo [3] 手动下载 Python 安装包
echo.
set /p choice="请输入选项 (1-3): "

if "%choice%"=="1" goto :download_python
if "%choice%"=="2" goto :check_python_again
if "%choice%"=="3" goto :manual_download

goto :end

:download_python
echo.
echo [1/3] 正在下载 Python 安装程序...
echo      下载地址: https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
curl -L -o python_installer.exe https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
if %errorLevel% neq 0 (
    echo [错误] 下载失败，请检查网络连接
    pause
    goto :end
)
echo [OK] 下载完成

echo.
echo [2/3] 正在安装 Python（可能需要几分钟）...
echo      请等待安装完成...
python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
if %errorLevel% neq 0 (
    echo [错误] 安装失败，请手动安装
    start https://www.python.org/downloads/
    pause
    goto :end
)
echo [OK] Python 安装完成

echo.
echo [3/3] 清理安装文件...
del python_installer.exe
echo [OK] 清理完成

echo.
echo ================================================
echo Python 安装成功！正在启动 Chrome 启动器...
echo ================================================
echo.
timeout /t 2 /nobreak >nul

:: 重新检测Python
call :check_python_again
if %errorLevel% neq 0 goto :end

:: 运行Python脚本
:run_python
echo.
echo [启动] 使用 Python 运行启动器...
python start_browser.py
if %errorLevel% neq 0 (
    echo.
    echo [错误] 启动失败
    echo 请截图此界面并联系客服
    pause
)
goto :end

:run_exe
echo.
echo [启动] 使用程序运行...
start_browser.exe
goto :end

:check_python_again
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [错误] Python 安装后仍未检测到
    echo 请重启电脑后再试
    exit /b 1
)
exit /b 0

:manual_download
echo.
echo 正在打开 Python 下载页面...
echo 请下载并安装 Python 3.8 或更高版本
echo 安装时请勾选 "Add Python to PATH"
start https://www.python.org/downloads/
pause
goto :end

:end
echo.
echo 按任意键退出...
pause >nul
