@echo off
chcp 65001 >nul
echo ========================================
echo    SSH连接故障诊断工具
echo ========================================
echo.

set SERVER_IP=8.163.37.124
set SERVER_USER=admin
set KEY_PATH=d:\work6.05\xsdm.pem

echo 诊断配置:
echo   公网IP: %SERVER_IP%
echo   用户名: %SERVER_USER%
echo   私钥: %KEY_PATH%
echo.

REM 检查私钥文件
echo [检查 1/5] 私钥文件是否存在...
if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)
echo ✓ 私钥文件存在
echo.

REM 检查私钥文件权限
echo [检查 2/5] 私钥文件权限...
icacls "%KEY_PATH%" | findstr /i "%USERNAME%.*F" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo ✓ 权限配置正确
) else (
    echo ⚠ 权限可能不正确
    echo 当前权限:
    icacls "%KEY_PATH%"
    echo.
    set /p FIX_PERM="是否修复权限？(y/n): "
    if /i "%FIX_PERM%"=="y" (
        icacls "%KEY_PATH%" /inheritance:r
        icacls "%KEY_PATH%" /grant:r "%USERNAME%:F"
        echo ✓ 权限已修复
    )
)
echo.

REM 测试网络连通性
echo [检查 3/5] 测试网络连通性...
ping -n 2 %SERVER_IP% >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo ✓ 网络连通正常
) else (
    echo ❌ 无法ping通服务器
    echo   请检查服务器是否运行
    pause
    exit /b 1
)
echo.

REM 测试SSH端口
echo [检查 4/5] 测试SSH端口(22)...
powershell -Command "$tcp = New-Object System.Net.Sockets.TcpClient; try { $tcp.Connect('%SERVER_IP%', 22); $tcp.Close(); Write-Host '✓ SSH端口开放'; exit 0 } catch { Write-Host '❌ SSH端口无法访问'; exit 1 }" 2>nul
if %ERRORLEVEL% neq 0 (
    echo ❌ SSH端口(22)无法访问
    echo   可能原因:
    echo   1. 防火墙未开放22端口
    echo   2. 服务器SSH服务未启动
    echo.
    echo 解决方案:
    echo   1. 在阿里云控制台检查防火墙规则
    echo   2. 使用Workbench连接检查SSH服务状态
    pause
    exit /b 1
)
echo.

REM 测试SSH连接（详细模式）
echo [检查 5/5] 测试SSH连接...
echo 尝试连接服务器...
echo.

REM 尝试使用不同的用户名
echo 测试用户名: %SERVER_USER%
ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o BatchMode=yes %SERVER_USER%@%SERVER_IP% "echo '连接成功！'" 2>&1 | findstr /i "success" >nul
if %ERRORLEVEL% equ 0 (
    echo ✓ 使用 %SERVER_USER%@%SERVER_IP% 连接成功！
    echo.
    echo 可以开始部署了！
    pause
    exit /b 0
)

echo ❌ 使用 %SERVER_USER%@%SERVER_IP% 连接失败
echo.

REM 尝试root用户
echo 尝试使用root用户...
ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o BatchMode=yes root@%SERVER_IP% "echo '连接成功！'" 2>&1 | findstr /i "success" >nul
if %ERRORLEVEL% equ 0 (
    echo ✓ 使用 root@%SERVER_IP% 连接成功！
    echo.
    echo 您的服务器使用root用户，不是admin用户
    echo 请更新部署脚本中的用户名为root
    pause
    exit /b 0
)

echo ❌ 使用 root@%SERVER_IP% 也连接失败
echo.

echo ========================================
echo 诊断结果汇总
echo ========================================
echo.
echo 可能的问题:
echo.
echo 1. 密钥对未正确绑定到服务器
echo    - 在阿里云控制台检查密钥对绑定状态
echo    - 如果未绑定，需要重新绑定密钥对
echo.
echo 2. 服务器用户名不正确
echo    - 轻量应用服务器可能默认使用root用户
echo    - 尝试使用root而不是admin
echo.
echo 3. 密钥对不匹配
echo    - 确认使用的私钥文件是正确的
echo    - 检查密钥对是否已绑定到当前实例
echo.
echo ========================================
echo 建议的解决方案
echo ========================================
echo.
echo 方案1: 使用Workbench连接并配置
echo   1. 在阿里云控制台点击"远程连接"
echo   2. 选择"Workbench"
echo   3. 使用Token登录
echo   4. 检查SSH配置和用户名
echo.
echo 方案2: 重新绑定密钥对
echo   1. 在阿里云控制台进入"密钥对"
echo   2. 确认密钥对已绑定到实例
echo   3. 如果未绑定，点击"绑定密钥对"
echo.
echo 方案3: 使用密码认证（临时方案）
echo   1. 在Workbench中设置root密码
echo   2. 使用密码连接进行部署
echo.
pause
exit /b 1