@echo off
chcp 65001 >nul
echo ========================================
echo   xsdm.com.cn 域名配置脚本上传工具
echo ========================================
echo.

set SSH_KEY=d:\work6.05\xsdm.pem
set SERVER_IP=8.163.37.124
set SCRIPT_PATH=scripts\deploy\setup_xsdm_domain.sh

echo 检查文件...
if not exist "%SSH_KEY%" (
    echo ❌ 错误: SSH密钥文件不存在: %SSH_KEY%
    pause
    exit /b 1
)

if not exist "%SCRIPT_PATH%" (
    echo ❌ 错误: 配置脚本不存在: %SCRIPT_PATH%
    pause
    exit /b 1
)

echo ✅ 文件检查通过
echo.

echo 正在上传配置脚本到服务器...
scp -i "%SSH_KEY%" "%SCRIPT_PATH%" root@%SERVER_IP%:/root/

if %ERRORLEVEL% NEQ 0 (
    echo ❌ 上传失败
    pause
    exit /b 1
)

echo.
echo ✅ 配置脚本已成功上传到服务器
echo.
echo ========================================
echo   下一步操作
echo ========================================
echo.
echo 1. 连接到服务器：
echo    ssh -i "%SSH_KEY%" root@%SERVER_IP%
echo.
echo 2. 执行配置脚本：
echo    chmod +x /root/setup_xsdm_domain.sh
echo    sudo bash /root/setup_xsdm_domain.sh
echo.
echo 3. 配置DNS解析（在阿里云控制台）：
echo    - 登录 https://dns.console.aliyun.com/
echo    - 添加 A记录: @ → 8.163.37.124
echo    - 添加 A记录: www → 8.163.37.124
echo.
echo 4. 等待DNS生效后申请SSL证书：
echo    sudo certbot --nginx -d xsdm.com.cn -d www.xsdm.com.cn
echo.
echo 详细文档：docs\guides\XSDM_DOMAIN_QUICK_START.md
echo.
pause